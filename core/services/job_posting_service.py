"""Service layer for job posting operations."""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ..database import models, schemas, crud

class JobPostingService:
    @staticmethod
    def add_job_posting_with_details(
        db: Session,
        title: str,
        company: str, 
        description: str,
        location: Optional[str] = None,
        source_url: Optional[str] = None,
        date_posted: Optional[str] = None,
        questions_answered: Optional[str] = None,
        parsed_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[models.JobPosting]:
        """Add a new job posting with the given details."""
        job_posting = crud.create_job_posting(
            db,
            schemas.JobPostingCreate(
                title=title,
                company=company,
                description=description,
                location=location,
                source_url=source_url,
                date_posted=date_posted,
                questions_answered=questions_answered
            )
        )
        
        if job_posting and parsed_metadata:
            crud.update_or_create_parsed_metadata(db, job_posting.id, parsed_metadata)
                
        return job_posting

    @staticmethod
    def generate_description_hash(title: str, company: str, description: str) -> str:
        """Generate a hash for the job posting details."""
        return crud.generate_description_hash(title, company, description)
