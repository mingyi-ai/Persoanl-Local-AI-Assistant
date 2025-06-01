"""Unified service layer for job posting and application operations."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from ..database import models, schemas, crud

class JobTrackerService:
    # Job Posting Methods
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

    # Application Methods
    @staticmethod
    def add_application_with_details(
        db: Session,
        job_posting_id: int,
        submission_method: Optional[str] = None,
        date_submitted: Optional[str] = None,
        resume_file_path: Optional[str] = None,
        cover_letter_file_path: Optional[str] = None,
        cover_letter_text: Optional[str] = None,
        additional_questions: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[models.Application]:
        """Add a new application with the given details."""
        # Create application
        application = crud.create_application(
            db,
            schemas.ApplicationCreate(
                job_posting_id=job_posting_id,
                submission_method=submission_method,
                date_submitted=date_submitted,
                resume_file_path=resume_file_path,
                cover_letter_file_path=cover_letter_file_path,
                cover_letter_text=cover_letter_text,
                additional_questions=additional_questions,
                notes=notes
            )
        )
        
        return application

    @staticmethod
    def get_applications_with_latest_status(db: Session) -> List[Dict[str, Any]]:
        """Get all applications with their latest status."""
        # Query applications with job postings and status history
        applications = (
            db.query(models.Application)
            .options(
                joinedload(models.Application.job_posting),
                joinedload(models.Application.status_history)
            )
            .all()
        )
        
        result = []
        for app in applications:
            # Get latest status
            latest_status = None
            if app.status_history:
                latest_status = max(app.status_history, key=lambda s: s.created_at)
            
            result.append({
                'application': app,
                'job_posting': app.job_posting,
                'latest_status': latest_status.status if latest_status else 'unknown',
                'status_date': latest_status.created_at if latest_status else app.created_at
            })
        
        return result

    @staticmethod
    def add_status_update(
        db: Session,
        application_id: int,
        status: str,
        source_text: Optional[str] = None
    ) -> Optional[models.ApplicationStatus]:
        """Add a status update to an application."""
        return crud.create_application_status(
            db,
            schemas.ApplicationStatusCreate(
                application_id=application_id,
                status=status,
                source_text=source_text
            )
        )

    @staticmethod
    def get_application_by_id(db: Session, application_id: int) -> Optional[models.Application]:
        """Get an application by its ID."""
        return crud.get_application(db, application_id)

    @staticmethod
    def get_applications_by_status(
        db: Session, 
        status: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[models.Application]:
        """Get applications filtered by their latest status."""
        return crud.get_applications_with_status(db, status, skip, limit)

    @staticmethod
    def get_all_applications_with_details(db: Session) -> List[Dict[str, Any]]:
        """Get all applications with job posting details and latest status."""
        applications = (
            db.query(models.Application)
            .options(
                joinedload(models.Application.job_posting),
                joinedload(models.Application.status_history)
            )
            .all()
        )

        results = []
        for app in applications:
            # Get latest status
            latest_status = None
            latest_timestamp = None
            if app.status_history:
                latest_status_record = max(app.status_history, key=lambda x: x.created_at)
                latest_status = latest_status_record.status
                latest_timestamp = latest_status_record.created_at

            result = {
                "application_id": app.id,
                "job_title": app.job_posting.title,
                "job_company": app.job_posting.company,
                "job_location": app.job_posting.location,
                "date_submitted": app.date_submitted,
                "resume_file_path": app.resume_file_path,
                "cover_letter_file_path": app.cover_letter_file_path,
                "submission_method": app.submission_method,
                "current_status": latest_status,
                "status_timestamp": latest_timestamp,
                "notes": app.notes
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
                joinedload(models.Application.status_history)
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
            "job_type": application.job_posting.type,
            "job_seniority": application.job_posting.seniority,
            "job_tags": application.job_posting.tags,
            "job_skills": application.job_posting.skills,
            "job_industry": application.job_posting.industry,
            "date_submitted": application.date_submitted,
            "resume_file_path": application.resume_file_path,
            "cover_letter_file_path": application.cover_letter_file_path,
            "cover_letter_text": application.cover_letter_text,
            "submission_method": application.submission_method,
            "additional_questions": application.additional_questions,
            "notes": application.notes,
            "created_at": application.created_at,
            "updated_at": application.updated_at
        }
        
        # Add status history
        result["status_history"] = [
            {
                "created_at": status.created_at,
                "status": status.status,
                "source_text": status.source_text
            }
            for status in sorted(application.status_history, key=lambda x: x.created_at)
        ]
        
        return result

    @staticmethod
    def update_application(
        db: Session,
        application_id: int,
        **updates
    ) -> Optional[models.Application]:
        """Update an application with new details."""
        return crud.update_application(db, application_id, updates)

    @staticmethod
    def delete_application(db: Session, application_id: int) -> bool:
        """Delete an application and its associated data."""
        return crud.delete_application(db, application_id)

    @staticmethod
    def get_applications_summary(db: Session) -> Dict[str, Any]:
        """Get summary statistics for applications."""
        total_applications = db.query(models.Application).count()
        
        # Get status counts
        status_counts = {}
        applications = db.query(models.Application).options(
            joinedload(models.Application.status_history)
        ).all()
        
        for app in applications:
            if app.status_history:
                latest_status = max(app.status_history, key=lambda x: x.created_at)
                status = latest_status.status
            else:
                status = 'unknown'
            
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_applications": total_applications,
            "status_counts": status_counts
        }
