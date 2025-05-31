from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class JobPosting(Base):
    """Simplified job posting table with all form fields."""
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Core job posting fields from JobPostingForm
    title = Column(String, nullable=False)
    company = Column(String, nullable=False) 
    location = Column(String)
    type = Column(String)  # Full-time, Part-time, Contract, etc.
    seniority = Column(String)  # Entry, Mid-Senior, Director, etc.
    description = Column(Text, nullable=False)
    source_url = Column(String)
    date_posted = Column(String)  # ISO date string
    
    # Optional fields for future expansion
    tags = Column(String)  # Comma-separated string, can be normalized later
    skills = Column(String)  # Comma-separated string, can be normalized later  
    industry = Column(String)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    applications = relationship("Application", back_populates="job_posting", cascade="all, delete")

class Application(Base):
    """Simplified application table with all form fields."""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_posting_id = Column(Integer, ForeignKey('job_postings.id', ondelete='CASCADE'), nullable=False)
    
    # Application fields from ApplicationForm
    submission_method = Column(String)  # web, email, referral, other
    date_submitted = Column(String)  # ISO date string
    
    # File handling - simplified to store file paths directly for now
    resume_file_path = Column(String)  # Path to uploaded resume file
    cover_letter_file_path = Column(String)  # Path to uploaded cover letter file
    cover_letter_text = Column(Text)  # Text content of cover letter
    
    # Additional fields
    additional_questions = Column(Text)  # JSON string for Q&A data
    notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    job_posting = relationship("JobPosting", back_populates="applications")
    status_history = relationship("ApplicationStatus", back_populates="application", cascade="all, delete")

class ApplicationStatus(Base):
    """Simplified application status tracking."""
    __tablename__ = "application_status"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    
    # Status fields from ApplicationStatusForm
    status = Column(String, nullable=False)  # submitted, viewed, screening, interview, etc.
    source_text = Column(Text)  # Source/notes about the status update
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    application = relationship("Application", back_populates="status_history")
