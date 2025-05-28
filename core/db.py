import sqlite3
from datetime import datetime
from pathlib import Path

DATABASE_PATH = Path(__file__).parent.parent / "data" / "job_applications.db"

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE NOT NULL,
        sha256_hash TEXT UNIQUE NOT NULL,
        upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_id INTEGER,
        job_description TEXT NOT NULL,
        cover_letter_text TEXT,
        submission_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        ai_score REAL,
        ai_reasoning TEXT,
        FOREIGN KEY (resume_id) REFERENCES resumes (id)
    )
    """)
    conn.commit()
    conn.close()

def add_resume(file_path: str, sha256_hash: str) -> int | None:
    """Adds a resume to the database. Returns the resume ID."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO resumes (file_path, sha256_hash) VALUES (?, ?)", (file_path, sha256_hash))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Resume with this hash or path already exists
        cursor.execute("SELECT id FROM resumes WHERE sha256_hash = ?", (sha256_hash,))
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error adding resume: {e}")
        return None
    finally:
        conn.close()

def add_job_application(resume_id: int, job_description: str, cover_letter_text: str | None, ai_score: float | None, ai_reasoning: str | None) -> int | None:
    """Adds a job application to the database. Returns the application ID."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO job_applications (resume_id, job_description, cover_letter_text, ai_score, ai_reasoning, submission_timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (resume_id, job_description, cover_letter_text, ai_score, ai_reasoning, datetime.now()))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error adding job application: {e}")
        return None
    finally:
        conn.close()

def get_all_applications():
    """Retrieves all job applications with resume file paths."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT ja.id, r.file_path, ja.job_description, ja.cover_letter_text, ja.submission_timestamp, ja.ai_score, ja.ai_reasoning
        FROM job_applications ja
        JOIN resumes r ON ja.resume_id = r.id
        ORDER BY ja.submission_timestamp DESC
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching applications: {e}")
        return []
    finally:
        conn.close()

# Initialize the database when this module is loaded
init_db()
