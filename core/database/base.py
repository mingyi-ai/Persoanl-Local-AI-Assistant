from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pathlib import Path
from typing import Generator
from contextlib import contextmanager

def get_database_path() -> Path:
    """Get the database file path."""
    return Path(__file__).parent.parent.parent / "data" / "job_applications.db"

def create_database_engine():
    """Create and return the database engine."""
    DATABASE_PATH = get_database_path()
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
    
    # Ensure the directory exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create the database URL - using the same path as before
DATABASE_PATH = get_database_path()
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create SQLAlchemy engine
engine = create_database_engine()

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
