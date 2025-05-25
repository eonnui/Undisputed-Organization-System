from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime

class Organization(BaseModel):
    id: int
    name: str
    theme_color: Optional[str] = None
    custom_palette: Optional[str] = None # <--- THIS LINE IS CRUCIAL AND WAS MISSING

    class Config:
        from_attributes = True # Use from_attributes for Pydantic V2, orm_mode = True for V1

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
    last_name: str # Corrected from 'bool' if this was a typo
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
