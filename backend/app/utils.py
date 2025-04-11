# backend/app/utils.py
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Admin, BulletinBoard, Event, User  # Import the Event and User models
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_temporary_entry():
    db: Session = SessionLocal()
    try:
        # ... (previous temporary admin and bulletin board code) ...

        # 3. Create a temporary Event
        temporary_event = Event(
            title="Campus Fun Day",
            classification="Social",
            description="A day full of fun activities for all students!",
            date=datetime(2025, 5, 25, 10, 0, 0),
            location="Main Grounds",
            admin_id=1,  # Assuming admin with ID 1 exists from the previous entry
            max_participants=50,
        )
        db.add(temporary_event)
        db.commit()
        db.refresh(temporary_event)
        print(f"Temporary Event created with ID: {temporary_event.event_id}")

        # 4. Add some temporary participants to the event
        user1 = db.query(User).first()  # Get the first user (you might need to create some users first)
        if user1:
            temporary_event.participants.append(user1)
            db.commit()
            db.refresh(temporary_event)
            print(f"Added participant {user1.student_number} to Event {temporary_event.event_id}")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    from .database import Base
    Base.metadata.create_all(bind=engine)
    create_temporary_entry()
    print("Temporary admin, bulletin board post, and event created (with a participant).")