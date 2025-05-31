"""Controller layer for job posting operations."""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ..services.job_posting_service import JobPostingService
from ..database import models

class JobPostingController:
    def __init__(self):
        self.service = JobPostingService()

    def create_job_posting(
        self,
        db: Session,
        title: str,
        company: str, 
        description: str,
        location: Optional[str] = None,
        type: Optional[str] = None,
        seniority: Optional[str] = None,
        source_url: Optional[str] = None,
        date_posted: Optional[str] = None,
        tags: Optional[str] = None,
        skills: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new job posting and return a formatted response."""
        job_posting = self.service.add_job_posting_with_details(
            db=db,
            title=title,
            company=company,
            description=description,
            location=location,
            job_type=type,
            seniority=seniority,
            source_url=source_url,
            date_posted=date_posted,
            tags=tags,
            skills=skills,
            industry=industry
        )

        if not job_posting:
            return {"success": False, "message": "Failed to create job posting"}

        return {
            "success": True,
            "job_posting_id": job_posting.id,
            "message": "Job posting created successfully"
        }

    def get_job_posting(self, db: Session, job_posting_id: int) -> Dict[str, Any]:
        """Get a job posting by ID."""
        job_posting = self.service.get_job_posting_by_id(db, job_posting_id)
        
        if not job_posting:
            return {
                "success": False,
                "message": f"Job posting with ID {job_posting_id} not found"
            }

        return {
            "success": True,
            "job_posting": {
                "id": job_posting.id,
                "title": job_posting.title,
                "company": job_posting.company,
                "location": job_posting.location,
                "type": job_posting.type,
                "seniority": job_posting.seniority,
                "description": job_posting.description,
                "source_url": job_posting.source_url,
                "date_posted": job_posting.date_posted,
                "tags": job_posting.tags,
                "skills": job_posting.skills,
                "industry": job_posting.industry,
                "created_at": job_posting.created_at,
                "updated_at": job_posting.updated_at
            }
        }

    def search_job_postings(
        self, 
        db: Session, 
        search_term: str = "", 
        company: str = "", 
        skip: int = 0, 
        limit: int = 100
    ) -> Dict[str, Any]:
        """Search job postings."""
        job_postings = self.service.search_job_postings(db, search_term, company, skip, limit)
        
        return {
            "success": True,
            "job_postings": [
                {
                    "id": jp.id,
                    "title": jp.title,
                    "company": jp.company,
                    "location": jp.location,
                    "type": jp.type,
                    "seniority": jp.seniority,
                    "date_posted": jp.date_posted,
                    "created_at": jp.created_at
                }
                for jp in job_postings
            ]
        }
    
    def update_job_posting(
        self,
        db: Session,
        job_posting_id: int,
        title: str,
        company: str, 
        description: str,
        location: Optional[str] = None,
        type: Optional[str] = None,
        seniority: Optional[str] = None,
        source_url: Optional[str] = None,
        date_posted: Optional[str] = None,
        tags: Optional[str] = None,
        skills: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a job posting and return a formatted response."""
        job_posting = self.service.update_job_posting_with_details(
            db=db,
            job_posting_id=job_posting_id,
            title=title,
            company=company,
            description=description,
            location=location,
            job_type=type,
            seniority=seniority,
            source_url=source_url,
            date_posted=date_posted,
            tags=tags,
            skills=skills,
            industry=industry
        )

        if not job_posting:
            return {"success": False, "message": "Failed to update job posting or job posting not found"}

        return {
            "success": True,
            "job_posting_id": job_posting.id,
            "message": "Job posting updated successfully"
        }
