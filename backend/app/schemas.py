# schemas.py

from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime

class Organization(BaseModel):
    id: int
    name: str
    theme_color: Optional[str] = None
    custom_palette: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True # Use from_attributes for Pydantic V2, orm_mode = True for V1

class UserDataResponse(BaseModel):
    first_name: Optional[str] = None
    profile_picture: Optional[str] = None
    organization: Optional[Organization] = None

    class Config:
        from_attributes = True # orm_mode = True for Pydantic V1.x


class UserBase(BaseModel):
    student_number: str
    email: EmailStr

class UserCreate(UserBase):
    organization: str
    first_name: str
    last_name: str
    password: str

class UserLogin(BaseModel):
    identifier: str
    password: str

class User(UserBase):
    id: int
    organization: Optional[Organization] = None # Ensure this is Optional[Organization] object
    first_name: str
    last_name: str
    is_active: bool
    name: Optional[str]
    campus: Optional[str]
    semester: Optional[str]
    course: Optional[str]
    school_year: Optional[str]
    year_level: Optional[str]
    section: Optional[str]
    address: Optional[str]
    birthdate: Optional[str]
    sex: Optional[str]
    contact: Optional[str]
    guardian_name: Optional[str]
    guardian_contact: Optional[str]
    registration_form: Optional[str]
    profile_picture: Optional[str]
    is_verified: bool
    verified_by: Optional[str]
    verification_date: Optional[datetime]

    class Config:
        from_attributes = True # For Pydantic V2, orm_mode=True for V1

class UserUpdate(BaseModel):
    name: Optional[str]
    campus: Optional[str]
    semester: Optional[str]
    course: Optional[str]
    school_year: Optional[str]
    year_level: Optional[str]
    section: Optional[str]
    address: Optional[str]
    birthdate: Optional[str]
    sex: Optional[str]
    contact: Optional[str]
    guardian_name: Optional[str]
    guardian_contact: Optional[str]
    registration_form: Optional[str]
    profile_picture: Optional[str]

# --- New Pydantic Schemas for Admin Organization and Admin Management ---
class OrganizationCreate(BaseModel):
    name: str
    theme_color: str

class AdminCreate(BaseModel):
    email: str
    password: str
    name: Optional[str] = "Admin"
    position: str # <--- ADD THIS LINE
    organization_id: Optional[int] = None

# Added Admin schema to represent the Admin model in responses
class Admin(BaseModel):
    admin_id: int
    name: str
    email: EmailStr
    role: str
    position: str # <--- ADD THIS LINE as well, if Admin responses should include position
    # Do NOT include password here for security reasons

    class Config:
        from_attributes = True # For Pydantic V2, orm_mode=True for V1

class OrganizationThemeUpdate(BaseModel):
    new_theme_color: str

class OrganizationDisplay(BaseModel):
    id: int
    name: str
    theme_color: str
    custom_palette: str
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True # Changed to from_attributes for Pydantic V2