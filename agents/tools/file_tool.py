import aiofiles
import os
import shutil
from pathlib import Path
from typing import List

def _validate_path(sandbox_path: str, filepath: str) -> Path:
    """
    Resolves the absolute path of sandbox_path / filepath.
    Raises PermissionError if the resolved path is not inside sandbox_path.
    Returns the resolved Path object.
    """
    base = Path(sandbox_path).resolve()
    target = (base / filepath).resolve()
    
    # Check if target is inside base
    if not str(target).startswith(str(base)):
        raise PermissionError(f"Path traversal detected: {filepath} is outside sandbox {sandbox_path}")
    
    return target

async def read_file(sandbox_path: str, filepath: str) -> str:
    """Read file content as string. sandbox_path is the base dir. Raise FileNotFoundError if file doesn't exist. Raise PermissionError if path traversal detected."""
    target = _validate_path(sandbox_path, filepath)
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    async with aiofiles.open(target, mode='r', encoding='utf-8') as f:
        return await f.read()

async def write_file(sandbox_path: str, filepath: str, content: str) -> None:
    """Write content to file. Create parent directories if they don't exist. Raise PermissionError if path traversal detected."""
    target = _validate_path(sandbox_path, filepath)
    target.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(target, mode='w', encoding='utf-8') as f:
        await f.write(content)

async def list_files(sandbox_path: str, subdir: str = "") -> List[str]:
    """Return list of all file paths relative to sandbox_path. If subdir provided, list only within that subdirectory."""
    base = Path(sandbox_path).resolve()
    search_dir = _validate_path(sandbox_path, subdir) if subdir else base
    
    if not search_dir.is_dir():
        return []
    
    paths = []
    # rglob('*') gets all files and directories recursively
    for p in search_dir.rglob('*'):
        if p.is_file():
            paths.append(str(p.relative_to(base)))
    return paths

async def file_exists(sandbox_path: str, filepath: str) -> bool:
    """Return True if file exists within sandbox. Never raises."""
    try:
        target = _validate_path(sandbox_path, filepath)
        return target.is_file()
    except (PermissionError, ValueError):
        return False

async def delete_file(sandbox_path: str, filepath: str) -> None:
    """Delete a file within sandbox. Raise FileNotFoundError if doesn't exist. Raise PermissionError if path traversal detected."""
    target = _validate_path(sandbox_path, filepath)
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # aiofiles doesn't provide os.remove, so we use os.remove directly
    # since it's a quick metadata operation. 
    import asyncio
    await asyncio.to_thread(os.remove, target)

async def copy_file(sandbox_path: str, src: str, dst: str) -> None:
    """Copy file within sandbox. Both src and dst validated against sandbox."""
    src_path = _validate_path(sandbox_path, src)
    dst_path = _validate_path(sandbox_path, dst)
    
    if not src_path.is_file():
        raise FileNotFoundError(f"Source file not found: {src}")
    
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    
    import asyncio
    await asyncio.to_thread(shutil.copy2, src_path, dst_path)
