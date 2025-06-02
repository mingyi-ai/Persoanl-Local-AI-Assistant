\
import sys
import os
from datetime import datetime, timedelta
import random
import json

# Adjust path to import from core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from core.database.base import SessionLocal, engine
from core.database import models, schemas, crud

# Sample Data Generation
JOB_TITLES = [
    "Software Engineer", "Senior Software Engineer", "Product Manager", "Data Scientist",
    "UX Designer", "DevOps Engineer", "Marketing Specialist", "Sales Representative"
]
COMPANIES = [
    "Innovatech Ltd.", "Future Solutions Co.", "Alpha Corp", "Beta Systems",
    "Omega Industries", "Quantum Leap Inc.", "Starlight Digital", "Sunrise Software"
]
LOCATIONS = ["New York, NY", "San Francisco, CA", "Austin, TX", "Chicago, IL", "Remote"]
DESCRIPTIONS = [
    "Seeking a motivated individual to join our dynamic team. Responsibilities include developing and maintaining software applications.",
    "We are looking for an experienced professional to lead our product development efforts. Strong analytical skills required.",
    "Join our data science team to work on cutting-edge machine learning models and data analysis projects.",
    "Exciting opportunity for a creative UX designer to shape the user experience of our flagship products."
]
TAG_KEYWORDS = ["tech", "software", "development", "ai", "data", "design", "cloud", "web"]
SKILL_KEYWORDS = [
    "Python", "JavaScript", "Java", "C++", "SQL", "NoSQL", "AWS", "Azure", "Docker", "Kubernetes",
    "React", "Angular", "Vue", "TensorFlow", "PyTorch", "Scikit-learn", "Figma", "Adobe XD"
]
INDUSTRIES = ["Technology", "Finance", "Healthcare", "E-commerce", "Education"]

def generate_random_date_iso(start_days_ago=90, end_days_ago=1):
    days_ago = random.randint(end_days_ago, start_days_ago)
    return (datetime.now() - timedelta(days=days_ago)).isoformat()

def create_test_data(db: Session, num_job_postings: int = 10, apps_per_job: int = 3):
    print(f"Generating {num_job_postings} job postings...")

    for i in range(num_job_postings):
        job_data = schemas.JobPostingCreate(
            title=f"{random.choice(JOB_TITLES)} #{i+1}",
            company=random.choice(COMPANIES),
            location=random.choice(LOCATIONS),
            type=random.choice(list(schemas.JobType)).value,
            seniority=random.choice(list(schemas.SeniorityLevel)).value,
            description=f"{random.choice(DESCRIPTIONS)} This is job posting {i+1}.",
            source_url=f"https://example.com/job/{random.randint(1000,9999)}",
            date_posted=generate_random_date_iso(start_days_ago=60, end_days_ago=5),
            tags=",".join(random.sample(TAG_KEYWORDS, random.randint(1, 3))),
            skills=",".join(random.sample(SKILL_KEYWORDS, random.randint(2, 5))),
            industry=random.choice(INDUSTRIES)
        )
        try:
            job_posting = crud.create_job_posting(db, job_data)
            print(f"  Created Job Posting: {job_posting.title} (ID: {job_posting.id})")

            for j in range(random.randint(1, apps_per_job)):
                app_data = schemas.ApplicationCreate(
                    job_posting_id=job_posting.id,
                    submission_method=random.choice(list(schemas.SubmissionMethod)).value,
                    date_submitted=generate_random_date_iso(start_days_ago=int((datetime.now() - datetime.fromisoformat(job_posting.date_posted)).days)-1, end_days_ago=1) if job_posting.date_posted else generate_random_date_iso(start_days_ago=30, end_days_ago=1),
                    resume_file_path=f"/path/to/resume_applicant_{j+1}_job_{job_posting.id}.pdf" if random.choice([True, False]) else None,
                    cover_letter_file_path=f"/path/to/cover_letter_applicant_{j+1}_job_{job_posting.id}.pdf" if random.choice([True, False]) else None,
                    cover_letter_text="This is a sample cover letter text." if random.choice([True, False]) else None,
                    additional_questions=json.dumps({"question1": "Answer 1", "question2": f"Random answer {random.randint(1,100)}"}) if random.choice([True, False]) else None,
                    notes=f"Some notes for application {j+1} for job {job_posting.id}."
                )
                application = crud.create_application(db, app_data)
                print(f"    Created Application ID: {application.id} for Job ID: {job_posting.id}")

                # Create status history for the application
                statuses_to_add = random.sample(list(schemas.ApplicationStatus), random.randint(1, 4))
                # Ensure 'submitted' is usually the first status if multiple are added
                if len(statuses_to_add) > 1 and schemas.ApplicationStatus.SUBMITTED not in statuses_to_add:
                    statuses_to_add.insert(0, schemas.ApplicationStatus.SUBMITTED)
                elif not statuses_to_add: # ensure at least one status
                     statuses_to_add.append(schemas.ApplicationStatus.SUBMITTED)


                # Sort statuses by a typical progression (simplified)
                status_order = {s.value: k for k, s in enumerate(schemas.ApplicationStatus)}
                
                # Ensure submitted is first if present
                if schemas.ApplicationStatus.SUBMITTED.value in [s.value for s in statuses_to_add]:
                    statuses_to_add.sort(key=lambda s: (s.value != schemas.ApplicationStatus.SUBMITTED.value, status_order.get(s.value, 99)))
                else: # if submitted is not there, just sort by enum order
                    statuses_to_add.sort(key=lambda s: status_order.get(s.value, 99))


                for status_enum in statuses_to_add:
                    status_data = schemas.ApplicationStatusCreate(
                        application_id=application.id,
                        status=status_enum.value,
                        source_text=f"Status updated to {status_enum.value} via test script."
                    )
                    # The 'created_at' for status is server_default, but for realism in sequence:
                    # We don't directly control 'created_at' here as it's server_default.
                    # The order of creation implies sequence.
                    status_record = crud.create_application_status(db, status_data)
                    print(f"      Added Status: {status_record.status} for Application ID: {application.id}")
        except Exception as e:
            print(f"Error creating job posting or related data: {e}")
            db.rollback() # Rollback for this specific job posting and its children if error occurs
            continue # Continue to the next job posting

if __name__ == "__main__":
    print("Initializing database session...")
    db = SessionLocal()
    try:
        print("Ensuring database tables are created...")
        # This will create tables if they don't exist, based on your models.
        models.Base.metadata.create_all(bind=engine)

        print("Populating test data...")
        create_test_data(db, num_job_postings=15, apps_per_job=4) # Generate 15 job postings, up to 4 apps each
        
        db.commit() # Commit all changes at the end
        print("\\nTest data populated successfully.")
    except Exception as e:
        print(f"An error occurred during the process: {e}")
        db.rollback()
    finally:
        print("Closing database session.")
        db.close()

