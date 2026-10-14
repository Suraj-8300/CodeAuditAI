import os
import asyncio
from pydantic import BaseModel
from typing import AsyncGenerator

# 1. The Data Contract
class FileMetadata(BaseModel):
    file_path: str
    extension: str
    size_bytes: int

# 2. The Exclusion Shield
EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}
EXCLUDED_EXTS = {".pyc", ".exe", ".dll", ".so", ".o", ".class", ".zip", ".tar", ".gz"}

# 3. The Core Engine
async def scan_directory(root_path: str) -> AsyncGenerator[FileMetadata, None]:
    """
    Asynchronously walks a directory tree without blocking the main event loop.
    Yields FileMetadata objects for valid files.
    """
    # We use a queue-based approach instead of recursion to prevent call-stack depth limits
    # and to easily yield control back to the asyncio event loop.
    queue = [root_path]
    
    while queue:
        current_dir = queue.pop(0)
        
        try:
            # Offload the blocking disk I/O (directory reading) to a separate thread
            # os.scandir is highly optimized for performance compared to os.walk
            entries = await asyncio.to_thread(lambda d: list(os.scandir(d)), current_dir)
        except (PermissionError, FileNotFoundError):
            continue

        for entry in entries:
            if entry.is_dir():
                # Apply our exclusion filter for directories
                if entry.name not in EXCLUDED_DIRS and not entry.name.startswith('.'):
                    queue.append(entry.path)
                    
            elif entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                
                # Apply our exclusion filter for file types
                if ext not in EXCLUDED_EXTS:
                    yield FileMetadata(
                        file_path=entry.path,
                        extension=ext,
                        size_bytes=entry.stat().st_size
                    )
        
        # Explicitly yield control back to the event loop after processing a directory
        # This guarantees FastAPI can handle other API requests concurrently
        await asyncio.sleep(0)

# 4. Standalone Execution Test
if __name__ == "__main__":
    async def run_test():
        print("🚀 Initiating non-blocking directory scan...")
        # Pointing to the current directory to test it out
        target_dir = "." 
        
        file_count = 0
        total_size = 0
        
        async for file_meta in scan_directory(target_dir):
            print(f"Found: {file_meta.file_path} | Size: {file_meta.size_bytes} bytes")
            file_count += 1
            total_size += file_meta.size_bytes
            
        print(f"\n✅ Scan Complete! Found {file_count} valid files. Total size: {total_size / 1024:.2f} KB")

    # Run the isolated async test
    asyncio.run(run_test())