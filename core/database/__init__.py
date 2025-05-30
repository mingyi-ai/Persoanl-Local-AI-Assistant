from .base import Base, engine, SessionLocal, get_db
from .models import (
    JobPosting,
    File,
    Application,
    ApplicationStatusHistory,
    Contact,
    Email,
    ParsedMetadata,
    Tag,
)

# Create all tables
Base.metadata.create_all(bind=engine)

__all__ = [
    'Base',
    'engine',
    'SessionLocal',
    'get_db',
    'JobPosting',
    'File',
    'Application',
    'ApplicationStatusHistory',
    'Contact',
    'Email',
    'ParsedMetadata',
    'Tag',
]
