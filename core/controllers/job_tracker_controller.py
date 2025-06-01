"""Unified controller layer for job posting and application operations."""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ..services.job_tracker_service import JobTrackerService
from ..database import models

class JobTrackerController:
    def __init__(self):
        self.service = JobTrackerService()

    # Job Posting Methods
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

    # Application Methods
    def create_application(
        self,
        db: Session,
        job_posting_id: int,
        submission_method: Optional[str] = None,
        date_submitted: Optional[str] = None,
        resume_file_path: Optional[str] = None,
        cover_letter_file_path: Optional[str] = None,
        cover_letter_text: Optional[str] = None,
        additional_questions: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new application and return a formatted response."""
        application = self.service.add_application_with_details(
            db=db,
            job_posting_id=job_posting_id,
            submission_method=submission_method,
            date_submitted=date_submitted,
            resume_file_path=resume_file_path,
            cover_letter_file_path=cover_letter_file_path,
            cover_letter_text=cover_letter_text,
            additional_questions=additional_questions,
            notes=notes
        )

        if not application:
            return {"success": False, "message": "Failed to create application"}

        return {
            "success": True,
            "application_id": application.id,
            "message": "Application created successfully"
        }

    def get_application_list(self, db: Session) -> Dict[str, Any]:
        """Get a list of all applications with their latest status."""
        applications = self.service.get_all_applications_with_details(db)
        return {
            "success": True,
            "applications": applications
        }

    def get_application_details(self, db: Session, application_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific application."""
        details = self.service.get_full_application_details(db, application_id)
        if not details:
            return {
                "success": False,
                "message": f"Application with ID {application_id} not found"
            }

        return {
            "success": True,
            "details": details
        }

    def update_application_status(
        self,
        db: Session,
        application_id: int,
        status: str,
        source_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update the status of an application."""
        status_record = self.service.add_status_update(
            db=db,
            application_id=application_id,
            status=status,
            source_text=source_text
        )

        if not status_record:
            return {
                "success": False,
                "message": "Failed to update application status"
            }

        return {
            "success": True,
            "message": f"Application status updated to {status}"
        }

    def update_application(
        self,
        db: Session,
        application_id: int,
        **updates
    ) -> Dict[str, Any]:
        """Update an application with new details."""
        application = self.service.update_application(db, application_id, **updates)
        
        if not application:
            return {
                "success": False,
                "message": f"Failed to update application with ID {application_id}"
            }

        return {
            "success": True,
            "message": "Application updated successfully"
        }

    def delete_application(self, db: Session, application_id: int) -> Dict[str, Any]:
        """Delete an application."""
        success = self.service.delete_application(db, application_id)
        
        if not success:
            return {
                "success": False,
                "message": f"Failed to delete application with ID {application_id}"
            }

        return {
            "success": True,
            "message": "Application deleted successfully"
        }

    def get_applications_summary(self, db: Session) -> Dict[str, Any]:
        """Get summary statistics for applications."""
        summary = self.service.get_applications_summary(db)
        return {
            "success": True,
            "summary": summary
        }
