# backend/app/utils.py
from sqlalchemy.orm import Session
from .database import SessionLocal, engine  # Import your SessionLocal and engine
from .models import Admin, BulletinBoard  # Import your SQLAlchemy models
from werkzeug.security import generate_password_hash  # For hashing the admin password

def create_temporary_entry():
    db: Session = SessionLocal()
    try:
        # 1. Create a temporary Admin user
        hashed_password = generate_password_hash("temporary_admin_password")
        temporary_admin = Admin(
            name="Temporary Admin",
            email="temp.admin@example.com",
            password=hashed_password,
            role="admin"
        )
        db.add(temporary_admin)
        db.commit()
        db.refresh(temporary_admin)
        print(f"Temporary Admin created with ID: {temporary_admin.admin_id}")

        # 2. Create a temporary Bulletin Board post associated with the admin
        temporary_post = BulletinBoard(
            title="Important Announcement!",
            content="This is a temporary announcement for testing purposes on the bulletin board.",
            category="General",
            is_pinned=True,
            heart_count=5,
            admin_id=temporary_admin.admin_id,  # Link to the temporary admin
            image_path=None  # You can set a path here if you have a test image
        )
        db.add(temporary_post)
        db.commit()
        db.refresh(temporary_post)
        print(f"Temporary Bulletin Board post created with ID: {temporary_post.post_id}")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    from .database import Base  # Import Base here to ensure tables are created
    Base.metadata.create_all(bind=engine) # Create tables if they don't exist (redundant if you ran database.py)
    create_temporary_entry()
    print("Temporary admin and bulletin board post created.")