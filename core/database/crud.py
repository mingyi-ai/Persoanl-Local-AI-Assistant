"""Basic CRUD operations for the job tracker database."""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Any
from . import models, schemas

def init_db(db: Session) -> None:
    """Initialize the database by creating all tables and any initial data."""
    from .base import Base, engine
    Base.metadata.create_all(bind=engine)
    
    # You can add any initial data here if needed
    # For example, creating default statuses, etc.

# Job posting operations
def get_job_posting(db: Session, job_posting_id: int) -> Optional[models.JobPosting]:
    """Get a job posting by its ID."""
    return db.query(models.JobPosting).filter(models.JobPosting.id == job_posting_id).first()

def get_job_postings(db: Session, skip: int = 0, limit: int = 100) -> List[models.JobPosting]:
    """Get all job postings with pagination."""
    return db.query(models.JobPosting).offset(skip).limit(limit).all()

def create_job_posting(db: Session, job_posting: schemas.JobPostingCreate) -> models.JobPosting:
    """Create a new job posting."""
    db_job_posting = models.JobPosting(**job_posting.model_dump())
    db.add(db_job_posting)
    db.commit()
    db.refresh(db_job_posting)
    return db_job_posting

def update_job_posting(db: Session, job_posting_id: int, job_posting: schemas.JobPostingUpdate) -> Optional[models.JobPosting]:
    """Update a job posting."""
    db_job_posting = get_job_posting(db, job_posting_id)
    if db_job_posting:
        update_data = job_posting.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_job_posting, field, value)
        db.commit()
        db.refresh(db_job_posting)
    return db_job_posting

def delete_job_posting(db: Session, job_posting_id: int) -> bool:
    """Delete a job posting."""
    db_job_posting = get_job_posting(db, job_posting_id)
    if db_job_posting:
        db.delete(db_job_posting)
        db.commit()
        return True
    return False

# Application operations
def create_application(db: Session, application: schemas.ApplicationCreate) -> models.Application:
    """Create a new application."""
    db_application = models.Application(**application.model_dump())
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application

def get_application(db: Session, application_id: int) -> Optional[models.Application]:
    """Get an application by its ID."""
    return db.query(models.Application).filter(models.Application.id == application_id).first()

def get_applications(db: Session, skip: int = 0, limit: int = 100) -> List[models.Application]:
    """Get all applications with pagination."""
    return db.query(models.Application).offset(skip).limit(limit).all()

def get_applications_by_job_posting(db: Session, job_posting_id: int) -> List[models.Application]:
    """Get all applications for a specific job posting."""
    return db.query(models.Application).filter(models.Application.job_posting_id == job_posting_id).all()

def update_application(db: Session, application_id: int, application: schemas.ApplicationUpdate) -> Optional[models.Application]:
    """Update an application."""
    db_application = get_application(db, application_id)
    if db_application:
        update_data = application.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_application, field, value)
        db.commit()
        db.refresh(db_application)
    return db_application

def delete_application(db: Session, application_id: int) -> bool:
    """Delete an application."""
    db_application = get_application(db, application_id)
    if db_application:
        db.delete(db_application)
        db.commit()
        return True
    return False

# Status history operations
def create_application_status(db: Session, status: schemas.ApplicationStatusCreate) -> models.ApplicationStatus:
    """Create a new status history record."""
    db_status = models.ApplicationStatus(**status.model_dump())
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

def get_application_status_history(db: Session, application_id: int) -> List[models.ApplicationStatus]:
    """Get the status history for an application."""
    return db.query(models.ApplicationStatus)\
             .filter(models.ApplicationStatus.application_id == application_id)\
             .order_by(models.ApplicationStatus.created_at)\
             .all()

def get_latest_application_status(db: Session, application_id: int) -> Optional[models.ApplicationStatus]:
    """Get the latest status for an application."""
    return db.query(models.ApplicationStatus)\
             .filter(models.ApplicationStatus.application_id == application_id)\
             .order_by(models.ApplicationStatus.created_at.desc())\
             .first()

# Utility functions for search and filtering
def search_job_postings(db: Session, search_term: str = "", company: str = "", skip: int = 0, limit: int = 100) -> List[models.JobPosting]:
    """Search job postings by title, company, or description."""
    query = db.query(models.JobPosting)
    
    if search_term:
        search_filter = f"%{search_term}%"
        query = query.filter(
            models.JobPosting.title.ilike(search_filter) |
            models.JobPosting.description.ilike(search_filter)
        )
    
    if company:
        company_filter = f"%{company}%"
        query = query.filter(models.JobPosting.company.ilike(company_filter))
    
    return query.offset(skip).limit(limit).all()

def get_applications_with_status(db: Session, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[models.Application]:
    """Get applications filtered by their latest status."""
    if status:
        # Get applications with latest status matching the filter
        subquery = db.query(
            models.ApplicationStatus.application_id,
            models.ApplicationStatus.status,
            models.ApplicationStatus.created_at.label('latest_date')
        ).order_by(
            models.ApplicationStatus.application_id,
            models.ApplicationStatus.created_at.desc()
        ).distinct(models.ApplicationStatus.application_id).subquery()
        
        return db.query(models.Application)\
                 .join(subquery, models.Application.id == subquery.c.application_id)\
                 .filter(subquery.c.status == status)\
                 .offset(skip).limit(limit).all()
    else:
        return get_applications(db, skip, limit)
