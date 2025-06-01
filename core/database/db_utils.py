import os
import shutil
from datetime import datetime
from urllib.parse import urlparse, unquote

from core.database.base import DATABASE_URL # Changed SQLALCHEMY_DATABASE_URL to DATABASE_URL

TRASH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'trash'))

def get_database_file_path() -> str:
    """
    Parses the DATABASE_URL to get the absolute file path of the SQLite database.
    Assumes the URL is in the format: sqlite:///./path/to/db.sqlite
    """
    if not DATABASE_URL.startswith("sqlite:///./") and not DATABASE_URL.startswith("sqlite:///"):
        raise ValueError(f"Unsupported DATABASE_URL format for SQLite: {DATABASE_URL}. Expected 'sqlite:///./path/to/file.db' or 'sqlite:///path/to/file.db'")
    
    # Remove "sqlite:///" prefix
    if DATABASE_URL.startswith("sqlite:///./"):
        relative_path_part = DATABASE_URL[len("sqlite:///./"):].lstrip('/')
    else: # sqlite:////absolute/path/to/file.db or sqlite:///relative/path/from/project/root
        path_part = DATABASE_URL[len("sqlite:///"):]
        # Check if it's an absolute path
        if os.path.isabs(path_part):
            return os.path.normpath(path_part)
        # If relative, assume it's relative to project root
        relative_path_part = path_part

    # Construct absolute path from the project root (assuming db_utils.py is in core/database/)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    db_file_path = os.path.join(project_root, relative_path_part)
    return os.path.normpath(db_file_path)

def archive_database_file() -> tuple[bool, str]:
    """
    Moves the current database file to a trash directory with a timestamp.
    Creates the trash directory if it doesn't exist.
    Returns a tuple (success_status, message).
    """
    try:
        db_path = get_database_file_path()
        if not os.path.exists(db_path):
            return False, f"Database file not found at {db_path}."

        if not os.path.exists(TRASH_DIR):
            os.makedirs(TRASH_DIR)
            print(f"Created trash directory: {TRASH_DIR}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_filename = os.path.basename(db_path)
        archive_filename = f"{os.path.splitext(db_filename)[0]}_{timestamp}{os.path.splitext(db_filename)[1]}"
        archive_path = os.path.join(TRASH_DIR, archive_filename)

        shutil.move(db_path, archive_path)
        return True, f"Database file '{db_filename}' archived to '{archive_path}'"
    except Exception as e:
        return False, f"Error archiving database file: {e}"

