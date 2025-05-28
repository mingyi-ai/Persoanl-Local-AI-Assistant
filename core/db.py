import sqlite3
from datetime import datetime
from pathlib import Path
import json # Added import

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
        job_title TEXT NOT NULL,
        company TEXT,
        resume_id INTEGER,
        job_description TEXT,
        cover_letter_path TEXT,
        submission_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        ai_score REAL,
        ai_reasoning TEXT,
        outcome TEXT DEFAULT 'pending',
        notes TEXT,
        custom_fields TEXT,
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

def add_job_application(
    job_title: str,
    company: str | None,
    resume_id: int | None, # Made optional to allow manual entry without resume
    job_description: str | None,
    cover_letter_path: str | None,
    ai_score: float | None,
    ai_reasoning: str | None,
    outcome: str = 'pending',
    notes: str | None = None,
    submission_date: datetime | None = None,
    custom_fields: dict | None = None # Added custom_fields
) -> int | None:
    """Adds a job application to the database. Returns the application ID."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    if submission_date is None:
        submission_date = datetime.now()
    
    custom_fields_json = json.dumps(custom_fields) if custom_fields else None

    try:
        cursor.execute("""
        INSERT INTO job_applications (
            job_title, company, resume_id, job_description, cover_letter_path,
            ai_score, ai_reasoning, outcome, notes, submission_date, custom_fields
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_title, company, resume_id, job_description, cover_letter_path,
            ai_score, ai_reasoning, outcome, notes, submission_date, custom_fields_json
        ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error adding job application: {e}")
        return None
    finally:
        conn.close()

def get_all_applications():
    """Retrieves all job applications with resume file paths and custom fields."""
    conn = sqlite3.connect(DATABASE_PATH)
    # So that we can access columns by name
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    try:
        # Use LEFT JOIN to include applications even if resume_id is NULL
        cursor.execute("""
        SELECT 
            ja.id, 
            ja.job_title, 
            ja.company, 
            r.file_path as resume_file_path, 
            ja.job_description, 
            ja.cover_letter_path, 
            ja.submission_date, 
            ja.ai_score, 
            ja.ai_reasoning, 
            ja.outcome, 
            ja.notes,
            ja.custom_fields 
        FROM job_applications ja
        LEFT JOIN resumes r ON ja.resume_id = r.id
        ORDER BY ja.submission_date DESC
        """)
        applications = []
        for row in cursor.fetchall():
            app_dict = dict(row)
            if app_dict['custom_fields']:
                try:
                    app_dict['custom_fields'] = json.loads(app_dict['custom_fields'])
                except json.JSONDecodeError:
                    app_dict['custom_fields'] = {} # Default to empty dict if JSON is invalid
            else:
                app_dict['custom_fields'] = {} # Default to empty dict if NULL
            applications.append(app_dict)
        return applications
    except Exception as e:
        print(f"Error fetching applications: {e}")
        return []
    finally:
        conn.close()

def get_application_by_id(application_id: int):
    """Retrieves a specific job application by its ID, including custom fields."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # So that we can access columns by name
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT 
            ja.id, 
            ja.job_title, 
            ja.company, 
            r.file_path as resume_file_path, 
            ja.job_description, 
            ja.cover_letter_path, 
            ja.submission_date, 
            ja.ai_score, 
            ja.ai_reasoning, 
            ja.outcome, 
            ja.notes,
            ja.resume_id,
            ja.custom_fields
        FROM job_applications ja
        LEFT JOIN resumes r ON ja.resume_id = r.id
        WHERE ja.id = ?
        """, (application_id,))
        row = cursor.fetchone()
        if row:
            app_dict = dict(row)
            if app_dict['custom_fields']:
                try:
                    app_dict['custom_fields'] = json.loads(app_dict['custom_fields'])
                except json.JSONDecodeError:
                    app_dict['custom_fields'] = {} # Default to empty dict if JSON is invalid
            else:
                app_dict['custom_fields'] = {} # Default to empty dict if NULL
            return app_dict
        return None
    except Exception as e:
        print(f"Error fetching application by ID {application_id}: {e}")
        return None
    finally:
        conn.close()

def update_job_application(
    application_id: int,
    job_title: str,
    company: str | None,
    job_description: str | None,
    outcome: str,
    notes: str | None,
    resume_id: int | None = None, 
    cover_letter_path: str | None = None, 
    submission_date: datetime | None = None,
    custom_fields: dict | None = None # Added custom_fields
) -> bool:
    """Updates an existing job application."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    set_clauses = []
    sql_params = []

    if job_title is not None:
        set_clauses.append("job_title = ?")
        sql_params.append(job_title)
    if company is not None: 
        set_clauses.append("company = ?")
        sql_params.append(company)
    
    set_clauses.append("resume_id = ?") # Always include resume_id, even if None
    sql_params.append(resume_id)

    if job_description is not None: 
        set_clauses.append("job_description = ?")
        sql_params.append(job_description)
    if cover_letter_path is not None: 
        set_clauses.append("cover_letter_path = ?")
        sql_params.append(cover_letter_path)
    if submission_date is not None:
        set_clauses.append("submission_date = ?")
        sql_params.append(submission_date)
    if outcome is not None:
        set_clauses.append("outcome = ?")
        sql_params.append(outcome)
    if notes is not None: 
        set_clauses.append("notes = ?")
        sql_params.append(notes)
    
    if custom_fields is not None:
        set_clauses.append("custom_fields = ?")
        sql_params.append(json.dumps(custom_fields))

    if not set_clauses:
        print("No fields to update.")
        return False

    sql = f"UPDATE job_applications SET {', '.join(set_clauses)} WHERE id = ?"
    sql_params.append(application_id)
    
    try:
        cursor.execute(sql, tuple(sql_params))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating job application {application_id}: {e}")
        return False
    finally:
        conn.close()

def get_all_resumes():
    """Retrieves all resumes (id and file_path) from the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, file_path FROM resumes ORDER BY upload_timestamp DESC")
        resumes = cursor.fetchall()
        return [dict(row) for row in resumes]
    except Exception as e:
        print(f"Error fetching all resumes: {e}")
        return []
    finally:
        conn.close()

def delete_job_application(application_id: int) -> bool:
    """Deletes a job application from the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM job_applications WHERE id = ?", (application_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting job application {application_id}: {e}")
        return False
    finally:
        conn.close()

# Initialize the database when this module is loaded
init_db()
