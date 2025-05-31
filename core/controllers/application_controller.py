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
