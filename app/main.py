import os
import asyncio
from fastapi import FastAPI, HTTPException, Query
from app.services.vector_db import VectorStorageService
from app.agents.reviewer import audit_agent_app

app = FastAPI(
    title="AI Code Auditor API",
    description="Unified multi-agent asynchronous engine for intelligent codebase audits.",
    version="1.0.0"
)

# Create an architectural system cache ledger at the top of app/main.py
AUDIT_CACHE = {}

# Initialize our shared persistent vector database service
vector_service = VectorStorageService()


def extract_clean_text(report_field) -> str:
    """
    Defensive helper to strip Google GenAI SDK wrappers if present,
    returning a clean markdown string to the API response.
    """
    if isinstance(report_field, list) and len(report_field) > 0:
        if isinstance(report_field[0], dict) and "text" in report_field[0]:
            return report_field[0]["text"]
    if isinstance(report_field, str):
        return report_field
    return str(report_field)


@app.get("/")
def read_root():
    return {"status": "healthy", "message": "Welcome to the AI Code Auditor API Gateway"}


@app.post("/index-file")
async def api_index_file(file_path: str):
    """
    Locates, splits, and indexes a local file into ChromaDB vector storage.
    """
    try:
        chunks_indexed = vector_service.index_file(file_path)
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
async def api_search_codebase(query: str, limit: int = Query(default=2, ge=1, le=5)):
    """
    Executes a semantic similarity search across all indexed code blocks.
    """
    try:
        search_hits = vector_service.semantic_search(query=query, limit=limit)
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
    The Ultimate Endpoint: Analyzes a local file with built-in 
    in-memory architectural caching to save API rate-limits.
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Target file not found: {file_path}")

    # 1. Check our Production Shield Cache
    if file_path in AUDIT_CACHE:
        print(f"🛡️ [Shield] Cache hit for {file_path}! Skipping Gemini API round-trip.")
        return AUDIT_CACHE[file_path]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        print(f"🔍 [Pipeline] Retrieving semantic database clues for {file_path}...")
        db_hints = vector_service.semantic_search(query=f"vulnerabilities in {file_path}", limit=2)
        context_strings = [hit["content"] for hit in db_hints]

        initial_scorecard = {
            "file_path": file_path,
            "source_code": source_code,
            "retrieved_context": context_strings,
            "security_report": "",
            "performance_report": "",
            "final_compiled_review": ""
        }

        print("🚀 [Pipeline] Triggering LangGraph Multi-Agent Engine...")
        final_state = await audit_agent_app.ainvoke(initial_scorecard)

        # Instead of: final_state = await audit_agent_app.ainvoke(...)
        # You can stream every node transaction in real-time:
        async for event in audit_agent_app.astream(initial_scorecard):
            for node_name, output in event.items():
                print(f"⚙️ Node '{node_name}' has modified the state scorecard keys: {list(output.keys())}")
        
        clean_security = extract_clean_text(final_state.get("security_report", ""))
        clean_performance = extract_clean_text(final_state.get("performance_report", ""))

        # Package the successful response payload
        response_payload = {
            "status": "success",
            "target_file": file_path,
            "cached": True,  # Will show True when pulled from memory next time
            "audit_results": {
                "security_analysis": clean_security,
                "performance_analysis": clean_performance
            }
        }

        # 2. Save to cache before returning to user
        AUDIT_CACHE[file_path] = response_payload
        
        # Adjust the payload flag for the initial live generation run
        live_payload = response_payload.copy()
        live_payload["cached"] = False
        return live_payload

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit loop failed: {str(e)}")