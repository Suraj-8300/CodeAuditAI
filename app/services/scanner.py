import os
import asyncio
from pathlib import Path
from pydantic import BaseModel
from typing import AsyncGenerator, Set

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
    Enforces strict canonical boundary containment, disables symlink following,
    and tracks visited paths to prevent symlink cycle resource exhaustion.
    """
    try:
        resolved_root = Path(root_path).resolve(strict=True)
    except (FileNotFoundError, RuntimeError, OSError):
        return

    visited_paths: Set[str] = {str(resolved_root)}
    queue = [resolved_root]
    
    while queue:
        current_dir = queue.pop(0)
        
        try:
            # Offload the blocking disk I/O (directory reading) to a separate thread
            entries = await asyncio.to_thread(lambda d: list(os.scandir(str(d))), current_dir)
        except (PermissionError, FileNotFoundError, OSError):
            continue

        for entry in entries:
            try:
                # Do not follow symlinks to avoid directory traversal and infinite recursion
                is_directory = entry.is_dir(follow_symlinks=False)
                is_file = entry.is_file(follow_symlinks=False)
            except OSError:
                continue

            entry_path = Path(entry.path)

            # Strict boundary validation: verify containment inside resolved_root
            try:
                canonical_entry = entry_path.resolve(strict=False)
                if not canonical_entry.is_relative_to(resolved_root):
                    continue
            except (ValueError, RuntimeError, OSError):
                continue

            if is_directory:
                # Apply exclusion filter for directories
                if entry.name not in EXCLUDED_DIRS and not entry.name.startswith('.'):
                    real_str = str(canonical_entry)
                    if real_str not in visited_paths:
                        visited_paths.add(real_str)
                        queue.append(entry_path)
                    
            elif is_file:
                ext = os.path.splitext(entry.name)[1].lower()
                
                # Apply exclusion filter for file types
                if ext not in EXCLUDED_EXTS:
                    try:
                        file_size = entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        file_size = 0
                    yield FileMetadata(
                        file_path=str(entry_path),
                        extension=ext,
                        size_bytes=file_size
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