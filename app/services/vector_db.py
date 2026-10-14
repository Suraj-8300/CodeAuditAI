import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

# CSS-family extensions (no LangChain Language enum exists for CSS)
CSS_EXTENSIONS = {".css", ".scss", ".sass", ".less"}

# Map of common file extensions to LangChain splitters
EXTENSION_TO_LANGUAGE = {
    # Python
    ".py": Language.PYTHON,
    # JavaScript / TypeScript
    ".js": Language.JS,
    ".jsx": Language.JS,
    ".mjs": Language.JS,
    ".cjs": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    # Go
    ".go": Language.GO,
    # C / C++
    ".cpp": Language.CPP,
    ".cc": Language.CPP,
    ".cxx": Language.CPP,
    ".h": Language.CPP,
    ".hpp": Language.CPP,
    ".c": Language.C,
    # Java / Kotlin
    ".java": Language.JAVA,
    ".kt": Language.KOTLIN,
    ".kts": Language.KOTLIN,
    # Rust
    ".rs": Language.RUST,
    # PHP
    ".php": Language.PHP,
    # HTML
    ".html": Language.HTML,
    ".htm": Language.HTML,
    # Markdown
    ".md": Language.MARKDOWN,
    ".mdx": Language.MARKDOWN,
    # Swift
    ".swift": Language.SWIFT,
    # C# 
    ".cs": Language.CSHARP,
    # Ruby
    ".rb": Language.RUBY,
    # Lua
    ".lua": Language.LUA,
    # Perl
    ".pl": Language.PERL,
    ".pm": Language.PERL,
    # R
    ".r": Language.R,
    ".R": Language.R,
    # Scala
    ".scala": Language.SCALA,
}

class VectorStorageService:
    def __init__(self, storage_path: str = "./app/services/chroma_storage"):
        """
        Initializes the persistent local vector database connection.
        """
        # Ensure the storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=storage_path)
        
        # Uses standard local sentence-transformers (all-MiniLM-L6-v2) under the hood,
        # running entirely on the user's local machine without external API token costs.
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Initialize our production collection
        self.collection = self.client.get_or_create_collection(
            name="codebase_vault",
            embedding_function=self.embedding_fn
        )

    def _get_splitter_for_file(self, file_path: str) -> RecursiveCharacterTextSplitter:
        """
        Detects file extension and returns a syntax-aware splitter,
        or a default splitter if the language is unsupported.
        """
        _, ext = os.path.splitext(file_path)
        ext_lower = ext.lower()
        lang = EXTENSION_TO_LANGUAGE.get(ext_lower)

        if lang:
            return RecursiveCharacterTextSplitter.from_language(
                language=lang,
                chunk_size=700,  # Increased slightly to accommodate contextual header
                chunk_overlap=70
            )
        elif ext_lower in CSS_EXTENSIONS:
            # CSS/SCSS/SASS/LESS — custom rule-block-aware splitter
            return RecursiveCharacterTextSplitter(
                chunk_size=700,
                chunk_overlap=70,
                separators=["}", "\n\n", "\n", " ", ""]
            )
        else:
            # Generic plain-text/config files splitter
            return RecursiveCharacterTextSplitter(
                chunk_size=700,
                chunk_overlap=70,
                separators=["\n\n", "\n", " ", ""]
            )

    MAX_INDEX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB threshold against DoS memory exhaustion (CWE-400)

    def index_file(self, file_path: str, file_role: str = "") -> int:
        """
        Reads a local file, splits it into syntax-aware chunks, enriches each chunk
        with contextual metadata headers (Contextual Chunking), and indexes into ChromaDB.
        Returns the number of indexed chunks.
        """
        norm_path = os.path.abspath(os.path.normpath(file_path))
        if not os.path.exists(norm_path):
            raise FileNotFoundError(f"Target file not found: {norm_path}")

        # Protect against Denial of Service via giant/unbounded files (CWE-400)
        file_size = os.path.getsize(norm_path)
        if file_size > self.MAX_INDEX_FILE_SIZE:
            print(f"⚠️ [VectorStorage] Skipping indexing for oversized file ({file_size} bytes): {norm_path}")
            return 0
            
        with open(norm_path, "r", encoding="utf-8", errors="ignore") as f:
            source_code = f.read()
            
        splitter = self._get_splitter_for_file(norm_path)
        raw_chunks = splitter.split_text(source_code)
        if not raw_chunks:
            return 0
            
        # Contextual Enrichment: prepending file name & role/summary to each chunk
        # This keeps critical high-level context attached to the chunk inside the vector space.
        enriched_chunks = []
        filename = os.path.basename(norm_path)
        role_info = f" | Role: {file_role}" if file_role else ""
        
        for chunk in raw_chunks:
            header = f"[File: {filename}{role_info}]\n---\n"
            enriched_chunks.append(header + chunk)
            
        # Generate canonical, collision-free tracking keys using normalized path (CWE-22)
        chunk_ids = [f"{norm_path}_chunk_{i}" for i in range(len(enriched_chunks))]
        metadatas = [{"source_file": norm_path} for _ in range(len(enriched_chunks))]
        
        # Commit directly to our collection
        self.collection.add(
            documents=enriched_chunks,
            ids=chunk_ids,
            metadatas=metadatas
        )
        return len(enriched_chunks)

    def delete_file_index(self, file_path: str):
        """
        Removes all indexed chunks associated with a specific file path.
        """
        norm_path = os.path.abspath(os.path.normpath(file_path))
        try:
            self.collection.delete(where={"source_file": norm_path})
        except Exception as e:
            # Collection might be empty or key missing; log structured diagnostic
            if "not found" not in str(e).lower():
                print(f"⚠️ [VectorStorage] Notice deleting index for {norm_path}: {e}")

    def semantic_search(self, query: str, limit: int = 2, filter_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Queries the vector space and returns the closest matching code structural segments.
        Optionally filters results to a specific file.
        """
        norm_filter = os.path.abspath(os.path.normpath(filter_file)) if filter_file else None
        where_clause = {"source_file": norm_filter} if norm_filter else None
        
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where_clause
        )
        
        # Reformat Chroma's output into a clean, scannable list
        formatted_results = []
        if results and results["documents"] and len(results["documents"]) > 0:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                })
        return formatted_results