from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    student_number: str
    email: EmailStr

class UserCreate(UserBase):
    organization: str
    first_name: str
    last_name: str
    password: str

class UserLogin(BaseModel):
    student_number: str
    password: str

class User(UserBase):
    id: int
    organization: str
    first_name: str
    last_name: str
    is_active: bool
    
    class Config:
        from_attributes = True