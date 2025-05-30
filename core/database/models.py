from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint, UniqueConstraint, Table
from sqlalchemy.orm import relationship
from .base import Base

# Junction table for application tags
application_tags = Table('application_tags', Base.metadata,
    Column('application_id', Integer, ForeignKey('applications.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String)
    description = Column(String)
    source_url = Column(String)
    date_posted = Column(String)  # ISO text
    date_submitted = Column(String)  # ISO text
    questions_answered = Column(String)
    description_hash = Column(String, unique=True)

    # Relationships
    applications = relationship("Application", back_populates="job_posting", cascade="all, delete")
    parsed_metadata = relationship("ParsedMetadata", back_populates="job_posting", uselist=False, cascade="all, delete")

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    original_name = Column(String)
    stored_path = Column(String, nullable=False, unique=True)
    sha256 = Column(String, nullable=False, unique=True)
    file_type = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint(file_type.in_(['resume', 'cover_letter', 'attachment', 'other']), name='check_file_type'),
    )

    # Relationships
    resume_applications = relationship("Application", foreign_keys="Application.resume_file_id", back_populates="resume_file")
    cover_letter_applications = relationship("Application", foreign_keys="Application.cover_letter_file_id", back_populates="cover_letter_file")

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_posting_id = Column(Integer, ForeignKey('job_postings.id', ondelete='CASCADE'), nullable=False)
    resume_file_id = Column(Integer, ForeignKey('files.id', ondelete='SET NULL'))
    cover_letter_file_id = Column(Integer, ForeignKey('files.id', ondelete='SET NULL'))
    submission_method = Column(String)
    notes = Column(String)

    __table_args__ = (
        CheckConstraint(submission_method.in_(['web', 'email', 'referral', 'other']), name='check_submission_method'),
    )

    # Relationships
    job_posting = relationship("JobPosting", back_populates="applications")
    resume_file = relationship("File", foreign_keys=[resume_file_id], back_populates="resume_applications")
    cover_letter_file = relationship("File", foreign_keys=[cover_letter_file_id], back_populates="cover_letter_applications")
    status_history = relationship("ApplicationStatusHistory", back_populates="application", cascade="all, delete")
    contacts = relationship("Contact", back_populates="application", cascade="all, delete")
    emails = relationship("Email", back_populates="application", cascade="all, delete")
    tags = relationship("Tag", secondary=application_tags, back_populates="applications")

class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    status = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)  # ISO datetime
    source_text = Column(String)

    # Relationships
    application = relationship("Application", back_populates="status_history")

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    role = Column(String)
    email = Column(String)
    phone = Column(String)
    first_reached = Column(String)  # ISO date
    last_contacted = Column(String)  # ISO date

    # Relationships
    application = relationship("Application", back_populates="contacts")

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    direction = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)  # ISO datetime
    subject = Column(String)
    body = Column(String)

    __table_args__ = (
        CheckConstraint(direction.in_(['sent', 'received']), name='check_email_direction'),
    )

    # Relationships
    application = relationship("Application", back_populates="emails")

class ParsedMetadata(Base):
    __tablename__ = "parsed_metadata"

    id = Column(Integer, primary_key=True, index=True)
    job_posting_id = Column(Integer, ForeignKey('job_postings.id', ondelete='CASCADE'), nullable=False, unique=True)
    tags = Column(String)  # JSON
    tech_stacks = Column(String)  # JSON
    seniority = Column(String)
    industry = Column(String)

    # Relationships
    job_posting = relationship("JobPosting", back_populates="parsed_metadata")

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    # Relationships
    applications = relationship("Application", secondary=application_tags, back_populates="tags")
