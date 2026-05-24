from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
import chromadb

def chunk_and_index_real_code():
    # 1. Read our actual production file
    target_file = "app/main.py"
    print(f"📖 Reading target file: {target_file}...")
    with open(target_file, "r") as f:
        source_code = f.read()

    # 2. Initialize the Python-aware text splitter
    # chunk_size: Target character length of each chunk
    # chunk_overlap: How many characters to repeat between chunks so context isn't lost at the boundaries
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=250, 
        chunk_overlap=30
    )

    # 3. Split the code
    chunks = splitter.split_text(source_code)
    print(f"✂️ Successfully split code into {len(chunks)} distinct structural chunks.\n")

    # 4. Connect to our persistent database
    chroma_client = chromadb.PersistentClient(path="./learning/chroma_db_storage")
    collection = chroma_client.get_or_create_collection(name="production_code_base")

    # 5. Prepare data for indexing
    # We create unique IDs based on the filename and an index number
    chunk_ids = [f"main_py_chunk_{i}" for i in range(len(chunks))]
    
    # Metadata helps us filter results later (e.g., only search specific files)
    metadata_list = [{"source": target_file} for _ in range(len(chunks))]

    print("📥 Committing chunks to 'production_code_base' collection...")
    collection.add(
        documents=chunks,
        ids=chunk_ids,
        metadatas=metadata_list
    )
    print("✅ Local codebase indexing complete!")

    # 6. Test the real retrieval
    query = "Where is the asynchronous analyze route defined?"
    print(f"\n🔍 Testing Semantic Search Query: '{query}'")
    
    search_results = collection.query(
        query_texts=[query],
        n_results=1
    )

    print("\n🎯 Retracted Production Snippet:")
    print("--------------------------------------------------")
    print(search_results['documents'][0][0])
    print("--------------------------------------------------")

if __name__ == "__main__":
    chunk_and_index_real_code()