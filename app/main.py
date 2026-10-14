import os
import re
import uuid
import shutil
import hashlib
import asyncio
import subprocess
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.services.sqlite_db import SQLiteStorageService
from app.services.vector_db import VectorStorageService
from app.services.repo_mapper import RepositoryMapperService
from app.agents.reviewer import audit_agent_app
from app.services.language_detector import detect_language
from app.services.sarif_exporter import generate_sarif_report
from app.services.report_generator import generate_markdown_report
from app.services.llm_client import byok_manager

# Local directory where GitHub repos are cloned into
CLONED_REPOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cloned_repos")
os.makedirs(CLONED_REPOS_DIR, exist_ok=True)

# Static web files directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(
    title="CodeAuditAI Studio & API",
    description="Unified multi-agent asynchronous review studio and engine for intelligent codebase audits.",
    version="1.2.0"
)

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize our shared persistent service instances
sqlite_service = SQLiteStorageService()
vector_service = VectorStorageService()
repo_mapper = RepositoryMapperService(sqlite_service, vector_service)


def calculate_file_hash(file_path: str) -> str:
    """Computes MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_repo_root(file_path: str) -> str:
    """Walks upwards from a file path to find the repository root directory (.git or fallback)."""
    path = os.path.abspath(file_path)
    if os.path.isfile(path):
        path = os.path.dirname(path)
    
    while path and path != os.path.dirname(path):
        if os.path.exists(os.path.join(path, ".git")):
            return path
        path = os.path.dirname(path)
    return os.getcwd() # Default fallback


@app.get("/", response_class=HTMLResponse)
@app.get("/studio", response_class=HTMLResponse)
@app.get("/cli", response_class=HTMLResponse)
@app.get("/docs", response_class=HTMLResponse)
@app.get("/landing", response_class=HTMLResponse)
def read_studio():
    """
    Serves the CodeAuditAI Autonomous Multi-Agent Code Review Studio UI.
    """
    index_html_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_html_path):
        with open(index_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(
        content="<h1>CodeAuditAI Studio</h1><p>Web studio index.html not found. Place it in app/static/index.html</p>",
        status_code=404
    )


@app.get("/api/health")
def api_health():
    """
    System and model health check gateway.
    """
    return {
        "status": "healthy",
        "service": "CodeAuditAI Studio & API Gateway",
        "version": "1.2.0",
        "active_provider": byok_manager.active_provider,
        "active_model": byok_manager.models.get(byok_manager.active_provider, ""),
        "supported_languages": [
            "Python", "JavaScript", "TypeScript", "C", "C++", "Java", 
            "HTML", "CSS", "Go", "Rust", "PHP", "Ruby", "Swift", 
            "Kotlin", "Scala", "Lua", "Perl", "R", "Shell", "Markdown"
        ]
    }


# ---------------------------------------------------------------------------
# BYOK (Bring Your Own Key) Endpoints
# ---------------------------------------------------------------------------

class BYOKUpdateRequest(BaseModel):
    provider: Optional[str] = None
    key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None

class BYOKTestRequest(BaseModel):
    provider: str
    key: Optional[str] = None
    model: Optional[str] = None


@app.get("/api/byok/config")
def api_get_byok_config():
    """
    Returns non-sensitive status of all BYOK providers (Google AI Studio, Claude, OpenAI, DeepSeek, Copilot).
    """
    return byok_manager.get_config_summary()


@app.post("/api/byok/config")
def api_update_byok_config(req: BYOKUpdateRequest):
    """
    Updates the active provider, API key, model, or custom base URL dynamically at runtime.
    """
    if req.provider:
        byok_manager.set_provider(req.provider)
    if req.key and req.provider:
        byok_manager.update_key(req.provider, req.key)
    if req.model and req.provider:
        byok_manager.update_model(req.provider, req.model)
    if req.base_url and req.provider:
        byok_manager.update_base_url(req.provider, req.base_url)
    return {
        "status": "success",
        "message": f"Updated BYOK provider: {byok_manager.active_provider}",
        "config": byok_manager.get_config_summary()
    }


@app.post("/api/byok/test")
async def api_test_byok_connection(req: BYOKTestRequest):
    """
    Tests an API key connection for a specific provider with a live test ping.
    """
    result = await byok_manager.test_provider(provider=req.provider, key=req.key, model=req.model)
    return result


@app.post("/index-file")
async def api_index_file(file_path: str):
    """
    Locates, splits, and indexes a local file into ChromaDB vector storage with dynamic language detection.
    """
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
            
        file_hash = calculate_file_hash(file_path)
        repo_root = find_repo_root(file_path)
        
        # Check if we already have a summary cached in SQLite, otherwise generate a default one
        cached_meta = sqlite_service.get_file_metadata(file_path)
        summary = cached_meta["summary"] if cached_meta else "Single file manually indexed."
        
        # Index in vector DB
        vector_service.delete_file_index(file_path)
        chunks_indexed = vector_service.index_file(file_path, file_role=summary)
        
        # Upsert metadata in SQLite
        sqlite_service.upsert_file_metadata(
            repo_path=repo_root,
            file_path=file_path,
            file_hash=file_hash,
            summary=summary,
            importance="Medium"
        )
        
        return {
            "status": "success",
            "file_processed": file_path,
            "chunks_added": chunks_indexed
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal indexing failure: {str(e)}")


@app.get("/search-codebase")
async def api_search_codebase(
    query: str, 
    limit: int = Query(default=2, ge=1, le=5),
    filter_file: Optional[str] = None
):
    """
    Executes a semantic similarity search across indexed code blocks, optionally filtered to a single file.
    """
    try:
        search_hits = vector_service.semantic_search(query=query, limit=limit, filter_file=filter_file)
        return {
            "status": "success",
            "query": query,
            "total_matches": len(search_hits),
            "matches": search_hits
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal database query failure: {str(e)}")


@app.post("/analyze")
async def api_analyze_file(file_path: str):
    """
    Analyzes a local file with smart database-backed caching and repository-wide context mapping.
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Target file not found: {file_path}")

    try:
        current_hash = calculate_file_hash(file_path)
        
        # 1. Check SQLite Persistent Cache
        cached_meta = sqlite_service.get_file_metadata(file_path)
        cached_audit = sqlite_service.get_audit(file_path)
        
        if cached_meta and cached_audit and cached_meta["hash"] == current_hash:
            print(f"🛡️ [Cache Hit] Serving cached audit for: {file_path}")
            return {
                "status": "success",
                "target_file": file_path,
                "cached": True,
                "audit_results": {
                    "security_analysis": cached_audit["security_report"],
                    "performance_analysis": cached_audit["performance_report"]
                }
            }

        # 2. Cache Miss: Retrieve/Build Repository Context
        repo_root = find_repo_root(file_path)
        repo_data = await repo_mapper.map_repository(repo_root)
        
        # Fetch updated file role/summary from mapper
        updated_meta = sqlite_service.get_file_metadata(file_path)
        file_role = updated_meta["summary"] if updated_meta else ""
        
        # 3. Retrieve database semantic clues
        print(f"🔍 [Pipeline] Querying semantic context vectors for: {file_path}")
        db_hints = vector_service.semantic_search(
            query=f"vulnerabilities or performance issues in {os.path.basename(file_path)}", 
            limit=3
        )
        context_strings = [hit["content"] for hit in db_hints]

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source_code = f.read()

        initial_scorecard = {
            "file_path": file_path,
            "source_code": source_code,
            "repo_path": repo_root,
            "repo_map": repo_data["repo_map_string"],
            "retrieved_context": context_strings,
            "security_draft": "",
            "performance_draft": "",
            "security_report": "",
            "performance_report": ""
        }

        print("🚀 [Pipeline] Invoking upgraded LangGraph Multi-Agent Engine...")
        final_state = await audit_agent_app.ainvoke(initial_scorecard)

        security_report = final_state.get("security_report", "Analysis failed.")
        performance_report = final_state.get("performance_report", "Analysis failed.")

        # 4. Save audit results to database cache
        sqlite_service.upsert_audit(file_path, security_report, performance_report)
        
        # Double check that MD5 hash is stored correctly
        sqlite_service.upsert_file_metadata(
            repo_path=repo_root,
            file_path=file_path,
            file_hash=current_hash,
            summary=file_role,
            importance=updated_meta["importance"] if updated_meta else "Medium",
            language=updated_meta["language"] if updated_meta else ""
        )

        return {
            "status": "success",
            "target_file": file_path,
            "cached": False,
            "audit_results": {
                "security_analysis": security_report,
                "performance_analysis": performance_report
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit loop failed: {str(e)}")


@app.post("/analyze-repo")
async def api_analyze_repository(
    repo_path: str, 
    audit_high_importance: bool = Query(default=False, description="Auto-audit all High-importance files in the repo")
):
    """
    Maps and indexes a whole repository.
    Optionally triggers parallel audits for all detected High-importance files (e.g. entrypoints, configurations).
    """
    if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
        raise HTTPException(status_code=400, detail=f"Invalid repository directory: {repo_path}")

    try:
        # 1. Map and index repository
        repo_data = await repo_mapper.map_repository(repo_path)
        
        # 2. Retrieve all files
        repo_files = sqlite_service.get_repo_files(repo_path)
        
        audited_files_results = []
        
        # 3. If requested, audit High-importance files
        if audit_high_importance:
            high_imp_files = [f for f in repo_files if f["importance"] == "High"]
            print(f"⚡ [Pipeline] Auditing {len(high_imp_files)} High-importance files in background...")
            
            # Helper to run audit for a file (utilizes cache if clean)
            async def audit_single_file(file_entry):
                file_path = file_entry["file_path"]
                try:
                    current_hash = calculate_file_hash(file_path)
                    cached_audit = sqlite_service.get_audit(file_path)
                    
                    if cached_audit and file_entry["hash"] == current_hash:
                        return {
                            "file_path": file_path,
                            "summary": file_entry["summary"],
                            "cached": True,
                            "security_report": cached_audit["security_report"],
                            "performance_report": cached_audit["performance_report"]
                        }
                    
                    # Run full audit
                    db_hints = vector_service.semantic_search(
                        query=f"vulnerabilities or performance issues in {os.path.basename(file_path)}", 
                        limit=3
                    )
                    context_strings = [hit["content"] for hit in db_hints]
                    
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        source_code = f.read()

                    initial_scorecard = {
                        "file_path": file_path,
                        "source_code": source_code,
                        "repo_path": repo_path,
                        "repo_map": repo_data["repo_map_string"],
                        "retrieved_context": context_strings,
                        "security_draft": "",
                        "performance_draft": "",
                        "security_report": "",
                        "performance_report": ""
                    }
                    
                    final_state = await audit_agent_app.ainvoke(initial_scorecard)
                    sec_rep = final_state.get("security_report", "Analysis failed.")
                    perf_rep = final_state.get("performance_report", "Analysis failed.")
                    
                    sqlite_service.upsert_audit(file_path, sec_rep, perf_rep)
                    
                    return {
                        "file_path": file_path,
                        "summary": file_entry["summary"],
                        "cached": False,
                        "security_report": sec_rep,
                        "performance_report": perf_rep
                    }
                except Exception as ex:
                    return {
                        "file_path": file_path,
                        "summary": file_entry["summary"],
                        "error": str(ex)
                    }
            
            # Execute sequentially or with a small limit to protect rate limit bounds
            for file_entry in high_imp_files:
                res = await audit_single_file(file_entry)
                audited_files_results.append(res)
                
        return {
            "status": "success",
            "repository": repo_data["name"],
            "path": repo_data["path"],
            "summary": repo_data["summary"],
            "total_files": repo_data["file_count"],
            "repo_map": repo_data["repo_map_string"],
            "high_importance_audits": audited_files_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repository analysis failed: {str(e)}")


@app.post("/analyze-github")
async def api_analyze_github(
    github_url: str,
    audit_high_importance: bool = Query(default=False, description="Auto-audit all High-importance files after cloning")
):
    """
    Accepts a GitHub repository URL, clones it locally (or pulls latest if already cloned),
    then runs the full repository analysis pipeline on it.
    """
    # Basic validation: must look like a GitHub URL
    if not re.match(r"https?://(www\.)?github\.com/[\w\-]+/[\w\-\.]+", github_url):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL. Must be in the format: https://github.com/owner/repo")

    # Derive repo name from URL (strip trailing .git if present)
    repo_slug = github_url.rstrip("/").split("/")[-1]
    if repo_slug.endswith(".git"):
        repo_slug = repo_slug[:-4]

    local_repo_path = os.path.join(CLONED_REPOS_DIR, repo_slug)

    try:
        loop = asyncio.get_event_loop()

        if os.path.exists(local_repo_path):
            # Repo already cloned — pull latest changes instead
            print(f"♻️  [GitHub] Repo '{repo_slug}' already cloned. Pulling latest...")
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["git", "-C", local_repo_path, "pull"],
                    capture_output=True, text=True, timeout=120
                )
            )
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"git pull failed: {result.stderr.strip()}"
                )
            print(f"✅ [GitHub] Pull complete: {result.stdout.strip() or 'Already up to date.'}")
        else:
            # Fresh clone
            print(f"📥 [GitHub] Cloning '{github_url}' into '{local_repo_path}'...")
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["git", "clone", "--depth=1", github_url, local_repo_path],
                    capture_output=True, text=True, timeout=300
                )
            )
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"git clone failed: {result.stderr.strip()}"
                )
            print(f"✅ [GitHub] Clone complete.")

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out after 5 minutes.")


    try:
        repo_data = await repo_mapper.map_repository(local_repo_path)
        repo_files = sqlite_service.get_repo_files(local_repo_path)
        audited_files_results = []

        if audit_high_importance:
            high_imp_files = [f for f in repo_files if f["importance"] == "High"]
            print(f"⚡ [Pipeline] Auditing {len(high_imp_files)} High-importance files in '{repo_slug}'...")

            for file_entry in high_imp_files:
                file_path = file_entry["file_path"]
                try:
                    current_hash = calculate_file_hash(file_path)
                    cached_audit = sqlite_service.get_audit(file_path)

                    if cached_audit and file_entry["hash"] == current_hash:
                        audited_files_results.append({
                            "file_path": file_path,
                            "summary": file_entry["summary"],
                            "cached": True,
                            "security_report": cached_audit["security_report"],
                            "performance_report": cached_audit["performance_report"]
                        })
                        continue

                    db_hints = vector_service.semantic_search(
                        query=f"vulnerabilities or performance issues in {os.path.basename(file_path)}",
                        limit=3
                    )
                    context_strings = [hit["content"] for hit in db_hints]

                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        source_code = f.read()

                    initial_scorecard = {
                        "file_path": file_path,
                        "source_code": source_code,
                        "repo_path": local_repo_path,
                        "repo_map": repo_data["repo_map_string"],
                        "retrieved_context": context_strings,
                        "security_draft": "",
                        "performance_draft": "",
                        "security_report": "",
                        "performance_report": ""
                    }

                    final_state = await audit_agent_app.ainvoke(initial_scorecard)
                    sec_rep = final_state.get("security_report", "Analysis failed.")
                    perf_rep = final_state.get("performance_report", "Analysis failed.")
                    sqlite_service.upsert_audit(file_path, sec_rep, perf_rep)

                    audited_files_results.append({
                        "file_path": os.path.relpath(file_path, local_repo_path),
                        "summary": file_entry["summary"],
                        "cached": False,
                        "security_report": sec_rep,
                        "performance_report": perf_rep
                    })
                except Exception as ex:
                    audited_files_results.append({
                        "file_path": os.path.relpath(file_path, local_repo_path),
                        "error": str(ex)
                    })

        return {
            "status": "success",
            "source": github_url,
            "local_clone": local_repo_path,
            "repository": repo_data["name"],
            "summary": repo_data["summary"],
            "total_files": repo_data["file_count"],
            "repo_map": repo_data["repo_map_string"],
            "high_importance_audits": audited_files_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub repository analysis failed: {str(e)}")


# ---------------------------------------------------------------------------
# Pydantic model for /analyze-snippet
# ---------------------------------------------------------------------------

class SnippetRequest(BaseModel):
    code: str
    language: str  # e.g. 'python', 'java', 'javascript', 'cpp', 'html', 'css'
    filename: Optional[str] = None


# Map submitted language slug → canonical file extension
_LANG_SLUG_TO_EXT = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "java": ".java",
    "c": ".c",
    "cpp": ".cpp",
    "html": ".html",
    "css": ".css",
    "go": ".go",
    "rust": ".rs",
    "php": ".php",
    "ruby": ".rb",
    "swift": ".swift",
    "kotlin": ".kt",
    "scala": ".scala",
    "lua": ".lua",
    "perl": ".pl",
    "r": ".r",
    "shell": ".sh",
    "bash": ".sh",
    "json": ".json",
    "yaml": ".yaml",
    "xml": ".xml",
    "sql": ".sql",
    "toml": ".toml",
    "markdown": ".md",
    "csharp": ".cs",
}


# ---------------------------------------------------------------------------
# GET /supported-languages
# ---------------------------------------------------------------------------

@app.get("/supported-languages")
def api_supported_languages():
    """
    Returns a JSON dict of all languages supported by CodeAuditAI,
    including their file extensions and audit capability notes.
    """
    return {
        "Python": {
            "extensions": [".py"],
            "audit_focus": "SQL injection, command injection, pickle deserialization, eval/exec, SSRF, SSTI, GIL, N+1 queries"
        },
        "JavaScript": {
            "extensions": [".js", ".jsx", ".mjs", ".cjs"],
            "audit_focus": "XSS, prototype pollution, eval(), ReDoS, memory leaks, bundle size"
        },
        "TypeScript": {
            "extensions": [".ts", ".tsx"],
            "audit_focus": "XSS, unsafe any casts, missing null checks, prototype pollution, bundle size"
        },
        "Java": {
            "extensions": [".java"],
            "audit_focus": "SQL injection, deserialization, XXE, LDAP injection, N+1 JPA queries, StringBuilder"
        },
        "C": {
            "extensions": [".c"],
            "audit_focus": "Buffer overflow, format strings, use-after-free, double free, memory leaks"
        },
        "C++": {
            "extensions": [".cpp", ".cc", ".cxx", ".h", ".hpp"],
            "audit_focus": "Buffer overflow, use-after-free, RAII, move semantics, cache locality"
        },
        "Go": {
            "extensions": [".go"],
            "audit_focus": "SQL injection, goroutine leaks, exec.Command injection, SSRF, sync.Mutex misuse"
        },
        "Rust": {
            "extensions": [".rs"],
            "audit_focus": "Unsafe blocks, integer overflow in release, unwrap() panics, excessive Arc/Rc"
        },
        "PHP": {
            "extensions": [".php"],
            "audit_focus": "SQL injection, shell_exec, LFI/RFI, XSS, unserialize(), N+1 queries"
        },
        "HTML": {
            "extensions": [".html", ".htm"],
            "audit_focus": "Inline XSS handlers, missing CSP, iframe without sandbox, lazy loading"
        },
        "CSS": {
            "extensions": [".css", ".scss", ".sass", ".less"],
            "audit_focus": "CSS injection, clickjacking z-index, @import from untrusted sources, repaints"
        },
        "C#": {
            "extensions": [".cs"],
            "audit_focus": "SQL injection, deserialization, XXE, hardcoded credentials"
        },
        "Ruby": {
            "extensions": [".rb"],
            "audit_focus": "SQL injection, command injection, eval, mass assignment, SSRF"
        },
        "Swift": {
            "extensions": [".swift"],
            "audit_focus": "Force unwrap crashes, SQL injection, hardcoded keys, insecure storage"
        },
        "Kotlin": {
            "extensions": [".kt", ".kts"],
            "audit_focus": "Null pointer, SQL injection, insecure deserialization, coroutine misuse"
        },
        "Scala": {
            "extensions": [".scala"],
            "audit_focus": "Injection flaws, deserialization, actor deadlocks, memory leaks"
        },
        "Lua": {
            "extensions": [".lua"],
            "audit_focus": "Injection via load/loadstring, hardcoded credentials, global variable pollution"
        },
        "Perl": {
            "extensions": [".pl", ".pm"],
            "audit_focus": "Command injection, SQL injection, eval, taint mode bypasses"
        },
        "R": {
            "extensions": [".r", ".R"],
            "audit_focus": "Command injection via system(), eval, hardcoded credentials, package trust"
        },
        "Shell": {
            "extensions": [".sh", ".bash"],
            "audit_focus": "Command injection, unquoted variables, path traversal, hardcoded credentials"
        },
        "Markdown": {
            "extensions": [".md", ".mdx"],
            "audit_focus": "Hardcoded secrets in docs, sensitive data in comments, injection in code examples"
        },
        "JSON": {
            "extensions": [".json"],
            "audit_focus": "Hardcoded credentials, API keys, sensitive configuration exposure"
        },
        "YAML": {
            "extensions": [".yaml", ".yml"],
            "audit_focus": "Hardcoded secrets, YAML injection, insecure CI/CD permissions"
        },
        "XML": {
            "extensions": [".xml"],
            "audit_focus": "XXE injection, sensitive data exposure, overly permissive DTDs"
        },
        "SQL": {
            "extensions": [".sql"],
            "audit_focus": "Injection patterns, privilege escalation, sensitive data exposure"
        },
        "TOML": {
            "extensions": [".toml"],
            "audit_focus": "Hardcoded secrets, insecure dependency versions, credential exposure"
        },
    }


# ---------------------------------------------------------------------------
# GET /list-files
# ---------------------------------------------------------------------------

@app.get("/list-files")
def api_list_files(repo_path: Optional[str] = None):
    """
    Returns file metadata stored in the SQLite database.
    If repo_path is provided, filters to that repository only.
    """
    try:
        if repo_path:
            files = sqlite_service.get_repo_files(repo_path)
        else:
            # Query all files across every repo
            with sqlite_service._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM files")
                files = [dict(row) for row in cursor.fetchall()]
        return {
            "status": "success",
            "repo_path": repo_path or "all",
            "total_files": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


# ---------------------------------------------------------------------------
# GET /api/projects & DELETE /api/projects
# ---------------------------------------------------------------------------

@app.get("/api/projects")
def api_get_projects():
    """
    Returns all indexed repositories/projects with file counts and audit stats.
    """
    try:
        projects = sqlite_service.get_all_repositories()
        return {
            "status": "success",
            "total_projects": len(projects),
            "projects": projects
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")


@app.delete("/api/projects")
def api_delete_project(repo_path: str = Query(..., description="Repository path to remove")):
    """
    Removes a project from the database, including its indexed files and cached audits.
    """
    try:
        success = sqlite_service.delete_repository(repo_path)
        return {
            "status": "success",
            "message": f"Project '{repo_path}' and associated records removed successfully.",
            "deleted": success
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


# ---------------------------------------------------------------------------
# GET /get-audit
# ---------------------------------------------------------------------------

@app.get("/get-audit")
def api_get_audit(file_path: str):
    """
    Returns the cached audit result for a specific file path, or 404 if not found.
    """
    audit = sqlite_service.get_audit(file_path)
    if not audit:
        raise HTTPException(
            status_code=404,
            detail=f"No cached audit found for: {file_path}"
        )
    return {
        "status": "success",
        "file_path": file_path,
        "audit": audit
    }


# ---------------------------------------------------------------------------
# DELETE /clear-cache
# ---------------------------------------------------------------------------

@app.delete("/clear-cache")
def api_clear_cache(file_path: str):
    """
    Clears the cached audit for a specific file path.
    Use file_path='*' to clear ALL cached audits.
    """
    try:
        if file_path == "*":
            sqlite_service.clear_all_audits()
            return {"status": "success", "message": "All cached audits have been cleared."}
        else:
            sqlite_service.clear_audit(file_path)
            return {"status": "success", "message": f"Cached audit cleared for: {file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


# ---------------------------------------------------------------------------
# POST /analyze-snippet
# ---------------------------------------------------------------------------

SNIPPETS_DIR = "/tmp/codeauditai_snippets"


@app.post("/analyze-snippet")
async def api_analyze_snippet(request: SnippetRequest):
    """
    Analyzes an inline code snippet by writing it to a temp file and running
    the full audit pipeline (same as /analyze), then cleaning up the temp file.
    """
    # Resolve file extension from language slug
    lang_slug = request.language.lower().strip()
    ext = _LANG_SLUG_TO_EXT.get(lang_slug)
    if ext is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language slug '{request.language}'. "
                   f"Supported: {sorted(_LANG_SLUG_TO_EXT.keys())}"
        )

    # Build temp file path
    os.makedirs(SNIPPETS_DIR, exist_ok=True)
    snippet_id = str(uuid.uuid4())
    base_name = request.filename or f"snippet{ext}"
    # Ensure the filename has the correct extension
    if not base_name.endswith(ext):
        base_name = f"{os.path.splitext(base_name)[0]}{ext}"
    temp_file_path = os.path.join(SNIPPETS_DIR, f"{snippet_id}_{base_name}")

    try:
        # Write snippet to disk
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(request.code)

        # Build minimal audit context (no repo map needed for a snippet)
        db_hints = vector_service.semantic_search(
            query=f"vulnerabilities or performance issues in {base_name}",
            limit=3
        )
        context_strings = [hit["content"] for hit in db_hints]

        initial_scorecard = {
            "file_path": temp_file_path,
            "source_code": request.code,
            "repo_path": SNIPPETS_DIR,
            "repo_map": "Standalone code snippet — no repository context.",
            "retrieved_context": context_strings,
            "security_draft": "",
            "performance_draft": "",
            "security_report": "",
            "performance_report": ""
        }

        print(f"🚀 [Snippet] Invoking LangGraph audit pipeline for snippet: {base_name}")
        final_state = await audit_agent_app.ainvoke(initial_scorecard)

        security_report = final_state.get("security_report", "Analysis failed.")
        performance_report = final_state.get("performance_report", "Analysis failed.")

        detected_language = detect_language(temp_file_path)

        return {
            "status": "success",
            "snippet_id": snippet_id,
            "filename": base_name,
            "language": detected_language,
            "cached": False,
            "audit_results": {
                "security_analysis": security_report,
                "performance_analysis": performance_report
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Snippet audit failed: {str(e)}")

    finally:
        # Always clean up the temp file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# GET /export/sarif
# ---------------------------------------------------------------------------

@app.get("/export/sarif")
def api_export_sarif(repo_path: Optional[str] = None):
    """
    Exports all cached audit findings in standard SARIF v2.1.0 format.
    Suitable for importing into GitHub Security alerts, VS Code SARIF viewer, GitLab, etc.
    """
    try:
        if repo_path:
            repo_files = sqlite_service.get_repo_files(repo_path)
            repo_info = sqlite_service.get_repository(repo_path)
            repo_name = repo_info["name"] if repo_info else os.path.basename(repo_path.rstrip(os.sep))
        else:
            with sqlite_service._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM files")
                repo_files = [dict(row) for row in cursor.fetchall()]
            repo_name = "CodeAuditAI All Repositories Scan"

        audited_files = []
        for f in repo_files:
            file_path = f["file_path"]
            audit = sqlite_service.get_audit(file_path)
            if audit:
                audited_files.append({
                    "file_path": file_path,
                    "summary": f.get("summary", ""),
                    "security_report": audit["security_report"],
                    "performance_report": audit["performance_report"]
                })

        sarif_data = generate_sarif_report(audited_files, repo_name=repo_name)
        return JSONResponse(
            content=sarif_data,
            media_type="application/sarif+json",
            headers={"Content-Disposition": f"attachment; filename={repo_name.replace(' ', '_')}_findings.sarif"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SARIF export failed: {str(e)}")


# ---------------------------------------------------------------------------
# GET /export/markdown
# ---------------------------------------------------------------------------

@app.get("/export/markdown")
def api_export_markdown(repo_path: Optional[str] = None):
    """
    Exports a comprehensive Executive Markdown audit report for all cached files in a repository.
    """
    try:
        if repo_path:
            repo_files = sqlite_service.get_repo_files(repo_path)
            repo_info = sqlite_service.get_repository(repo_path)
            repo_name = repo_info["name"] if repo_info else os.path.basename(repo_path.rstrip(os.sep))
            repo_summary = repo_info["summary"] if repo_info else ""
        else:
            with sqlite_service._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM files")
                repo_files = [dict(row) for row in cursor.fetchall()]
            repo_name = "CodeAuditAI Master Scan"
            repo_summary = f"Aggregated analysis across {len(repo_files)} source files in database."

        audited_files = []
        for f in repo_files:
            file_path = f["file_path"]
            audit = sqlite_service.get_audit(file_path)
            if audit:
                audited_files.append({
                    "file_path": file_path,
                    "summary": f.get("summary", ""),
                    "security_report": audit["security_report"],
                    "performance_report": audit["performance_report"]
                })

        md_report = generate_markdown_report(
            repo_name=repo_name,
            repo_path=repo_path or "All Cached Repositories",
            audited_files=audited_files,
            repo_summary=repo_summary
        )

        return PlainTextResponse(
            content=md_report,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={repo_name.replace(' ', '_')}_report.md"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Markdown report export failed: {str(e)}")