# backend/app/utils.py
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Admin, BulletinBoard, Event, User
from werkzeug.security import generate_password_hash
from datetime import datetime
import random

def create_single_temporary_bulletin_board_post():
    db: Session = SessionLocal()
    try:
        # 1. Create a temporary Admin (if one doesn't exist)
        admin = db.query(Admin).filter(Admin.email == "temp_bulletin_admin@example.com").first()
        if not admin:
            hashed_password = generate_password_hash("temporary_password")
            temporary_admin = Admin(name="Temp Bulletin Admin", email="temp_bulletin_admin@example.com", password=hashed_password, role="admin")
            db.add(temporary_admin)
            db.commit()
            db.refresh(temporary_admin)
            admin_id = temporary_admin.admin_id
            print(f"Temporary Admin (bulletin) created with ID: {admin_id}")
        else:
            admin_id = admin.admin_id

        # 2. Create a single temporary Bulletin Board post
        categories = ["Announcements", "Events", "General", "Lost and Found", "Study Groups"]
        titles = {
            "Announcements": ["Important Notice: System Maintenance", "Campus Closure Alert", "New Policy Update"],
            "Events": ["Upcoming Workshop: Python for Beginners", "Guest Speaker Series: Tech Innovation", "Charity Bazaar"],
            "General": ["Welcome New Students!", "Tips for Exam Preparation", "Weekend Activities"],
            "Lost and Found": ["Found: Wallet near Cafeteria", "Lost: Keys with a Blue Keychain", "Claim Your Item"],
            "Study Groups": ["Looking for Math Study Partners", "Join Our Chemistry Review Session", "Literature Discussion Group"],
        }

        chosen_category = random.choice(categories)
        chosen_title = random.choice(titles[chosen_category])
        is_pinned = random.choice([True, False])
        image_paths = [None, "/static/images/placeholder1.jpg", "/static/images/placeholder2.png"] # Add your image paths
        chosen_image_path = random.choice(image_paths)

        temporary_post = BulletinBoard(
            title=chosen_title,
            content=f"This is a temporary bulletin board post for the '{chosen_category}' category. It was created for demonstration purposes.",
            category=chosen_category,
            admin_id=admin_id,
            is_pinned=is_pinned,
            image_path=chosen_image_path,
            heart_count=random.randint(0, 15)
        )
        db.add(temporary_post)
        db.commit()
        db.refresh(temporary_post)
        print(f"Single Temporary Bulletin Board Post created with ID: {temporary_post.post_id}, Title: {chosen_title}, Category: {chosen_category}, Pinned: {is_pinned}, Image: {chosen_image_path}, Hearts: {temporary_post.heart_count}")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    from .database import Base
    Base.metadata.create_all(bind=engine)
    create_single_temporary_bulletin_board_post()
    print("Temporary admin (for bulletin) and a single temporary bulletin board post created.")