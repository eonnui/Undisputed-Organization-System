from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Boolean, Float, Date
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

# New Organization Model
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    theme_color = Column(String, nullable=True)
    custom_palette = Column(Text, nullable=True)
    logo_url = Column(String, nullable=True) # <--- ADDED THIS LINE
    admins = relationship("Admin", secondary="organization_admins", back_populates="organizations")
    students = relationship("User", back_populates="organization")

# Association table for organizations and admins (many-to-many)
organization_admins = Table(
    'organization_admins',
    Base.metadata,
    Column('organization_id', Integer, ForeignKey('organizations.id'), primary_key=True),
    Column('admin_id', Integer, ForeignKey('admins.admin_id'), primary_key=True)
)

class Event(Base):
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    classification = Column(String)
    description = Column(Text)
    date = Column(DateTime)
    location = Column(String)
    admin_id = Column(Integer, ForeignKey("admins.admin_id"))
    max_participants = Column(Integer)
    created_at = Column(DateTime, default=func.now()) # <--- ADDED THIS LINE
    participants = relationship("User", secondary=event_participants, back_populates="joined_events")
    admin = relationship("Admin", back_populates="events")

    def joined_count(self):
        return len(self.participants)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    student_number = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    organization = relationship("Organization", back_populates="students")
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    joined_events = relationship("Event", secondary=event_participants, back_populates="participants")
    name = Column(String, nullable=True)
    campus = Column(String, nullable=True)
    semester = Column(String, nullable=True)
    course = Column(String, nullable=True)
    school_year = Column(String, nullable=True)
    year_level = Column(String, nullable=True)
    section = Column(String, nullable=True)
    address = Column(String, nullable=True)
    birthdate = Column(String, nullable=True)
    sex = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    guardian_name = Column(String, nullable=True)
    guardian_contact = Column(String, nullable=True)
    registration_form = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String, nullable=True)
    verification_date = Column(DateTime, nullable=True)
    payments = relationship("Payment", back_populates="user")
    payment_items = relationship("PaymentItem", back_populates="user")

class Admin(Base):
    __tablename__ = "admins"
    admin_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)
    position = Column(String, nullable=True) # <--- ADDED THIS LINE
    bulletin_board_posts = relationship("BulletinBoard", back_populates="admin")
    events = relationship("Event", back_populates="admin")
    organizations = relationship("Organization", secondary="organization_admins", back_populates="admins")

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

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Float, nullable=False)
    paymaya_payment_id = Column(String, unique=True, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(Date, default=func.current_date())
    updated_at = Column(Date, onupdate=func.current_date())
    payment_item_id = Column(Integer, ForeignKey("payment_items.id"), nullable=True)
    payment_item = relationship("PaymentItem", back_populates="payments")
    user = relationship("User", back_populates="payments")

class PaymentItem(Base):
    __tablename__ = "payment_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    academic_year = Column(String, nullable=True)
    semester = Column(String, nullable=True)
    fee = Column(Float, nullable=False)
    created_at = Column(Date, default=func.current_date())
    updated_at = Column(Date, onupdate=func.current_date())
    is_paid = Column(Boolean, default=False)
    due_date = Column(Date, nullable=True)
    year_level_applicable = Column(Integer, nullable=True)
    is_past_due = Column(Boolean, default=False)
    is_not_responsible = Column(Boolean, default=False)

    user = relationship("User", back_populates="payment_items")
    payments = relationship("Payment", back_populates="payment_item")
