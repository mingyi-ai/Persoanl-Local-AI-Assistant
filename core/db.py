import sqlite3
from datetime import datetime, date # Added date
from pathlib import Path
import json
import hashlib # For description_hash

DATABASE_PATH = Path(__file__).parent.parent / "data" / "job_applications.db"

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # 1. job_postings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_postings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT,
        description TEXT,
        source_url TEXT,
        date_posted TEXT, -- ISO text
        date_submitted TEXT, -- ISO text (when the application linked to this posting was submitted)
        questions_answered TEXT,
        description_hash TEXT UNIQUE -- Hash of key job posting details to avoid duplicates
    )
    """)

    # 2. files
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_name TEXT,
        stored_path TEXT NOT NULL UNIQUE, -- Assuming stored_path should be unique
        sha256 TEXT NOT NULL UNIQUE,
        file_type TEXT NOT NULL CHECK(file_type IN ('resume', 'cover_letter', 'attachment', 'other'))
    )
    """)

    # 3. applications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_posting_id INTEGER NOT NULL,
        resume_file_id INTEGER, -- Can be NULL if no resume submitted or not tracked
        cover_letter_file_id INTEGER, -- Can be NULL
        submission_method TEXT CHECK(submission_method IN ('web', 'email', 'referral', 'other')),
        notes TEXT,
        FOREIGN KEY (job_posting_id) REFERENCES job_postings (id) ON DELETE CASCADE,
        FOREIGN KEY (resume_file_id) REFERENCES files (id) ON DELETE SET NULL,
        FOREIGN KEY (cover_letter_file_id) REFERENCES files (id) ON DELETE SET NULL
    )
    """)

    # 4. application_status_history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        timestamp TEXT NOT NULL, -- ISO datetime
        source_text TEXT,
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
    )
    """)

    # 5. contacts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL, -- Link contact to a specific application context
        name TEXT NOT NULL,
        role TEXT,
        email TEXT,
        phone TEXT,
        first_reached TEXT, -- ISO date
        last_contacted TEXT, -- ISO date
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
    )
    """)

    # 6. emails
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        direction TEXT NOT NULL CHECK(direction IN ('sent', 'received')),
        timestamp TEXT NOT NULL, -- ISO datetime
        subject TEXT,
        body TEXT,
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
    )
    """)

    # 7. parsed_metadata
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parsed_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_posting_id INTEGER NOT NULL UNIQUE, -- Assuming one metadata set per job posting
        tags TEXT,          -- comma-separated or JSON
        tech_stacks TEXT,   -- comma-separated or JSON
        seniority TEXT,
        industry TEXT,
        FOREIGN KEY (job_posting_id) REFERENCES job_postings (id) ON DELETE CASCADE
    )
    """)

    # 8. tags (normalized tagging system)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tags (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE
    )
    """)

    # Junction table for many-to-many relationship between applications and tags
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_tags (
      application_id INTEGER NOT NULL,
      tag_id INTEGER NOT NULL,
      PRIMARY KEY (application_id, tag_id),
      FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE,
      FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

def generate_description_hash(title: str, company: str, description: str) -> str:
    """Generates a SHA256 hash for core job posting details."""
    hasher = hashlib.sha256()
    hasher.update(title.lower().encode('utf-8'))
    hasher.update(company.lower().encode('utf-8'))
    hasher.update(description.lower().encode('utf-8')) # Consider normalizing description
    return hasher.hexdigest()

# --- File Management ---
def check_file_exists_by_hash(sha256_hash: str) -> tuple[int, str] | None:
    """Checks if a file with the given SHA256 hash exists. Returns (id, stored_path) or None."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, stored_path FROM files WHERE sha256 = ?", (sha256_hash,))
        result = cursor.fetchone()
        return result if result else None
    except Exception as e:
        print(f"Error checking file existence by hash: {e}")
        return None
    finally:
        conn.close()

def add_file(original_name: str, stored_path: str, sha256: str, file_type: str) -> int | None:
    """Adds a file to the database if it doesn't already exist by hash. Returns the file ID."""
    existing_file = check_file_exists_by_hash(sha256)
    if existing_file:
        return existing_file[0] # Return ID of existing file

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO files (original_name, stored_path, sha256, file_type) VALUES (?, ?, ?, ?)",
            (original_name, stored_path, sha256, file_type)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e: # Handles unique constraint violations (e.g. stored_path)
        print(f"Integrity error adding file (likely duplicate stored_path if hash was new): {e}")
        # Attempt to fetch by stored_path if hash was somehow new but path wasn't
        cursor.execute("SELECT id FROM files WHERE stored_path = ?", (stored_path,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error adding file: {e}")
        return None
    finally:
        conn.close()

# --- Job Posting Management ---
def add_job_posting(title: str, company: str, description: str, location: str | None = None,
                    source_url: str | None = None, date_posted: str | None = None,
                    questions_answered: str | None = None) -> int | None:
    """Adds a job posting. Returns the job posting ID."""
    desc_hash = generate_description_hash(title, company, description)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM job_postings WHERE description_hash = ?", (desc_hash,))
        existing = cursor.fetchone()
        if existing:
            return existing[0]

        cursor.execute(
            """INSERT INTO job_postings (title, company, location, description, source_url, date_posted, questions_answered, description_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, company, location, description, source_url, date_posted, questions_answered, desc_hash)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Should be caught by the check above, but as a safeguard
        cursor.execute("SELECT id FROM job_postings WHERE description_hash = ?", (desc_hash,))
        existing = cursor.fetchone()
        return existing[0] if existing else None
    except Exception as e:
        print(f"Error adding job posting: {e}")
        return None
    finally:
        conn.close()

# --- Application Management ---
def add_application(job_posting_id: int, resume_file_id: int | None, cover_letter_file_id: int | None,
                    submission_method: str | None, notes: str | None, date_submitted: str | None = None) -> int | None:
    """Adds an application. Returns the application ID."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if date_submitted is None:
        date_submitted = datetime.utcnow().isoformat()

    try:
        cursor.execute(
            """INSERT INTO applications (job_posting_id, resume_file_id, cover_letter_file_id, submission_method, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (job_posting_id, resume_file_id, cover_letter_file_id, submission_method, notes)
        )
        app_id = cursor.lastrowid
        
        # Update date_submitted in job_postings table for this application
        cursor.execute(
            "UPDATE job_postings SET date_submitted = ? WHERE id = ?",
            (date_submitted, job_posting_id)
        )
        conn.commit()
        return app_id
    except Exception as e:
        print(f"Error adding application: {e}")
        return None
    finally:
        conn.close()

# --- Application Status Management ---
def log_application_status(application_id: int, status: str, source_text: str | None = None, timestamp: str | None = None):
    """Logs a new status for an application."""
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO application_status_history (application_id, status, timestamp, source_text) VALUES (?, ?, ?, ?)",
            (application_id, status, timestamp, source_text)
        )
        conn.commit()
    except Exception as e:
        print(f"Error logging application status: {e}")
    finally:
        conn.close()

def get_latest_status_for_application(application_id: int) -> dict | None:
    """Retrieves the most recent status for a given application."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            """SELECT status, timestamp, source_text FROM application_status_history
               WHERE application_id = ? ORDER BY timestamp DESC LIMIT 1""",
            (application_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error getting latest status for application {application_id}: {e}")
        return None
    finally:
        conn.close()

def get_applications_with_latest_status(filter_status: str | None = None) -> list[dict]:
    """
    Retrieves all applications, joining with job posting details, file names,
    and their latest status. Optionally filters by the latest status.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
    SELECT
        app.id as application_id,
        jp.id as job_posting_id,
        jp.title as job_title,
        jp.company as job_company,
        jp.date_submitted as job_date_submitted,
        res_file.original_name as resume_name,
        cl_file.original_name as cover_letter_name,
        app.submission_method,
        app.notes as application_notes,
        latest_status.status as current_status,
        latest_status.timestamp as status_timestamp
    FROM applications app
    JOIN job_postings jp ON app.job_posting_id = jp.id
    LEFT JOIN files res_file ON app.resume_file_id = res_file.id
    LEFT JOIN files cl_file ON app.cover_letter_file_id = cl_file.id
    LEFT JOIN (
        SELECT application_id, status, timestamp
        FROM application_status_history h
        WHERE h.id = (SELECT MAX(id) FROM application_status_history WHERE application_id = h.application_id) -- More robust for same timestamp
    ) latest_status ON app.id = latest_status.application_id
    """

    params = []
    if filter_status:
        query += " WHERE latest_status.status = ?"
        params.append(filter_status)
    
    query += " ORDER BY jp.date_submitted DESC, app.id DESC"

    try:
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting applications with latest status: {e}")
        return []
    finally:
        conn.close()

def get_applications_by_status(status: str) -> list[dict]:
    """Filters applications by their latest status."""
    return get_applications_with_latest_status(filter_status=status)


# --- Tag Management ---
def add_tag(name: str) -> int | None:
    """Adds a tag. Returns tag ID."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO tags (name) VALUES (?)", (name.lower(),))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Tag name is unique
        cursor.execute("SELECT id FROM tags WHERE name = ?", (name.lower(),))
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error adding tag '{name}': {e}")
        return None
    finally:
        conn.close()

def link_tag_to_application(application_id: int, tag_id: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO application_tags (application_id, tag_id) VALUES (?, ?)", (application_id, tag_id))
        conn.commit()
    except sqlite3.IntegrityError: # PK violation means link already exists
        pass
    except Exception as e:
        print(f"Error linking tag {tag_id} to app {application_id}: {e}")
    finally:
        conn.close()

def get_tags_for_application(application_id: int) -> list[dict]:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT t.id, t.name FROM tags t
            JOIN application_tags at ON t.id = at.tag_id
            WHERE at.application_id = ?
        """, (application_id,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting tags for application {application_id}: {e}")
        return []
    finally:
        conn.close()

# --- Parsed Metadata Management ---
def add_or_update_parsed_metadata(job_posting_id: int, tags: str | None = None, tech_stacks: str | None = None,
                                  seniority: str | None = None, industry: str | None = None) -> int | None:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        # Check if metadata already exists for this job_posting_id
        cursor.execute("SELECT id FROM parsed_metadata WHERE job_posting_id = ?", (job_posting_id,))
        existing_metadata = cursor.fetchone()

        if existing_metadata:
            # Update existing metadata
            metadata_id = existing_metadata[0]
            updates = []
            params = []
            if tags is not None:
                updates.append("tags = ?")
                params.append(tags)
            if tech_stacks is not None:
                updates.append("tech_stacks = ?")
                params.append(tech_stacks)
            if seniority is not None:
                updates.append("seniority = ?")
                params.append(seniority)
            if industry is not None:
                updates.append("industry = ?")
                params.append(industry)
            
            if not updates: # Nothing to update
                return metadata_id

            params.append(metadata_id)
            cursor.execute(f"UPDATE parsed_metadata SET {', '.join(updates)} WHERE id = ?", tuple(params))
        else:
            # Insert new metadata
            cursor.execute(
                """INSERT INTO parsed_metadata (job_posting_id, tags, tech_stacks, seniority, industry)
                   VALUES (?, ?, ?, ?, ?)""",
                (job_posting_id, tags, tech_stacks, seniority, industry)
            )
            metadata_id = cursor.lastrowid
        conn.commit()
        return metadata_id
    except Exception as e:
        print(f"Error adding/updating parsed metadata for job_posting_id {job_posting_id}: {e}")
        return None
    finally:
        conn.close()

def get_parsed_metadata(job_posting_id: int) -> dict | None:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM parsed_metadata WHERE job_posting_id = ?", (job_posting_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error getting parsed metadata for job_posting_id {job_posting_id}: {e}")
        return None
    finally:
        conn.close()

def get_files_by_type(file_type: str) -> list[dict]:
    """Retrieves all files of a specific type (e.g., 'resume', 'cover_letter')."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, original_name, stored_path FROM files WHERE file_type = ? ORDER BY original_name", (file_type,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching files by type {file_type}: {e}")
        return []
    finally:
        conn.close()

def get_full_application_details(application_id: int) -> dict | None:
    """
    Retrieves comprehensive details for a single application,
    including job posting info, resume/cover letter file names,
    latest status, parsed metadata, and tags.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    application_details = {}

    try:
        # 1. Get basic application and job posting info
        cursor.execute(
            """SELECT
                app.id as application_id,
                app.notes as application_notes,
                app.submission_method,
                jp.id as job_posting_id,
                jp.title as job_title,
                jp.company as job_company,
                jp.location as job_location,
                jp.description as job_description,
                jp.source_url as job_source_url,
                jp.date_posted as job_date_posted,
                jp.date_submitted as job_date_submitted,
                jp.questions_answered as job_questions_answered,
                app.resume_file_id,
                app.cover_letter_file_id,
                res_file.original_name as resume_original_name,
                res_file.stored_path as resume_stored_path,
                cl_file.original_name as cover_letter_original_name,
                cl_file.stored_path as cover_letter_stored_path
            FROM applications app
            JOIN job_postings jp ON app.job_posting_id = jp.id
            LEFT JOIN files res_file ON app.resume_file_id = res_file.id
            LEFT JOIN files cl_file ON app.cover_letter_file_id = cl_file.id
            WHERE app.id = ?""",
            (application_id,)
        )
        main_info = cursor.fetchone()
        if not main_info:
            return None
        application_details.update(dict(main_info))

        # 2. Get latest status
        latest_status = get_latest_status_for_application(application_id)
        application_details['latest_status'] = latest_status if latest_status else {}

        # 3. Get parsed metadata for the job posting
        if application_details.get('job_posting_id'):
            metadata = get_parsed_metadata(application_details['job_posting_id'])
            application_details['parsed_metadata'] = metadata if metadata else {}

        # 4. Get tags for the application
        tags = get_tags_for_application(application_id)
        application_details['tags'] = tags if tags else []
        
        # 5. Get all status history
        cursor.execute(
            """SELECT id, status, timestamp, source_text
            FROM application_status_history
            WHERE application_id = ?
            ORDER BY timestamp DESC""",
            (application_id,)
        )
        application_details['status_history'] = [dict(row) for row in cursor.fetchall()]

        return application_details
    except Exception as e:
        print(f"Error fetching full application details for ID {application_id}: {e}")
        return None
    finally:
        conn.close()

def update_job_posting_details(
    job_posting_id: int, title: str | None = None, company: str | None = None,
    location: str | None = None, description: str | None = None, source_url: str | None = None,
    date_posted: str | None = None, questions_answered: str | None = None
) -> bool:
    """Updates specific fields of a job posting."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    fields_to_update = []
    params = []

    if title is not None: fields_to_update.append("title = ?"); params.append(title)
    if company is not None: fields_to_update.append("company = ?"); params.append(company)
    if location is not None: fields_to_update.append("location = ?"); params.append(location)
    if description is not None: fields_to_update.append("description = ?"); params.append(description)
    if source_url is not None: fields_to_update.append("source_url = ?"); params.append(source_url)
    if date_posted is not None: fields_to_update.append("date_posted = ?"); params.append(date_posted)
    if questions_answered is not None: fields_to_update.append("questions_answered = ?"); params.append(questions_answered)

    if not fields_to_update:
        return True # No changes needed

    params.append(job_posting_id)
    sql = f"UPDATE job_postings SET {', '.join(fields_to_update)} WHERE id = ?"
    try:
        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating job posting {job_posting_id}: {e}")
        return False
    finally:
        conn.close()

def update_application_record(
    application_id: int, resume_file_id: int | None = None, cover_letter_file_id: int | None = None,
    submission_method: str | None = None, notes: str | None = None,
    update_resume_id: bool = False, update_cl_id: bool = False # Flags to explicitly allow setting ID to NULL
) -> bool:
    """Updates specific fields of an application record."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    fields_to_update = []
    params = []

    if update_resume_id:
        fields_to_update.append("resume_file_id = ?"); params.append(resume_file_id)
    elif resume_file_id is not None:
        fields_to_update.append("resume_file_id = ?"); params.append(resume_file_id)

    if update_cl_id:
        fields_to_update.append("cover_letter_file_id = ?"); params.append(cover_letter_file_id)
    elif cover_letter_file_id is not None:
        fields_to_update.append("cover_letter_file_id = ?"); params.append(cover_letter_file_id)
        
    if submission_method is not None: fields_to_update.append("submission_method = ?"); params.append(submission_method)
    if notes is not None: fields_to_update.append("notes = ?"); params.append(notes)

    if not fields_to_update:
        return True # No changes needed

    params.append(application_id)
    sql = f"UPDATE applications SET {', '.join(fields_to_update)} WHERE id = ?"
    try:
        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating application record {application_id}: {e}")
        return False
    finally:
        conn.close()

def delete_application_record(application_id: int) -> bool:
    """
    Deletes an application record from the 'applications' table.
    Related records in 'application_status_history', 'contacts', 'emails', 
    and 'application_tags' should be deleted due to ON DELETE CASCADE.
    Job postings and files are not deleted by this function.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM applications WHERE id = ?", (application_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting application record {application_id}: {e}")
        return False
    finally:
        conn.close()

# IMPORTANT: If the schema has changed significantly, you might need to delete
# the old job_applications.db file for these changes to take effect without errors.
init_db()
# print("Database initialized with new schema.") # For verification
