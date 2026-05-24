import os
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

class VectorStorageService:
    def __init__(self, storage_path: str = "./app/services/chroma_storage"):
        """
        Initializes the persistent local vector database connection.
        """
        # Ensure the storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=storage_path)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Initialize our production collection
        self.collection = self.client.get_or_create_collection(
            name="codebase_vault",
            embedding_function=self.embedding_fn
        )
        
        # Configure our standard Python splitter
        self.splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON,
            chunk_size=500,
            chunk_overlap=50
        )

    def index_file(self, file_path: str) -> int:
        """
        Reads a local file, splits it into language-aware chunks, and commits it to the database.
        Returns the number of indexed chunks.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Target file not found: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
            
        chunks = self.splitter.split_text(source_code)
        if not chunks:
            return 0
            
        # Generate unique structured tracking keys
        chunk_ids = [f"{file_path}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"source_file": file_path} for _ in range(len(chunks))]
        
        # Commit directly to our collection
        self.collection.add(
            documents=chunks,
            ids=chunk_ids,
            metadatas=metadatas
        )
        return len(chunks)

    def semantic_search(self, query: str, limit: int = 2) -> List[Dict[str, Any]]:
        """
        Queries the vector space and returns the closest matching code structural segments.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        # Reformat Chroma's nested dictionary output into a clean, scannable list
        formatted_results = []
        if results and results["documents"]:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                })
        return formatted_results