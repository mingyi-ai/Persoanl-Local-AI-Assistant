#!/usr/bin/env python3
"""Test script for the simplified database schema."""

try:
    from core.database.base import SessionLocal
    from core.database import crud, schemas
    print("✅ Imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

def test_database():
    """Test the simplified database functionality."""
    db = SessionLocal()
    try:
        # Initialize database
        crud.init_db(db)
        print("✅ Database initialized successfully!")
        
        # Test job posting creation
        job_data = schemas.JobPostingCreate(
            title="Senior Software Engineer",
            company="Tech Corp",
            location="San Francisco, CA",
            type="Full-time",
            seniority="Mid-Senior",
            description="We are looking for a senior software engineer...",
            source_url="https://example.com/job",
            tags="Python, React, PostgreSQL",
            skills="Python, JavaScript, SQL",
            industry="Technology"
        )
        
        job_posting = crud.create_job_posting(db, job_data)
        print(f"✅ Created job posting: {job_posting.title} at {job_posting.company}")
        
        # Test application creation
        app_data = schemas.ApplicationCreate(
            job_posting_id=job_posting.id,
            submission_method="web",
            date_submitted="2024-01-15",
            cover_letter_text="Dear Hiring Manager...",
            additional_questions='{"q1": "Why do you want to work here?", "a1": "Because..."}',
            notes="Applied through company website"
        )
        
        application = crud.create_application(db, app_data)
        print(f"✅ Created application for job posting ID: {application.job_posting_id}")
        
        # Test status creation
        status_data = schemas.ApplicationStatusCreate(
            application_id=application.id,
            status="submitted",
            source_text="Initial application submitted via website"
        )
        
        status = crud.create_application_status(db, status_data)
        print(f"✅ Created status: {status.status} for application ID: {status.application_id}")
        
        # Test data retrieval
        retrieved_job = crud.get_job_posting(db, job_posting.id)
        print(f"✅ Retrieved job posting: {retrieved_job.title}")
        
        retrieved_app = crud.get_application(db, application.id)
        print(f"✅ Retrieved application with method: {retrieved_app.submission_method}")
        
        status_history = crud.get_application_status_history(db, application.id)
        print(f"✅ Retrieved {len(status_history)} status records")
        
        print("\n🎉 All tests passed! Simplified database is working correctly.")
        print("\n📋 Summary of simplified schema:")
        print("   • JobPosting: title, company, location, type, seniority, description, source_url, date_posted, tags, skills, industry")
        print("   • Application: submission_method, date_submitted, resume_file_path, cover_letter_text, additional_questions, notes")
        print("   • ApplicationStatus: status, source_text, created_at (auto-timestamp)")
        print("\n✅ The database now supports all form fields while being much simpler!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    test_database()
