\
import hashlib
import os
from pathlib import Path

DATA_FILES_DIR = Path(__file__).parent.parent / "data" / "files"
DATA_FILES_DIR.mkdir(parents=True, exist_ok=True)

def save_uploaded_file(uploaded_file_obj) -> str | None:
    """
    Saves an uploaded file to the DATA_FILES_DIR.
    The filename is the SHA256 hash of its content.
    Returns the path to the saved file, or None if saving failed.
    """
    if uploaded_file_obj is None:
        return None
    try:
        file_bytes = uploaded_file_obj.getvalue()
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()
        file_extension = Path(uploaded_file_obj.name).suffix
        save_path = DATA_FILES_DIR / f"{sha256_hash}{file_extension}"
        
        with open(save_path, "wb") as f:
            f.write(file_bytes)
        return str(save_path)
    except Exception as e:
        print(f"Error saving file: {e}")
        return None

def get_file_hash(file_path: str) -> str | None:
    """
    Computes the SHA256 hash of a file.
    Returns the hex digest of the hash, or None if an error occurs.
    """
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            return sha256_hash
    except Exception as e:
        print(f"Error hashing file {file_path}: {e}")
        return None
