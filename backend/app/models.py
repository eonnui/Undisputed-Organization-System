from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

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
    image_path = Column(String(255), nullable=True)  # New column for image path

    admin = relationship("Admin", back_populates="bulletin_board_posts")

    def __repr__(self):
        return f"<Post id={self.post_id}, title='{self.title}' image='{self.image_path}'>"

class Admin(Base):
    __tablename__ = "admins"
    admin_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)
    bulletin_board_posts = relationship("BulletinBoard", back_populates="admin")
