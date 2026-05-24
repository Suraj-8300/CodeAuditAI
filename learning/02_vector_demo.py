import chromadb
from chromadb.utils import embedding_functions

def run_vector_sandbox():
    # 1. Initialize a local, on-disk database client
    print("📦 Initializing local ChromaDB client...")
    chroma_client = chromadb.PersistentClient(path="./learning/chroma_db_storage")

    # 2. Use a default, built-in embedding function (runs locally)
    default_ef = embedding_functions.DefaultEmbeddingFunction()

    # 3. Create a collection (think of it like a table in SQL, but for vectors)
    collection = chroma_client.get_or_create_collection(
        name="sample_code_chunks", 
        embedding_function=default_ef
    )

    # 4. Define some mock code snippets (our chunks)
    mock_code_chunks = [
        "def connect_postgres(): return psycopg2.connect(dsn)",
        "def calculate_total_price(cart): return sum(item.price for item in cart)",
        "def verify_jwt_token(token): return jwt.decode(token, SECRET_KEY)",
        "def upload_to_s3(file_bytes): s3.upload_fileobj(file_bytes, bucket)"
    ]

    # Unique IDs for our chunks
    chunk_ids = ["chunk_db", "chunk_logic", "chunk_auth", "chunk_storage"]

    # 5. Add them to the database (Chroma automatically calculates the numerical vectors)
    print("📥 Indexing code chunks into mathematical space...")
    collection.add(
        documents=mock_code_chunks,
        ids=chunk_ids
    )
    print("✅ Indexing complete!")

    # 6. Query the database semantically
    # Notice we aren't using exact keyword matching; we are querying by meaning.
    query = "how amazon shopping app gather products?"
    print(f"\n🔍 Querying database for: '{query}'")
    
    results = collection.query(
        query_texts=[query],
        n_results=1  # Bring back the single closest match
    )

    print("\n🎯 Closest Match Found:")
    print(f"-> ID: {results['ids'][0][0]}")
    print(f"-> Document Contents: '{results['documents'][0][0]}'")
    print(f"-> Distance Score: {results['distances'][0][0]:.4f} (Lower means closer meaning)")

if __name__ == "__main__":
    run_vector_sandbox()