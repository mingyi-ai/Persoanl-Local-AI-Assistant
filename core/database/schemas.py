from pydantic import BaseModel, constr
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums for validation
class FileType(str, Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    ATTACHMENT = "attachment"
    OTHER = "other"

class SubmissionMethod(str, Enum):
    WEB = "web"
    EMAIL = "email"
    REFERRAL = "referral"
    OTHER = "other"

class EmailDirection(str, Enum):
    SENT = "sent"
    RECEIVED = "received"

# Base schemas
class FileBase(BaseModel):
    original_name: Optional[str] = None
    stored_path: str
    sha256: str
    file_type: FileType

class JobPostingBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    date_posted: Optional[str] = None
    questions_answered: Optional[str] = None

class ApplicationBase(BaseModel):
    job_posting_id: int
    resume_file_id: Optional[int] = None
    cover_letter_file_id: Optional[int] = None
    submission_method: Optional[SubmissionMethod] = None
    notes: Optional[str] = None

class StatusHistoryBase(BaseModel):
    application_id: int
    status: str
    timestamp: str
    source_text: Optional[str] = None

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
    tags: Optional[str] = None
    tech_stacks: Optional[str] = None
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
        orm_mode = True

class JobPosting(JobPostingBase):
    id: int
    description_hash: str
    applications: List['Application'] = []
    parsed_metadata: Optional['ParsedMetadata'] = None

    class Config:
        orm_mode = True

class Application(ApplicationBase):
    id: int
    job_posting: JobPosting
    status_history: List['StatusHistory'] = []
    contacts: List['Contact'] = []
    emails: List['Email'] = []
    tags: List['Tag'] = []

    class Config:
        orm_mode = True

class StatusHistory(StatusHistoryBase):
    id: int

    class Config:
        orm_mode = True

class Contact(ContactBase):
    id: int

    class Config:
        orm_mode = True

class Email(EmailBase):
    id: int

    class Config:
        orm_mode = True

class ParsedMetadata(ParsedMetadataBase):
    id: int

    class Config:
        orm_mode = True

class Tag(TagBase):
    id: int
    applications: List[Application] = []

    class Config:
        orm_mode = True

# Update forward references
JobPosting.update_forward_refs()
Application.update_forward_refs()
