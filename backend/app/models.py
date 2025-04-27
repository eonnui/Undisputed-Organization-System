# backend/app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# Association table for events and participants (many-to-many)
event_participants = Table(
    'event_participants',
    Base.metadata,
    Column('event_id', Integer, ForeignKey('events.event_id'), primary_key=True),
    Column('student_id', Integer, ForeignKey('users.id'), primary_key=True)
)

class Event(Base):
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    classification = Column(String)  # Renamed 'tagged' to 'classification' for clarity
    description = Column(Text)
    date = Column(DateTime)
    location = Column(String)
    admin_id = Column(Integer, ForeignKey("admins.admin_id"))
    max_participants = Column(Integer)
    participants = relationship("User", secondary=event_participants, back_populates="joined_events")
    admin = relationship("Admin", back_populates="events")

    def joined_count(self):
        return len(self.participants)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    student_number = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    organization = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    joined_events = relationship("Event", secondary=event_participants, back_populates="participants")
    name = Column(String)
    campus = Column(String)
    semester = Column(String)
    second = Column(String)
    school_year = Column(String)
    section = Column(String)
    address = Column(String)

# Ensure Admin model is also present (as defined previously)
class Admin(Base):
    __tablename__ = "admins"
    admin_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)
    bulletin_board_posts = relationship("BulletinBoard", back_populates="admin")
    events = relationship("Event", back_populates="admin")

class BulletinBoard(Base):
    __tablename__ = "bulletin_board"
    post_id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150))
    content = Column(Text)
    category = Column(String)
    created_at = Column(DateTime, default=func.now())
    is_pinned = Column(Boolean, default=False)
    heart_count = Column(Integer, default=0)
    admin_id = Column(Integer, ForeignKey("admins.admin_id"))
    image_path = Column(String(255), nullable=True)
    admin = relationship("Admin", back_populates="bulletin_board_posts")