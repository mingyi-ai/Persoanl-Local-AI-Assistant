"""Controller layer for application operations."""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ..services.application_service import ApplicationService
from ..database import models

class ApplicationController:
    def __init__(self):
        self.service = ApplicationService()

    def create_application(
        self,
        db: Session,
        job_posting_id: int,
        resume_file_id: Optional[int] = None,
        cover_letter_file_id: Optional[int] = None,
        submission_method: Optional[str] = None,
        notes: Optional[str] = None,
        date_submitted: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new application and return a formatted response."""
        application = self.service.add_application_with_details(
            db=db,
            job_posting_id=job_posting_id,
            resume_file_id=resume_file_id,
            cover_letter_file_id=cover_letter_file_id,
            submission_method=submission_method,
            notes=notes,
            date_submitted=date_submitted
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
        applications = self.service.get_applications_with_latest_status(db)
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
        status_history = self.service.log_application_status(
            db=db,
            application_id=application_id,
            status=status,
            source_text=source_text
        )

        if not status_history:
            return {
                "success": False,
                "message": "Failed to update application status"
            }

        return {
            "success": True,
            "message": f"Application status updated to {status}"
        }

    def list_files_by_type(self, db: Session, file_type: str) -> Dict[str, Any]:
        """Get a list of files of a specific type."""
        files = self.service.get_files_by_type(db, file_type)
        return {
            "success": True,
            "files": files
        }
