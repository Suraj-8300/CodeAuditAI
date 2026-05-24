import asyncio
import time

# --- SYNCHRONOUS WAY (The wrong way for AI) ---
def fetch_ai_response_sync(user_id: int):
    print(f"[Sync] User {user_id}: Sent prompt to AI...")
    time.sleep(2)  # Simulates waiting 2 seconds for an LLM
    print(f"[Sync] User {user_id}: Received response!")

def run_sync_demo():
    start_time = time.time()
    for user_id in range(1, 4):
        fetch_ai_response_sync(user_id)
    print(f"⏱️ Total Sync Time: {time.time() - start_time:.2f} seconds\n")


# --- ASYNCHRONOUS WAY (The AI Engineer way) ---
async def fetch_ai_response_async(user_id: int):
    print(f"[Async] User {user_id}: Sent prompt to AI...")
    await asyncio.sleep(2)  # Non-blocking pause. Releases control to event loop.
    print(f"[Async] User {user_id}: Received response!")

async def run_async_demo():
    start_time = time.time()
    # Gather runs all 3 functions concurrently
    await asyncio.gather(
        fetch_ai_response_async(1),
        fetch_ai_response_async(2),
        fetch_ai_response_async(3)
    )
    print(f"⏱️ Total Async Time: {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":
    print("--- Starting Sync Demo ---")
    run_sync_demo()
    
    print("--- Starting Async Demo ---")
    asyncio.run(run_async_demo())