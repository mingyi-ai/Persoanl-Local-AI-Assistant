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

class JobPosting(JobPostingBase):
    id: int
    created_at: datetime
    updated_at: datetime

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

class Application(ApplicationBase):
    id: int
    created_at: datetime
    updated_at: datetime

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

class ContactBase(BaseModel):
    application_id: int
    name: str
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    first_reached: Optional[str] = None
    last_contacted: Optional[str] = None

class EmailBase(BaseModel):
    application_id: int
    direction: EmailDirection
    timestamp: str
    subject: Optional[str] = None
    body: Optional[str] = None

class ParsedMetadataBase(BaseModel):
    job_posting_id: int
    tags: Optional[str] = Field(
        None,
        description="JSON string containing a list of relevant tags and skills"
    )
    tech_stacks: Optional[str] = Field(
        None,
        description="JSON string containing a list of technologies used"
    )
    seniority: Optional[str] = None
    industry: Optional[str] = None

class TagBase(BaseModel):
    name: str

# Create schemas
class FileCreate(FileBase):
    pass

class JobPostingCreate(JobPostingBase):
    pass

class ApplicationCreate(ApplicationBase):
    pass

class StatusHistoryCreate(StatusHistoryBase):
    pass

class ContactCreate(ContactBase):
    pass

class EmailCreate(EmailBase):
    pass

class ParsedMetadataCreate(ParsedMetadataBase):
    pass

class TagCreate(TagBase):
    pass

# Read schemas (including IDs)
class File(FileBase):
    id: int

    class Config:
        from_attributes = True

class JobPosting(JobPostingBase):
    id: int
    description_hash: str
    applications: List['Application'] = []
    parsed_metadata: Optional['ParsedMetadata'] = None

    class Config:
        from_attributes = True

class Application(ApplicationBase):
    id: int
    job_posting: JobPosting
    status_history: List['StatusHistory'] = []
    contacts: List['Contact'] = []
    emails: List['Email'] = []
    tags: List['Tag'] = []

    class Config:
        from_attributes = True

class StatusHistory(StatusHistoryBase):
    id: int

    class Config:
        from_attributes = True

class Contact(ContactBase):
    id: int

    class Config:
        from_attributes = True

class Email(EmailBase):
    id: int

    class Config:
        from_attributes = True

class ParsedMetadata(ParsedMetadataBase):
    id: int

    class Config:
        from_attributes = True

class Tag(TagBase):
    id: int
    applications: List[Application] = []

    class Config:
        from_attributes = True

# Update forward references
JobPosting.update_forward_refs()
Application.update_forward_refs()
