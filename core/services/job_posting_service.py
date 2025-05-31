"""Service layer for job posting operations."""
from typing import Optional, Dict, Any, List
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
        job_type: Optional[str] = None,
        seniority: Optional[str] = None,
        source_url: Optional[str] = None,
        date_posted: Optional[str] = None,
        tags: Optional[str] = None,
        skills: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> Optional[models.JobPosting]:
        """Add a new job posting with the given details."""
        job_posting = crud.create_job_posting(
            db,
            schemas.JobPostingCreate(
                title=title,
                company=company,
                description=description,
                location=location,
                type=job_type,
                seniority=seniority,
                source_url=source_url,
                date_posted=date_posted,
                tags=tags,
                skills=skills,
                industry=industry
            )
        )
        return job_posting

    @staticmethod
    def get_job_posting_by_id(db: Session, job_posting_id: int) -> Optional[models.JobPosting]:
        """Get a job posting by its ID."""
        return crud.get_job_posting(db, job_posting_id)

    @staticmethod
    def search_job_postings(
        db: Session, 
        search_term: str = "", 
        company: str = "", 
        skip: int = 0, 
        limit: int = 100
    ) -> List[models.JobPosting]:
        """Search job postings by various criteria."""
        return crud.search_job_postings(db, search_term, company, skip, limit)

    @staticmethod
    def get_all_job_postings(db: Session, skip: int = 0, limit: int = 100) -> List[models.JobPosting]:
        """Get all job postings with pagination."""
        return crud.get_job_postings(db, skip, limit)
    
    @staticmethod
    def update_job_posting_with_details(
        db: Session,
        job_posting_id: int,
        title: str,
        company: str, 
        description: str,
        location: Optional[str] = None,
        job_type: Optional[str] = None,
        seniority: Optional[str] = None,
        source_url: Optional[str] = None,
        date_posted: Optional[str] = None,
        tags: Optional[str] = None,
        skills: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> Optional[models.JobPosting]:
        """Update a job posting with the given details."""
        job_posting = crud.update_job_posting(
            db,
            job_posting_id,
            schemas.JobPostingCreate(
                title=title,
                company=company,
                description=description,
                location=location,
                type=job_type,
                seniority=seniority,
                source_url=source_url,
                date_posted=date_posted,
                tags=tags,
                skills=skills,
                industry=industry
            )
        )
        return job_posting
