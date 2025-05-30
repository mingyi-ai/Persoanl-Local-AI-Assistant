from base import SessionLocal
from crud import init_db

def main():
    """Initialize the database."""
    db = SessionLocal()
    try:
        init_db(db)
        print("Database initialized successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    main()
