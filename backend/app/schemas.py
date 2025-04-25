# backend/app/schemas.py
from pydantic import BaseModel, EmailStr, constr
from typing import List, Optional
from enum import Enum
from datetime import datetime

#class OrganizationBase(BaseModel): #removed
#    name: str
#    description: str

#class OrganizationCreate(OrganizationBase): #removed
#    pass

#class Organization(OrganizationBase):  #removed
#    organization_id: int

#    class Config:
#        from_attributes = True
        
class OrganizationPosition(str, Enum): # Added Enum class
    PRESIDENT = "President"
    VICE_PRESIDENT = "Vice President"
    SECRETARY = "Secretary"
    TREASURER_AUDITOR = "Treasurer/Auditor"
    PIO = "PIO"  # Public Information Officer
    
class AdminBase(BaseModel):
    email: EmailStr
    name: str
    #organization_id: int # Removed
    
class AdminCreate(AdminBase):
    password: str
    role: str
    organization_id: int

class Admin(AdminBase):
    admin_id: int
    role: str
    organization_id: int

    class Config:
        from_attributes = True
        
class AdminLogin(BaseModel):
    email: EmailStr
    password: str
    
class UserBase(BaseModel):
    student_number: str
    email: EmailStr

class UserCreate(UserBase):
    organization: str
    first_name: str
    last_name: str
    password: str
    position: Optional[OrganizationPosition] #add position

class UserLogin(BaseModel):
    student_number: str
    password: str

class User(UserBase):
    id: int
    organization: str
    first_name: str
    last_name: str
    is_active: bool
    position: Optional[OrganizationPosition] #add position
    #admin_id: Optional[int]

    class Config:
        from_attributes = True

# Schemas for BulletinBoard
class BulletinBoardBase(BaseModel):
    title: str
    content: str
    category: str
    is_pinned: bool = False
    image_path: Optional[str] = None

class BulletinBoardCreate(BulletinBoardBase):
    admin_id: int

class BulletinBoard(BulletinBoardBase):
    post_id: int
    created_at: datetime  # ✅ Use lowercase
    heart_count: int
    admin_id: int

    class Config:
        from_attributes = True
        
# Schemas for Events
class EventBase(BaseModel):
    title: str
    classification: str
    description: str
    date: datetime
    location: str
    max_participants: int
    organization_id: int

class EventCreate(EventBase):
    admin_id: int

class Event(EventBase):
    event_id: int
    admin_id: int

    class Config:
        from_attributes = True
        
class EventWithParticipants(Event):
    participants: List[User]