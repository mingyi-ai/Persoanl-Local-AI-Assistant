"""Controller layer for job posting operations."""
from typing import Optional, Dict, Any
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
        source_url: Optional[str] = None,
        date_posted: Optional[str] = None,
        questions_answered: Optional[str] = None,
        parsed_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new job posting and return a formatted response."""
        job_posting = self.service.add_job_posting_with_details(
            db=db,
            title=title,
            company=company,
            description=description,
            location=location,
            source_url=source_url,
            date_posted=date_posted,
            questions_answered=questions_answered,
            parsed_metadata=parsed_metadata
        )

        if not job_posting:
            return {"success": False, "message": "Failed to create job posting"}

        return {
            "success": True,
            "job_posting_id": job_posting.id,
            "message": "Job posting created successfully"
        }
