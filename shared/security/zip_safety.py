import zipfile
from pathlib import Path
from typing import Optional
from shared.security.validation import safe_resolve_path, PathTraversalError

def safe_extract_zip(zip_path: Path, extract_to: Path) -> None:
    """
    Safely extract a ZIP file to a target directory, preventing path traversal (ZIP Slip).
    
    Args:
        zip_path: Path to the ZIP file
        extract_to: Directory to extract into
        
    Raises:
        PathTraversalError: If a malicious path is detected in the ZIP
        zipfile.BadZipFile: If the ZIP file is corrupted
    """
    if not extract_to.exists():
        extract_to.mkdir(parents=True, exist_ok=True)
        
    extract_to_resolved = extract_to.resolve()
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            # Skip directory entries ending with /
            if member.endswith("/"):
                continue
                
            # This will raise PathTraversalError if 'member' tries to escape 'extract_to_resolved'
            safe_resolve_path(extract_to_resolved, member)
            
        # If we get here, all paths are safe
        zf.extractall(extract_to_resolved)
