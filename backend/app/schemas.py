from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime, date

class OrganizationBase(BaseModel):
    name: str
    theme_color: Optional[str] = None
    primary_course_code: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class Organization(OrganizationBase):
    id: int
    custom_palette: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True

class OrganizationDisplay(BaseModel):
    id: int
    name: str
    theme_color: str
    custom_palette: str
    logo_url: Optional[str] = None
    primary_course_code: Optional[str] = None

    class Config:
        from_attributes = True


class UserDataResponse(BaseModel):
    first_name: Optional[str] = None
    profile_picture: Optional[str] = None
    organization: Optional[Organization] = None
    is_verified: Optional[bool] = None

    class Config:
        from_attributes = True


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
    organization: Optional[Organization] = None
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
        from_attributes = True

class ForgotPasswordRequest(BaseModel):
    identifier: str 

class ResetPasswordRequest(BaseModel):
    identifier: str 
    code: str
    new_password: str

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

class AdminCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    password: str
    position: str
    organization_id: Optional[int] = None

class Admin(BaseModel):
    admin_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    email: EmailStr
    role: str
    position: str

    class Config:
        from_attributes = True

class OrganizationThemeUpdate(BaseModel):
    new_theme_color: str


class ExpenseBase(BaseModel):
    description: str
    amount: float
    category: Optional[str] = None
    incurred_at: Optional[date] = None
    admin_id: Optional[int] = None
    organization_id: Optional[int] = None

class ExpenseCreate(ExpenseBase):
    pass

class Expense(ExpenseBase):
    id: int
    created_at: datetime
    admin: Optional[Admin] = None
    organization: Optional[Organization] = None

    class Config:
        from_attributes = True

class NotificationBase(BaseModel):
    message: str
    url: Optional[str] = None
    is_read: bool = False 
class NotificationCreate(NotificationBase): 
    pass

class Notification(NotificationBase):
    id: int
    created_at: datetime 

    class Config:
        from_attributes = True 

class RuleWikiEntryBase(BaseModel):
    title: str
    category: str
    content: str
    image_path: Optional[str] = None 

class RuleWikiEntryCreate(RuleWikiEntryBase):
    pass 

class RuleWikiEntryUpdate(RuleWikiEntryBase):
    pass 

class RuleWikiEntry(RuleWikiEntryBase):
    id: int
    admin_id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AdminLogBase(BaseModel):
    action_type: str
    description: str
    target_entity_type: Optional[str] = None
    target_entity_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    organization_id: Optional[int] = None

class AdminLogCreate(AdminLogBase):
    pass

class AdminLog(AdminLogBase):
    id: int
    timestamp: datetime
    admin_id: int
    admin_name: Optional[str] = None
    organization_name: Optional[str] = None

    class Config:
        from_attributes = True


class ShirtCampaignBase(BaseModel):
    title: str
    description: Optional[str] = None
    price_per_shirt: float
    pre_order_deadline: date
    available_stock: int # <--- ADD THIS LINE
    gcash_number: Optional[str] = None
    gcash_name: Optional[str] = None
    is_active: bool = True
    size_chart_image_path: Optional[str] = None

class ShirtCampaignCreate(ShirtCampaignBase):
    organization_id: int 

class ShirtCampaignUpdate(ShirtCampaignBase):
    
    title: Optional[str] = None
    description: Optional[str] = None
    price_per_shirt: Optional[float] = None
    pre_order_deadline: Optional[date] = None
    gcash_number: Optional[str] = None
    gcash_name: Optional[str] = None
    is_active: Optional[bool] = None
    size_chart_image_path: Optional[str] = None


class ShirtCampaign(ShirtCampaignBase):
    id: int
    admin_id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class StudentShirtOrderBase(BaseModel):
    student_name: str
    student_year_section: str
    student_email: Optional[str] = None
    student_phone: Optional[str] = None
    shirt_size: str
    quantity: int = 1
    payment_amount: float
    payment_reference_number: Optional[str] = None
    payment_date_time: Optional[datetime] = None
    payment_screenshot_path: Optional[str] = None
    payment_status: str = "Pending"

class StudentShirtOrderCreate(StudentShirtOrderBase):
    campaign_id: int
    student_id: int 

class StudentShirtOrderUpdate(BaseModel):
    
    payment_status: Optional[str] = None
    payment_reference_number: Optional[str] = None
    payment_date_time: Optional[datetime] = None
    payment_screenshot_path: Optional[str] = None 

class StudentShirtOrder(StudentShirtOrderBase):
    id: int
    campaign_id: int
    student_id: int
    ordered_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True