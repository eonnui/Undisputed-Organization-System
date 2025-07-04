from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Boolean, Float, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint 

event_participants = Table(
    'event_participants',
    Base.metadata,
    Column('event_id', Integer, ForeignKey('events.event_id'), primary_key=True),
    Column('student_id', Integer, ForeignKey('users.id'), primary_key=True)
)

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    theme_color = Column(String, nullable=True)
    custom_palette = Column(Text, nullable=True)
    logo_url = Column(String, nullable=True)
    primary_course_code = Column(String, nullable=True, unique=True, index=True)
    admins = relationship("Admin", secondary="organization_admins", back_populates="organizations")
    students = relationship("User", back_populates="organization")
    notifications = relationship("Notification", back_populates="organization", foreign_keys="[Notification.organization_id]")
    rule_wiki_entries_org = relationship("RuleWikiEntry", back_populates="organization")
    admin_logs = relationship("AdminLog", back_populates="organization")
    shirt_campaigns = relationship("ShirtCampaign", back_populates="organization")

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
    classification_image_url = Column(String)
    created_at = Column(DateTime, default=func.now())
    participants = relationship("User", secondary=event_participants, back_populates="joined_events")
    admin = relationship("Admin", back_populates="events")
    notifications = relationship("Notification", back_populates="event")

    def joined_count(self):
        return len(self.participants)

    @property
    def participants_list_json(self):
        """Returns a list of participant names and sections for JSON serialization."""
        return [{'name': p.name, 'section': p.section if hasattr(p, 'section') else None} for p in self.participants]
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
    payment_items = relationship("PaymentItem", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", foreign_keys="[Notification.user_id]")
    liked_posts = relationship("UserLike", back_populates="user")
    student_shirt_orders = relationship("StudentShirtOrder", back_populates="student")
class Admin(Base):
    __tablename__ = "admins"
    admin_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)
    position = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    bulletin_board_posts = relationship("BulletinBoard", back_populates="admin")
    events = relationship("Event", back_populates="admin")
    organizations = relationship("Organization", secondary="organization_admins", back_populates="admins")
    notifications = relationship("Notification", back_populates="admin", foreign_keys="[Notification.admin_id]")
    rule_wiki_entries = relationship("RuleWikiEntry", back_populates="admin")
    admin_logs = relationship("AdminLog", back_populates="admin")
    shirt_campaigns = relationship("ShirtCampaign", back_populates="admin")
    
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expiration_time = Column(DateTime, nullable=False)
    user = relationship("User")
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
    video_path = Column(String(255), nullable=True) 
    admin = relationship("Admin", back_populates="bulletin_board_posts")
    likes = relationship("UserLike", back_populates="bulletin_post")
    notifications = relationship("Notification", back_populates="bulletin_post")

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
    notifications = relationship("Notification", back_populates="payment")
    shirt_orders = relationship("StudentShirtOrder", back_populates="payment")
class PaymentItem(Base):
    __tablename__ = "payment_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
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
    student_shirt_order_id = Column(Integer, ForeignKey("student_shirt_orders.id"), unique=True, nullable=True)
    student_shirt_order = relationship("StudentShirtOrder", back_populates="payment_item", uselist=False) 
    user = relationship("User", back_populates="payment_items")
    payments = relationship("Payment", back_populates="payment_item")
    notifications = relationship("Notification", back_populates="payment_item")
class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=True)
    incurred_at = Column(Date, default=func.current_date())
    created_at = Column(DateTime, default=func.now())
    admin_id = Column(Integer, ForeignKey("admins.admin_id"), nullable=True)
    admin = relationship("Admin")
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    organization = relationship("Organization")
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    admin_id = Column(Integer, ForeignKey("admins.admin_id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    message = Column(Text, nullable=False)
    event_identifier = Column(String, nullable=True, index=True)
    notification_type = Column(String, default="general")
    bulletin_post_id = Column(Integer, ForeignKey("bulletin_board.post_id", ondelete='CASCADE'), nullable=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete='CASCADE'), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete='CASCADE'), nullable=True)
    payment_item_id = Column(Integer, ForeignKey("payment_items.id", ondelete='CASCADE'), nullable=True)
    verified_user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=True)
    rule_wiki_entry_id = Column(Integer, ForeignKey("rule_wiki_entries.id", ondelete='CASCADE'), nullable=True)
    shirt_campaign_id = Column(Integer, ForeignKey("shirt_campaigns.id", ondelete='CASCADE'), nullable=True)
    shirt_order_id = Column(Integer, ForeignKey("student_shirt_orders.id", ondelete='CASCADE'), nullable=True)
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    url = Column(String, nullable=True)
    user = relationship("User", back_populates="notifications", foreign_keys=[user_id])
    admin = relationship("Admin", back_populates="notifications", foreign_keys=[admin_id])
    organization = relationship("Organization", back_populates="notifications", foreign_keys=[organization_id])
    bulletin_post = relationship("BulletinBoard", back_populates="notifications", foreign_keys=[bulletin_post_id])
    event = relationship("Event", back_populates="notifications", foreign_keys=[event_id])
    payment = relationship("Payment", back_populates="notifications", foreign_keys=[payment_id])
    payment_item = relationship("PaymentItem", back_populates="notifications", foreign_keys=[payment_item_id])
    verified_user = relationship("User", foreign_keys=[verified_user_id])
    rule_wiki_entry = relationship("RuleWikiEntry", back_populates="notifications")
    shirt_campaign = relationship("ShirtCampaign", back_populates="notifications")
    shirt_order = relationship("StudentShirtOrder", back_populates="notifications")
class NotificationTypeConfig(Base):
    __tablename__ = "notification_type_configs"

    type_name = Column(String, primary_key=True, index=True, unique=True, nullable=False)
    display_name_plural = Column(String, nullable=True)
    group_by_type_only = Column(Boolean, default=False)
    message_template_plural = Column(String, nullable=True)
    context_phrase_template = Column(String, nullable=True)
    message_prefix_to_strip = Column(String, nullable=True)
    entity_model_name = Column(String, nullable=True)
    entity_title_attribute = Column(String, nullable=True)
    always_individual = Column(Boolean, default=False)
    message_template_individual = Column(String, nullable=True)
class UserLike(Base):
    __tablename__ = "user_likes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("bulletin_board.post_id"))
    user = relationship("User", back_populates="liked_posts")
    bulletin_post = relationship("BulletinBoard", back_populates="likes")
class RuleWikiEntry(Base):
    __tablename__ = "rule_wiki_entries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    category = Column(String)
    content = Column(Text)
    admin_id = Column(Integer, ForeignKey("admins.admin_id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    image_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    admin = relationship("Admin", back_populates="rule_wiki_entries")
    organization = relationship("Organization", back_populates="rule_wiki_entries_org")
    notifications = relationship("Notification", back_populates="rule_wiki_entry")
class AdminLog(Base):
    __tablename__ = "admin_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.admin_id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    action_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    target_entity_type = Column(String, nullable=True)
    target_entity_id = Column(Integer, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    admin = relationship("Admin", back_populates="admin_logs")
    organization = relationship("Organization", back_populates="admin_logs")
class ShirtCampaign(Base):
    __tablename__ = "shirt_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.admin_id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    title = Column(String, nullable=False)    
    description = Column(Text, nullable=True)
    prices_by_size = Column(JSON, nullable=True)    
    price_per_shirt = Column(Float, nullable=True)    
    pre_order_deadline = Column(DateTime, nullable=False)
    available_stock = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    size_chart_image_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    admin = relationship("Admin", back_populates="shirt_campaigns")
    organization = relationship("Organization", back_populates="shirt_campaigns")
    student_orders = relationship("StudentShirtOrder", back_populates="campaign", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="shirt_campaign")
class StudentShirtOrder(Base):
    __tablename__ = "student_shirt_orders"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("shirt_campaigns.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    student_name = Column(String, nullable=False)
    student_year_section = Column(String, nullable=False)
    student_email = Column(String, nullable=True)
    student_phone = Column(String, nullable=True)
    shirt_size = Column(String, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    order_total_amount = Column(Float, nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    ordered_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    campaign = relationship("ShirtCampaign", back_populates="student_orders")
    student = relationship("User", back_populates="student_shirt_orders")
    notifications = relationship("Notification", back_populates="shirt_order")
    payment = relationship("Payment", back_populates="shirt_orders")
    status = Column(String, default="pending", nullable=False)
    payment_item = relationship("PaymentItem", back_populates="student_shirt_order", uselist=False)
class OrgChartNode(Base):

    __tablename__ = "org_chart_nodes"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)    
    
    admin_id = Column(Integer, ForeignKey("admins.admin_id"), nullable=True) 
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    position = Column(String, nullable=True) 
    chart_picture_url = Column(String, nullable=True) 
    
    organization = relationship("Organization", foreign_keys=[organization_id])
    admin = relationship("Admin", foreign_keys=[admin_id])

    def __repr__(self):
        return f"<OrgChartNode(id={self.id}, org_id={self.organization_id}, admin_id={self.admin_id}, position='{self.position}')>"