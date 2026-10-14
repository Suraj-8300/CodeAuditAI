import os
import hashlib
import asyncio
from typing import List, Dict, Any, Tuple
from app.services.sqlite_db import SQLiteStorageService
from app.services.vector_db import VectorStorageService
from app.services.llm_client import safe_invoke

# Standard folders and extensions to ignore
IGNORE_FOLDERS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", 
    "dist", "build", "target", ".idea", ".vscode", "chroma_storage",
    "cloned_repos"
}

IGNORE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", 
    ".zip", ".tar", ".gz", ".rar", ".pdf", ".db", ".sqlite", 
    ".sqlite3", ".pyc", ".woff", ".woff2", ".eot", ".ttf", ".sarif"
}

# Files that should never be classified as High importance (saves audit tokens)
LOW_VALUE_FILENAMES = {
    ".gitignore", ".editorconfig", ".prettierrc", ".eslintrc", 
    ".eslintrc.js", ".eslintrc.json", "package-lock.json", "yarn.lock",
    "pnpm-lock.yaml", ".npmrc", ".nvmrc", "LICENSE", "LICENSE.md",
    "CHANGELOG.md", "CONTRIBUTING.md", ".dockerignore", "Makefile"
}

class RepositoryMapperService:
    def __init__(self, sqlite_service: SQLiteStorageService, vector_service: VectorStorageService):
        self.sqlite = sqlite_service
        self.vector_db = vector_service

    def _calculate_md5(self, file_path: str) -> str:
        """Computes MD5 hash of a file to check for content modifications."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _should_ignore(self, file_path: str, repo_root: str) -> bool:
        """Determines if a file should be ignored during repo scan."""
        rel_path = os.path.relpath(file_path, repo_root)
        parts = rel_path.split(os.sep)
        
        # Check folders
        if any(part in IGNORE_FOLDERS for part in parts):
            return True
            
        # Check extension
        _, ext = os.path.splitext(file_path)
        if ext.lower() in IGNORE_EXTENSIONS:
            return True
            
        # Ignore files that are larger than 1MB to prevent out-of-memory or token overload
        try:
            if os.path.getsize(file_path) > 1 * 1024 * 1024:
                return True
        except OSError:
            return True
            
        return False

    def _clamp_importance(self, filename: str, importance: str) -> str:
        """
        Prevents low-value files from being marked High, regardless of LLM output.
        This directly saves audit tokens since only High files get fully audited.
        """
        if filename in LOW_VALUE_FILENAMES:
            return "Low"
        return importance

    async def _summarize_file_llm(self, file_path: str, rel_path: str) -> Tuple[str, str, str]:
        """
        Asynchronously generates a quick summary, importance, and language for a file.
        Takes only the first 1500 chars to save tokens.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                snippet = f.read(1500)
        except Exception as e:
            return f"Error reading file: {str(e)}", "Low", ""

        if not snippet.strip():
            return "Empty file", "Low", ""

        prompt = (
            "You are a repository analyzer assistant.\n"
            f"Analyze the following preview of the file: {rel_path}\n"
            f"--- Code Preview ---\n{snippet}\n--- End Preview ---\n\n"
            "Respond in EXACTLY the following format (3 lines, no extra text):\n"
            "Summary: [One short sentence summarizing what this file does]\n"
            "Importance: [High/Medium/Low] (High = core logic/entry point/critical config, Medium = normal utility/component, Low = tests/mock data/lockfiles/auxiliary)\n"
            "Language: [Programming Language name, e.g. Python, JavaScript, TypeScript, Go]"
        )

        try:
            text = await safe_invoke(prompt)
            lines = text.split("\n")
            summary, importance, language = "No summary", "Medium", ""
            for line in lines:
                if line.startswith("Summary:"):
                    summary = line.replace("Summary:", "").strip()
                elif line.startswith("Importance:"):
                    importance = line.replace("Importance:", "").strip()
                    if importance not in {"High", "Medium", "Low"}:
                        importance = "Medium"
                elif line.startswith("Language:"):
                    language = line.replace("Language:", "").strip()
            
            # Clamp importance for known low-value files
            filename = os.path.basename(file_path)
            importance = self._clamp_importance(filename, importance)
            
            return summary, importance, language
        except Exception as e:
            print(f"⚠️ LLM summary failed for {rel_path}: {e}")
            return "Failed to analyze", "Medium", ""

    async def map_repository(self, repo_path: str) -> Dict[str, Any]:
        """
        Scans a repository, hashes all files, uses SQLite cache to skip unchanged files,
        summarizes new/modified files asynchronously, indexes modified files in ChromaDB,
        and saves repository metadata.
        """
        repo_path = os.path.abspath(repo_path)
        repo_name = os.path.basename(repo_path.rstrip(os.sep))
        
        print(f"📂 [RepoMapper] Scanning repository: {repo_name} at {repo_path}...")
        
        # 1. Walk filesystem to gather all files to process
        all_files = []
        for root, dirs, files in os.walk(repo_path):
            # Prune directory search to skip ignored folders
            dirs[:] = [d for d in dirs if d not in IGNORE_FOLDERS]
            for file in files:
                full_path = os.path.join(root, file)
                if not self._should_ignore(full_path, repo_path):
                    all_files.append(full_path)

        # 2. Identify new/modified files vs cached ones
        files_to_process = []
        db_files = self.sqlite.get_repo_files(repo_path)
        cached_files_map = {f["file_path"]: f for f in db_files}
        
        active_paths = set()
        
        for file_path in all_files:
            rel_path = os.path.relpath(file_path, repo_path)
            active_paths.add(file_path)
            
            curr_hash = self._calculate_md5(file_path)
            cached = cached_files_map.get(file_path)
            
            if cached and cached["hash"] == curr_hash:
                # File is unchanged — skip
                continue
            else:
                # File is new or changed
                files_to_process.append((file_path, rel_path, curr_hash))

        # 3. Clean up deleted files from SQLite & ChromaDB
        for file_path in cached_files_map:
            if file_path not in active_paths:
                print(f"🗑️ [RepoMapper] Deleting index and metadata for removed file: {file_path}")
                self.vector_db.delete_file_index(file_path)
                self.sqlite.clear_audit(file_path)
                with self.sqlite._get_connection() as conn:
                    conn.execute("DELETE FROM files WHERE file_path = ?", (file_path,))
                    conn.commit()

        # 4. Process new/modified files concurrently (with limited concurrency)
        if files_to_process:
            print(f"🧠 [RepoMapper] Found {len(files_to_process)} new/modified files. Running analysis...")
            # Semaphore of 3 prevents burst-firing too many LLM calls at once
            semaphore = asyncio.Semaphore(3)
            
            async def process_file(file_info):
                file_path, rel_path, curr_hash = file_info
                async with semaphore:
                    summary, importance, language = await self._summarize_file_llm(file_path, rel_path)
                    
                    # Store in SQLite
                    self.sqlite.upsert_file_metadata(
                        repo_path=repo_path,
                        file_path=file_path,
                        file_hash=curr_hash,
                        summary=summary,
                        importance=importance,
                        language=language
                    )
                    
                    # Re-index in Vector DB (delete old index first to avoid duplicate chunks)
                    self.vector_db.delete_file_index(file_path)
                    self.vector_db.index_file(file_path, file_role=summary)
                    
                    # Invalidate any old audit results for this modified file
                    self.sqlite.clear_audit(file_path)
                    print(f"✅ [RepoMapper] Processed & Indexed: {rel_path} ({importance})")

            # Run concurrently within semaphore limits
            await asyncio.gather(*(process_file(f) for f in files_to_process))
        else:
            print("🛡️ [RepoMapper] All files are cached and up-to-date!")

        # 5. Build the repository map representation
        repo_files = self.sqlite.get_repo_files(repo_path)
        
        # Sort files by relative path for structural display
        repo_files.sort(key=lambda x: os.path.relpath(x["file_path"], repo_path))
        
        repo_map_str = f"Repository: {repo_name}\nLocation: {repo_path}\n\nFiles List:\n"
        for file in repo_files:
            rel_path = os.path.relpath(file["file_path"], repo_path)
            repo_map_str += f"- {rel_path} | Importance: {file['importance']} | Role: {file['summary']}\n"

        # Update the repo summary in DB
        repo_summary = f"Codebase '{repo_name}' with {len(repo_files)} analyzed source files."
        self.sqlite.upsert_repository(repo_path, repo_name, repo_summary)
        
        return {
            "name": repo_name,
            "path": repo_path,
            "summary": repo_summary,
            "file_count": len(repo_files),
            "repo_map_string": repo_map_str
        }
