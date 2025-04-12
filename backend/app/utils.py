# backend/app/utils.py
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Admin, BulletinBoard, Event, User
from werkzeug.security import generate_password_hash
from datetime import datetime
import random

def create_single_temporary_event_with_variations():
    db: Session = SessionLocal()
    try:
        # 1. Create a temporary Admin (if one doesn't exist)
        admin = db.query(Admin).filter(Admin.email == "varied_event_admin@example.com").first()
        if not admin:
            hashed_password = generate_password_hash("temporary_password")
            temporary_admin = Admin(name="Varied Event Admin", email="varied_event_admin@example.com", password=hashed_password, role="admin")
            db.add(temporary_admin)
            db.commit()
            db.refresh(temporary_admin)
            admin_id = temporary_admin.admin_id
            print(f"Temporary Admin (varied event) created with ID: {admin_id}")
        else:
            admin_id = admin.admin_id

        # 2. Create a single temporary Event with variations
        classifications = ["Academic", "Sports", "Arts", "Music", "Esports", "Cultural"]
        locations = ["Lecture Hall A", "Campus Gym", "Art Gallery", "Music Room 1", "Esports Arena", "Student Union Hall"]
        titles = {
            "Academic": ["Study Session: Calculus", "Research Workshop", "Debate Club Meeting"],
            "Sports": ["Intramural Basketball Game", "Yoga Class", "Fun Run Registration"],
            "Arts": ["Pottery Workshop", "Painting Session", "Film Screening"],
            "Music": ["Acoustic Night", "Choir Practice", "Music Theory Seminar"],
            "Esports": ["League of Legends Tournament", "Valorant Scrims", "Fighting Game Night"],
            "Cultural": ["International Food Festival Prep", "Language Exchange", "Cultural Dance Rehearsal"],
        }
        tag_map = {
            "Academic": "tag-academic",
            "Sports": "tag-sports",
            "Arts": "tag-arts",
            "Music": "tag-music",
            "Esports": "tag-esports",
            "Cultural": "tag-cultural",
        }
        max_participants_options = [None, 15, 30, 60, 100]

        chosen_classification = random.choice(classifications)
        chosen_location = random.choice(locations)
        chosen_title = random.choice(titles[chosen_classification])
        chosen_max_participants = 1
        chosen_date = datetime(2025, random.randint(6, 8), random.randint(1, 28), random.randint(10, 18), 0, 0)
        chosen_tag = tag_map[chosen_classification]

        temporary_event = Event(
            title=chosen_title,
            classification=chosen_classification, # Using classification as the primary tag
            description=f"A temporary event for the {chosen_classification} category.",
            date=chosen_date,
            location=chosen_location,
            admin_id=admin_id,
            max_participants=chosen_max_participants,
            # If you had a dedicated tags column, you could do something like:
            # tags=[chosen_tag, "another-potential-tag"]
        )
        db.add(temporary_event)
        db.commit()
        db.refresh(temporary_event)
        print(f"Single Temporary Event created with ID: {temporary_event.event_id}, Title: {chosen_title}, Classification: {chosen_classification}, Max Participants: {chosen_max_participants}, Tag: {chosen_tag}")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    from .database import Base
    Base.metadata.create_all(bind=engine)
    create_single_temporary_event_with_variations()
    print("Temporary admin (for varied event) and a single temporary event with variations created.")