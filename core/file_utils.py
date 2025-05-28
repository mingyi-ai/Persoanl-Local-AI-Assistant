\
import hashlib
import os
from pathlib import Path

DATA_FILES_DIR = Path(__file__).parent.parent / "data" / "files"
DATA_FILES_DIR.mkdir(parents=True, exist_ok=True)

COVER_LETTERS_DIR = DATA_FILES_DIR / "cover_letters"
COVER_LETTERS_DIR.mkdir(parents=True, exist_ok=True)

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

def save_cover_letter(cover_letter_content: str, filename_prefix: str) -> str | None:
    """
    Saves cover letter content to a file in the COVER_LETTERS_DIR.
    The filename will be <filename_prefix>_cover_letter.txt.
    Returns the path to the saved file, or None if saving failed.
    """
    if not cover_letter_content or not filename_prefix:
        return None
    try:
        # Sanitize filename_prefix to remove characters not suitable for filenames
        safe_prefix = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in filename_prefix).strip()
        safe_prefix = safe_prefix.replace(' ', '_') # Replace spaces with underscores
        
        # Ensure the prefix is not too long (optional, but good practice)
        max_prefix_len = 50 
        if len(safe_prefix) > max_prefix_len:
            safe_prefix = safe_prefix[:max_prefix_len]

        # Remove any trailing underscores that might result from sanitization
        while safe_prefix.endswith('_'):
            safe_prefix = safe_prefix[:-1]
        
        if not safe_prefix: # If prefix becomes empty after sanitization
            safe_prefix = "cover_letter"

        filename = f"{safe_prefix}_cover_letter.txt"
        save_path = COVER_LETTERS_DIR / filename
        
        # Ensure filename is unique if it already exists by appending a number
        counter = 1
        original_save_path = save_path
        while save_path.exists():
            filename = f"{safe_prefix}_cover_letter_{counter}.txt"
            save_path = COVER_LETTERS_DIR / filename
            counter += 1
            if counter > 100: # Safety break to prevent infinite loop
                print(f"Error: Could not find a unique filename for {original_save_path.name} after 100 attempts.")
                return None

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(cover_letter_content)
        return str(save_path)
    except Exception as e:
        print(f"Error saving cover letter: {e}")
        return None
