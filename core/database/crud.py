"""Basic CRUD operations for the job tracker database."""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import hashlib
import logging
from typing import Optional, List, Dict, Any
from . import models, schemas

logger = logging.getLogger(__name__)

def init_db(db: Session) -> None:
    """Initialize the database by creating all tables and any initial data."""
    from .base import Base, engine
    Base.metadata.create_all(bind=engine)
    
    # You can add any initial data here if needed
    # For example, creating default tags, etc.

def generate_description_hash(title: str, company: str, description: str) -> str:
    """Generates a SHA256 hash for core job posting details."""
    hasher = hashlib.sha256()
    hasher.update(title.lower().encode('utf-8'))
    hasher.update(company.lower().encode('utf-8'))
    hasher.update(description.lower().encode('utf-8'))
    return hasher.hexdigest()

# File operations
def get_file_by_hash(db: Session, sha256_hash: str) -> Optional[models.File]:
    """Get a file by its SHA256 hash."""
    return db.query(models.File).filter(models.File.sha256 == sha256_hash).first()

def create_file(db: Session, file: schemas.FileCreate) -> models.File:
    """Create a new file record or return existing one if hash matches."""
    existing_file = get_file_by_hash(db, file.sha256)
    if existing_file:
        return existing_file
    
    db_file = models.File(**file.dict())
    try:
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        return db_file
    except IntegrityError:
        db.rollback()
        return db.query(models.File).filter(models.File.stored_path == file.stored_path).first()

# Job posting operations
def get_job_posting(db: Session, job_posting_id: int) -> Optional[models.JobPosting]:
    """Get a job posting by its ID."""
    return db.query(models.JobPosting).filter(models.JobPosting.id == job_posting_id).first()

def get_job_posting_by_hash(db: Session, desc_hash: str) -> Optional[models.JobPosting]:
    """Get a job posting by its description hash."""
    return db.query(models.JobPosting).filter(models.JobPosting.description_hash == desc_hash).first()

def create_job_posting(db: Session, job_posting: schemas.JobPostingCreate) -> models.JobPosting:
    """Create a new job posting or return existing one if hash matches."""
    logger.debug(f"CRUD: Creating job posting - Title: {job_posting.title}, Company: {job_posting.company}")
    
    desc_hash = generate_description_hash(
        job_posting.title,
        job_posting.company,
        job_posting.description or ""
    )
    
    existing = get_job_posting_by_hash(db, desc_hash)
    if existing:
        logger.debug(f"CRUD: Found existing job posting with hash: {desc_hash}")
        return existing
    
    try:
        db_job_posting = models.JobPosting(**job_posting.dict(), description_hash=desc_hash)
        db.add(db_job_posting)
        db.commit()
        db.refresh(db_job_posting)
        logger.debug(f"CRUD: Successfully created job posting with ID: {db_job_posting.id}")
        return db_job_posting
    except Exception as e:
        logger.error(f"CRUD: Error creating job posting: {e}")
        db.rollback()
        raise

# Application operations
def create_application(db: Session, application: schemas.ApplicationCreate) -> models.Application:
    """Create a new application."""
    db_application = models.Application(**application.dict())
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application

def get_application(db: Session, application_id: int) -> Optional[models.Application]:
    """Get an application by its ID."""
    return db.query(models.Application).filter(models.Application.id == application_id).first()

# Status history operations
def create_status_history(db: Session, status: schemas.StatusHistoryCreate) -> models.ApplicationStatusHistory:
    """Create a new status history record."""
    db_status = models.ApplicationStatusHistory(**status.dict())
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

def get_application_status_history(db: Session, application_id: int) -> List[models.ApplicationStatusHistory]:
    """Get the status history for an application."""
    return db.query(models.ApplicationStatusHistory)\
             .filter(models.ApplicationStatusHistory.application_id == application_id)\
             .order_by(models.ApplicationStatusHistory.timestamp)\
             .all()

# Contact operations
def create_contact(db: Session, contact: schemas.ContactCreate) -> models.Contact:
    """Create a new contact record."""
    db_contact = models.Contact(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def get_contact(db: Session, contact_id: int) -> Optional[models.Contact]:
    """Get a contact by its ID."""
    return db.query(models.Contact).filter(models.Contact.id == contact_id).first()

def get_application_contacts(db: Session, application_id: int) -> List[models.Contact]:
    """Get all contacts for an application."""
    return db.query(models.Contact)\
             .filter(models.Contact.application_id == application_id)\
             .all()

# Email operations
def create_email(db: Session, email: schemas.EmailCreate) -> models.Email:
    """Create a new email record."""
    db_email = models.Email(**email.dict())
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return db_email

def get_email(db: Session, email_id: int) -> Optional[models.Email]:
    """Get an email by its ID."""
    return db.query(models.Email).filter(models.Email.id == email_id).first()

def get_application_emails(db: Session, application_id: int) -> List[models.Email]:
    """Get all emails for an application."""
    return db.query(models.Email)\
             .filter(models.Email.application_id == application_id)\
             .order_by(models.Email.timestamp)\
             .all()

# ParsedMetadata operations
def create_parsed_metadata(db: Session, metadata: schemas.ParsedMetadataCreate) -> models.ParsedMetadata:
    """Create new parsed metadata for a job posting."""
    db_metadata = models.ParsedMetadata(**metadata.dict())
    db.add(db_metadata)
    db.commit()
    db.refresh(db_metadata)
    return db_metadata

def update_or_create_parsed_metadata(
    db: Session, 
    job_posting_id: int,
    parsed_metadata: Dict[str, Any]
) -> Optional[models.ParsedMetadata]:
    """Update existing or create new parsed metadata for a job posting."""
    logger.debug(f"CRUD: Adding/updating parsed metadata for job posting ID: {job_posting_id}")
    logger.debug(f"CRUD: Raw metadata: {parsed_metadata}")
    
    # Try to find existing metadata
    existing = db.query(models.ParsedMetadata).filter(
        models.ParsedMetadata.job_posting_id == job_posting_id
    ).first()
    
    import json
    # Convert lists to JSON strings
    tags = parsed_metadata.get("required_skills", []) + parsed_metadata.get("preferred_skills", [])
    tech_stacks = parsed_metadata.get("tech_stacks", [])
    
    metadata_dict = {
        "job_posting_id": job_posting_id,
        "tags": json.dumps(tags) if tags else None,
        "tech_stacks": json.dumps(tech_stacks) if tech_stacks else None,
        "seniority": parsed_metadata.get("experience_level"),
        "industry": parsed_metadata.get("industry", "Not specified")
    }
    
    logger.debug(f"CRUD: Processed metadata dict: {metadata_dict}")
    
    try:
        if existing:
            logger.debug("CRUD: Updating existing metadata")
            for key, value in metadata_dict.items():
                setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing
        
        logger.debug("CRUD: Creating new metadata")
        return create_parsed_metadata(db, schemas.ParsedMetadataCreate(**metadata_dict))
    except Exception as e:
        logger.error(f"CRUD: Error updating/creating metadata: {e}")
        db.rollback()
        raise

# Tag operations
def create_tag(db: Session, tag: schemas.TagCreate) -> models.Tag:
    """Create a new tag or return existing one if name matches."""
    db_tag = models.Tag(**tag.dict())
    try:
        db.add(db_tag)
        db.commit()
        db.refresh(db_tag)
        return db_tag
    except IntegrityError:
        db.rollback()
        return db.query(models.Tag).filter(models.Tag.name == tag.name).first()

def get_tag(db: Session, tag_id: int) -> Optional[models.Tag]:
    """Get a tag by its ID."""
    return db.query(models.Tag).filter(models.Tag.id == tag_id).first()

def get_tag_by_name(db: Session, name: str) -> Optional[models.Tag]:
    """Get a tag by its name."""
    return db.query(models.Tag).filter(models.Tag.name == name).first()

def add_tag_to_application(db: Session, application_id: int, tag_name: str) -> models.Tag:
    """Add a tag to an application."""
    tag = get_tag_by_name(db, tag_name)
    if not tag:
        tag = create_tag(db, schemas.TagCreate(name=tag_name))
    
    application = get_application(db, application_id)
    if application and tag not in application.tags:
        application.tags.append(tag)
        db.commit()
    return tag
