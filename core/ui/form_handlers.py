"""Centralized form handlers for the job tracker UI."""
from typing import Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
import streamlit as st

from .forms import JobPostingForm, ApplicationForm, ApplicationStatusForm
from .base import show_validation_errors, show_operation_result
from ..services.file_service import FileService


class BaseFormHandler:
    """Base class for form submission handlers."""
    
    def __init__(self, db: Session):
        self.db = db
        self.file_service = FileService()
    
    def handle_validation_errors(self, form_class, data: Dict[str, Any]) -> bool:
        """Handle form validation and return True if there are errors (should stop processing)."""
        errors = form_class.validate(data)
        return show_validation_errors(errors)
    
    def show_result(self, result: Dict[str, Any], success_message: str) -> bool:
        """Show operation result and return success status."""
        return show_operation_result(result, success_message)


class JobPostingFormHandler(BaseFormHandler):
    """Handler for job posting form operations."""
    
    def __init__(self, db: Session, job_tracker_controller):
        super().__init__(db)
        self.job_posting_controller = job_tracker_controller
    
    def create_job_posting(self, job_posting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job posting from form data."""
        if self.handle_validation_errors(JobPostingForm, job_posting_data):
            return {"success": False, "message": "Validation errors"}
        
        return self.job_posting_controller.create_job_posting(
            db=self.db,
            title=job_posting_data["title"],
            company=job_posting_data["company"],
            description=job_posting_data["description"],
            location=job_posting_data["location"],
            source_url=job_posting_data["source_url"],
            date_posted=job_posting_data["date_posted"].isoformat() if job_posting_data["date_posted"] else None,
            type=job_posting_data["type"],
            seniority=job_posting_data["seniority"],
            tags=job_posting_data["tags"],
            skills=job_posting_data["skills"],
            industry=job_posting_data["industry"]
        )
    
    def update_job_posting(self, job_posting_id: int, job_posting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing job posting from form data."""
        if self.handle_validation_errors(JobPostingForm, job_posting_data):
            return {"success": False, "message": "Validation errors"}
        
        return self.job_posting_controller.update_job_posting(
            db=self.db,
            job_posting_id=job_posting_id,
            title=job_posting_data["title"],
            company=job_posting_data["company"],
            description=job_posting_data["description"],
            location=job_posting_data["location"],
            source_url=job_posting_data["source_url"],
            date_posted=job_posting_data["date_posted"].isoformat() if job_posting_data["date_posted"] else None,
            type=job_posting_data["type"],
            seniority=job_posting_data["seniority"],
            tags=job_posting_data["tags"],
            skills=job_posting_data["skills"],
            industry=job_posting_data["industry"]
        )


class ApplicationFormHandler(BaseFormHandler):
    """Handler for application form operations."""
    
    def __init__(self, db: Session, job_tracker_controller):
        super().__init__(db)
        self.application_controller = job_tracker_controller
    
    def create_application(self, job_posting_id: int, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new application from form data."""
        if self.handle_validation_errors(ApplicationForm, application_data):
            return {"success": False, "message": "Validation errors"}
        
        # Handle file uploads
        resume_file_path = None
        cover_letter_file_path = None
        
        if application_data.get("resume"):
            resume_file_path = self.file_service.save_uploaded_file(application_data["resume"])
        
        if application_data.get("cover_letter_file"):
            cover_letter_file_path = self.file_service.save_uploaded_file(application_data["cover_letter_file"])
        
        return self.application_controller.create_application(
            db=self.db,
            job_posting_id=job_posting_id,
            resume_file_path=resume_file_path,
            cover_letter_file_path=cover_letter_file_path,
            cover_letter_text=application_data["cover_letter_text"],
            submission_method=application_data["submission_method"],
            additional_questions=application_data["additional_questions"],
            notes=application_data["notes"],
            date_submitted=application_data["date_submitted"].isoformat()
        )
    
    def update_application(self, application_id: int, application_data: Dict[str, Any], 
                          new_resume=None, new_cover_letter=None, current_resume_path=None, 
                          current_cover_letter_path=None) -> Dict[str, Any]:
        """Update an existing application from form data."""
        if self.handle_validation_errors(ApplicationForm, application_data):
            return {"success": False, "message": "Validation errors"}
        
        # Handle file uploads
        resume_file_path = current_resume_path  # Keep existing by default
        cover_letter_file_path = current_cover_letter_path  # Keep existing by default
        
        if new_resume:
            resume_file_path = self.file_service.save_uploaded_file(new_resume)
        
        if new_cover_letter:
            cover_letter_file_path = self.file_service.save_uploaded_file(new_cover_letter)
        
        return self.application_controller.update_application(
            db=self.db,
            application_id=application_id,
            resume_file_path=resume_file_path,
            cover_letter_file_path=cover_letter_file_path,
            cover_letter_text=application_data["cover_letter_text"],
            submission_method=application_data["submission_method"],
            additional_questions=application_data["additional_questions"],
            notes=application_data["notes"]
        )


class ApplicationStatusFormHandler(BaseFormHandler):
    """Handler for application status form operations."""
    
    def __init__(self, db: Session, job_tracker_controller):
        super().__init__(db)
        self.application_controller = job_tracker_controller
    
    def update_status(self, application_id: int, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update application status from form data."""
        if self.handle_validation_errors(ApplicationStatusForm, status_data):
            return {"success": False, "message": "Validation errors"}
        
        return self.application_controller.update_application_status(
            db=self.db,
            application_id=application_id,
            status=status_data["status"],
            source_text=status_data["source_text"]
        )


class CombinedFormHandler:
    """Handler for combined job posting + application creation workflows."""
    
    def __init__(self, db: Session, job_tracker_controller):
        self.db = db
        self.job_posting_handler = JobPostingFormHandler(db, job_tracker_controller)
        self.application_handler = ApplicationFormHandler(db, job_tracker_controller)
        self.status_handler = ApplicationStatusFormHandler(db, job_tracker_controller)
    
    def create_job_posting_and_application(self, 
                                         job_posting_data: Dict[str, Any], 
                                         application_data: Dict[str, Any], 
                                         status_data: Dict[str, Any]) -> bool:
        """Handle the complete workflow: create job posting, application, and initial status."""
        
        # Create job posting
        jp_result = self.job_posting_handler.create_job_posting(job_posting_data)
        if not self.job_posting_handler.show_result(jp_result, f"Job Posting '{job_posting_data['title']}' created"):
            return False
        
        # Create application
        app_result = self.application_handler.create_application(
            jp_result["job_posting_id"], 
            application_data
        )
        if not self.application_handler.show_result(app_result, "Application created successfully"):
            return False
        
        # Log initial status
        status_result = self.status_handler.update_status(
            app_result["application_id"], 
            status_data
        )
        success = self.status_handler.show_result(status_result, "Initial status logged successfully")
        
        if success:
            # Clear analysis result after successful submission
            if "analysis_result" in st.session_state:
                del st.session_state.analysis_result
        
        return success
