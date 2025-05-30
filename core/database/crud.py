from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import hashlib
from typing import Optional, List
from . import models, schemas

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
    return db.query(models.File).filter(models.File.sha256 == sha256_hash).first()

def create_file(db: Session, file: schemas.FileCreate) -> models.File:
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
    return db.query(models.JobPosting).filter(models.JobPosting.id == job_posting_id).first()

def get_job_posting_by_hash(db: Session, desc_hash: str) -> Optional[models.JobPosting]:
    return db.query(models.JobPosting).filter(models.JobPosting.description_hash == desc_hash).first()

def create_job_posting(db: Session, job_posting: schemas.JobPostingCreate) -> models.JobPosting:
    desc_hash = generate_description_hash(
        job_posting.title,
        job_posting.company,
        job_posting.description or ""
    )
    
    existing = get_job_posting_by_hash(db, desc_hash)
    if existing:
        return existing
    
    db_job_posting = models.JobPosting(**job_posting.dict(), description_hash=desc_hash)
    db.add(db_job_posting)
    db.commit()
    db.refresh(db_job_posting)
    return db_job_posting

# Application operations
def create_application(db: Session, application: schemas.ApplicationCreate) -> models.Application:
    db_application = models.Application(**application.dict())
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application

def get_application(db: Session, application_id: int) -> Optional[models.Application]:
    return db.query(models.Application).filter(models.Application.id == application_id).first()

# Status history operations
def create_status_history(db: Session, status: schemas.StatusHistoryCreate) -> models.ApplicationStatusHistory:
    db_status = models.ApplicationStatusHistory(**status.dict())
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

def get_application_status_history(db: Session, application_id: int) -> List[models.ApplicationStatusHistory]:
    return db.query(models.ApplicationStatusHistory)\
             .filter(models.ApplicationStatusHistory.application_id == application_id)\
             .order_by(models.ApplicationStatusHistory.timestamp)\
             .all()

# Contact operations
def create_contact(db: Session, contact: schemas.ContactCreate) -> models.Contact:
    db_contact = models.Contact(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def get_application_contacts(db: Session, application_id: int) -> List[models.Contact]:
    return db.query(models.Contact)\
             .filter(models.Contact.application_id == application_id)\
             .all()

# Email operations
def create_email(db: Session, email: schemas.EmailCreate) -> models.Email:
    db_email = models.Email(**email.dict())
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return db_email

def get_application_emails(db: Session, application_id: int) -> List[models.Email]:
    return db.query(models.Email)\
             .filter(models.Email.application_id == application_id)\
             .order_by(models.Email.timestamp)\
             .all()

# ParsedMetadata operations
def create_parsed_metadata(db: Session, metadata: schemas.ParsedMetadataCreate) -> models.ParsedMetadata:
    db_metadata = models.ParsedMetadata(**metadata.dict())
    db.add(db_metadata)
    db.commit()
    db.refresh(db_metadata)
    return db_metadata

def get_job_posting_metadata(db: Session, job_posting_id: int) -> Optional[models.ParsedMetadata]:
    return db.query(models.ParsedMetadata)\
             .filter(models.ParsedMetadata.job_posting_id == job_posting_id)\
             .first()

# Tag operations
def create_tag(db: Session, tag: schemas.TagCreate) -> models.Tag:
    db_tag = models.Tag(**tag.dict())
    try:
        db.add(db_tag)
        db.commit()
        db.refresh(db_tag)
        return db_tag
    except IntegrityError:
        db.rollback()
        return db.query(models.Tag).filter(models.Tag.name == tag.name).first()

def get_tag_by_name(db: Session, name: str) -> Optional[models.Tag]:
    return db.query(models.Tag).filter(models.Tag.name == name).first()

def add_tag_to_application(db: Session, application_id: int, tag_name: str) -> models.Tag:
    tag = get_tag_by_name(db, tag_name)
    if not tag:
        tag = create_tag(db, schemas.TagCreate(name=tag_name))
    
    application = get_application(db, application_id)
    if application and tag not in application.tags:
        application.tags.append(tag)
        db.commit()
    return tag
