from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from . import models, schemas
from fastapi import HTTPException, status
from passlib.context import CryptContext
from typing import List

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user(db: Session, student_number: str):
    return db.query(models.User).filter(models.User.student_number == student_number).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        student_number=user.student_number,
        email=user.email,
        organization=user.organization,
        first_name=user.first_name,
        last_name=user.last_name,
        hashed_password=hashed_password,
        position=user.position
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, student_number: str, password: str):
    user = get_user(db, student_number=student_number)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user

def get_admin_by_email(db: Session, email: str):
    return db.query(models.Admin).filter(models.Admin.email == email).first() #change

def authenticate_admin(db: Session, email: str, password: str): #change
    admin = get_admin_by_email(db, email=email) #change
    if not admin:
        return None
    if not pwd_context.verify(password, admin.hashed_password): #change
        return None
    return admin

def create_admin(db: Session, admin: schemas.AdminCreate): #change
    hashed_password = pwd_context.hash(admin.password) # Hash the password
    db_admin = models.Admin(
        email=admin.email,
        name=admin.name,
        hashed_password=hashed_password, # Store the hashed password
        role=admin.role,
        organization_id=admin.organization_id
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin

def get_bulletin_board_posts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.BulletinBoard).offset(skip).limit(limit).all()

def create_bulletin_board_post(db: Session, post: schemas.BulletinBoardCreate):
    db_post = models.BulletinBoard(
        title=post.title,
        content=post.content,
        category=post.category,
        admin_id=post.admin_id,
        is_pinned=post.is_pinned,
        image_path=post.image_path
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

def get_events(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Event).options(joinedload(models.Event.participants)).offset(skip).limit(limit).all()

def get_event(db: Session, event_id: int):
    return db.query(models.Event).options(joinedload(models.Event.participants)).filter(models.Event.event_id == event_id).first()

def create_event(db: Session, event: schemas.EventCreate):
    db_event = models.Event(
        title=event.title,
        classification=event.classification,
        description=event.description,
        date=event.date,
        location=event.location,
        admin_id=event.admin_id,
        max_participants=event.max_participants,
        organization_id=event.organization_id
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def update_event(db: Session, event_id: int, event: schemas.EventBase):
    db_event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    db_event.title = event.title
    db_event.classification = event.classification
    db_event.description = event.description
    db_event.date = event.date
    db_event.location = event.location
    db_event.max_participants = event.max_participants
    db_event.organization_id = event.organization_id
    db.commit()
    db.refresh(db_event)
    return db_event
  
def delete_event(db: Session, event_id: int):
    db_event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(db_event)
    db.commit()
    return {"message": "Event deleted successfully"}