# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite database URL (for development)
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Only needed for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# This is the Base class your models will inherit from
Base = declarative_base()

if __name__ == "__main__":
    from .models import User, BulletinBoard, Admin  # Import your models here
    Base.metadata.create_all(bind=engine)
    print("Database tables created!")