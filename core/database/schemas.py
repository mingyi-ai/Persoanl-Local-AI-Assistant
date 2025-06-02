# filepath: /Users/mingyihou/Desktop/JobAssistant/core/database/schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums for validation - simplified
class SubmissionMethod(str, Enum):
    WEB = "web"
    EMAIL = "email"
    REFERRAL = "referral"
    OTHER = "other"

class JobType(str, Enum):
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    TEMPORARY = "Temporary"
    INTERNSHIP = "Internship"
    FREELANCE = "Freelance"
    OTHER = "Other"

class SeniorityLevel(str, Enum):
    ENTRY = "Entry"
    MID_SENIOR = "Mid-Senior"
    DIRECTOR = "Director"
    EXECUTIVE = "Executive"
    INTERN = "Intern"
    OTHER = "Other"

class ApplicationStatus(str, Enum):
    SUBMITTED = "submitted"
    VIEWED = "viewed"
    SCREENING = "screening"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    OTHER = "other"

# Base schemas for job posting
class JobPostingBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    type: Optional[str] = None
    seniority: Optional[str] = None
    description: str
    source_url: Optional[str] = None
    date_posted: Optional[str] = None
    tags: Optional[str] = None
    skills: Optional[str] = None
    industry: Optional[str] = None

class JobPostingCreate(JobPostingBase):
    pass

class JobPostingUpdate(BaseModel):
    """Schema for updating job postings - all fields optional"""
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    seniority: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    date_posted: Optional[str] = None
    tags: Optional[str] = None
    skills: Optional[str] = None
    industry: Optional[str] = None

class JobPosting(JobPostingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    applications: List['Application'] = []

    class Config:
        from_attributes = True

# Base schemas for application
class ApplicationBase(BaseModel):
    job_posting_id: int
    submission_method: Optional[str] = None
    date_submitted: Optional[str] = None
    resume_file_path: Optional[str] = None
    cover_letter_file_path: Optional[str] = None
    cover_letter_text: Optional[str] = None
    additional_questions: Optional[str] = None
    notes: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationUpdate(BaseModel):
    """Schema for updating applications - all fields optional"""
    job_posting_id: Optional[int] = None
    submission_method: Optional[str] = None
    date_submitted: Optional[str] = None
    resume_file_path: Optional[str] = None
    cover_letter_file_path: Optional[str] = None
    cover_letter_text: Optional[str] = None
    additional_questions: Optional[str] = None
    notes: Optional[str] = None

class Application(ApplicationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    job_posting: Optional[JobPosting] = None
    status_history: List['ApplicationStatusRecord'] = []

    class Config:
        from_attributes = True

# Base schemas for application status
class ApplicationStatusBase(BaseModel):
    application_id: int
    status: str
    source_text: Optional[str] = None

class ApplicationStatusCreate(ApplicationStatusBase):
    pass

class ApplicationStatusRecord(ApplicationStatusBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Update forward references
JobPosting.model_rebuild()
Application.model_rebuild()
ApplicationStatusRecord.model_rebuild()
