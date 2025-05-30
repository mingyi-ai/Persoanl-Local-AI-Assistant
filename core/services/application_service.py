"""Service layer for application operations."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from ..database import models, schemas, crud

class ApplicationService:
    @staticmethod
    def add_application_with_details(
        db: Session,
        job_posting_id: int,
        resume_file_id: Optional[int] = None,
        cover_letter_file_id: Optional[int] = None,
        submission_method: Optional[str] = None,
        notes: Optional[str] = None,
        date_submitted: Optional[str] = None,
    ) -> Optional[models.Application]:
        """Add a new application with the given details."""
        # Create application
        application = crud.create_application(
            db,
            schemas.ApplicationCreate(
                job_posting_id=job_posting_id,
                resume_file_id=resume_file_id,
                cover_letter_file_id=cover_letter_file_id,
                submission_method=submission_method,
                notes=notes
            )
        )
        
        # Update job posting with submission date
        if application and date_submitted:
            job_posting = crud.get_job_posting(db, job_posting_id)
            if job_posting:
                job_posting.date_submitted = date_submitted
                db.commit()
                
        return application

    @staticmethod
    def get_applications_with_latest_status(db: Session) -> List[Dict[str, Any]]:
        """Get all applications with their latest status."""
        # Query applications with job postings and status history
        applications = (
            db.query(models.Application)
            .options(
                joinedload(models.Application.job_posting),
                joinedload(models.Application.status_history),
                joinedload(models.Application.resume_file),
                joinedload(models.Application.cover_letter_file)
            )
            .all()
        )

        # Format the results
        results = []
        for app in applications:
            # Get latest status
            latest_status = None
            latest_timestamp = None
            if app.status_history:
                latest_status_record = max(app.status_history, key=lambda x: x.timestamp)
                latest_status = latest_status_record.status
                latest_timestamp = latest_status_record.timestamp

            result = {
                "application_id": app.id,
                "job_title": app.job_posting.title,
                "job_company": app.job_posting.company,
                "job_location": app.job_posting.location,
                "job_date_submitted": app.job_posting.date_submitted,
                "resume_name": app.resume_file.original_name if app.resume_file else None,
                "cover_letter_name": app.cover_letter_file.original_name if app.cover_letter_file else None,
                "submission_method": app.submission_method,
                "current_status": latest_status,
                "status_timestamp": latest_timestamp
            }
            results.append(result)

        return results

    @staticmethod
    def get_full_application_details(db: Session, application_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive details for a single application."""
        application = (
            db.query(models.Application)
            .options(
                joinedload(models.Application.job_posting),
                joinedload(models.Application.resume_file),
                joinedload(models.Application.cover_letter_file),
                joinedload(models.Application.status_history),
                joinedload(models.Application.contacts),
                joinedload(models.Application.emails),
                joinedload(models.Application.tags)
            )
            .filter(models.Application.id == application_id)
            .first()
        )
        
        if not application:
            return None
            
        # Format main details
        result = {
            "application_id": application.id,
            "job_posting_id": application.job_posting_id,
            "job_title": application.job_posting.title,
            "job_company": application.job_posting.company,
            "job_location": application.job_posting.location,
            "job_description": application.job_posting.description,
            "job_source_url": application.job_posting.source_url,
            "job_date_posted": application.job_posting.date_posted,
            "job_date_submitted": application.job_posting.date_submitted,
            "job_questions_answered": application.job_posting.questions_answered,
            "resume_file_id": application.resume_file_id,
            "resume_original_name": application.resume_file.original_name if application.resume_file else None,
            "resume_stored_path": application.resume_file.stored_path if application.resume_file else None,
            "cover_letter_file_id": application.cover_letter_file_id,
            "cover_letter_original_name": application.cover_letter_file.original_name if application.cover_letter_file else None,
            "cover_letter_stored_path": application.cover_letter_file.stored_path if application.cover_letter_file else None,
            "submission_method": application.submission_method,
            "application_notes": application.notes,
        }
        
        # Add status history
        result["status_history"] = [
            {
                "timestamp": status.timestamp,
                "status": status.status,
                "source_text": status.source_text
            }
            for status in sorted(application.status_history, key=lambda x: x.timestamp)
        ]
        
        # Add contacts
        result["contacts"] = [
            {
                "name": contact.name,
                "role": contact.role,
                "email": contact.email,
                "phone": contact.phone,
                "first_reached": contact.first_reached,
                "last_contacted": contact.last_contacted
            }
            for contact in application.contacts
        ]
        
        # Add emails
        result["emails"] = [
            {
                "direction": email.direction,
                "timestamp": email.timestamp,
                "subject": email.subject,
                "body": email.body
            }
            for email in sorted(application.emails, key=lambda x: x.timestamp)
        ]
        
        # Add tags
        result["tags"] = [tag.name for tag in application.tags]
        
        # Add parsed metadata if exists
        if application.job_posting.parsed_metadata:
            result["parsed_metadata"] = {
                "tags": application.job_posting.parsed_metadata.tags,
                "tech_stacks": application.job_posting.parsed_metadata.tech_stacks,
                "seniority": application.job_posting.parsed_metadata.seniority,
                "industry": application.job_posting.parsed_metadata.industry
            }
        
        return result

    @staticmethod
    def log_application_status(
        db: Session,
        application_id: int,
        status: str,
        source_text: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> Optional[models.ApplicationStatusHistory]:
        """Log a new status for an application."""
        if not timestamp:
            timestamp = datetime.now().isoformat()
            
        return crud.create_status_history(
            db,
            schemas.StatusHistoryCreate(
                application_id=application_id,
                status=status,
                timestamp=timestamp,
                source_text=source_text
            )
        )

    @staticmethod
    def get_files_by_type(db: Session, file_type: str) -> List[Dict[str, Any]]:
        """Get all files of a specific type."""
        files = (
            db.query(models.File)
            .filter(models.File.file_type == file_type)
            .all()
        )
        return [{"id": f.id, "original_name": f.original_name} for f in files]
