from typing import Optional, List, Dict 
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date

class OrganizationBase(BaseModel):
    name: str
    theme_color: Optional[str] = None
    primary_course_code: Optional[str] = None

class ParticipantResponse(BaseModel):
    name: str
    section: Optional[str] = None

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
    role: Optional[str] = None
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
    guardian_name: Optional[str] = None 
    guardian_contact: Optional[str] = None 
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
    first_name: Optional[str] = None 
    last_name: Optional[str] = None 
    name: Optional[str] = None 
    campus: Optional[str] = None
    semester: Optional[str] = None
    course: Optional[str] = None
    school_year: Optional[str] = None
    year_level: Optional[str] = None
    section: Optional[str] = None
    address: Optional[str] = None
    birthdate: Optional[str] = None
    sex: Optional[str] = None
    contact: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_contact: Optional[str] = None
    registration_form: Optional[str] = None
    profile_picture: Optional[str] = None

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
    price_per_shirt: Optional[float] = None    
    prices_by_size: Optional[Dict[str, float]] = None
    pre_order_deadline: datetime
    available_stock: int
    is_active: bool = True
    size_chart_image_path: Optional[str] = None

class ShirtCampaignCreate(ShirtCampaignBase):    
    prices_by_size: Dict[str, float] = Field(..., description="Dictionary of sizes to prices")

class ShirtCampaignUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None    
    price_per_shirt: Optional[float] = None    
    prices_by_size: Optional[Dict[str, float]] = None
    pre_order_deadline: Optional[datetime] = None
    available_stock: Optional[int] = None 
    is_active: Optional[bool] = None
    size_chart_image_path: Optional[str] = None

class ShirtCampaign(ShirtCampaignBase):
    id: int
    admin_id: Optional[int] = None 
    organization_id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class PaymentItemBase(BaseModel):
    id: int
    user_id: int
    fee: float
    is_paid: bool
    
    academic_year: Optional[str] = None
    semester: Optional[str] = None
    due_date: Optional[date] = None
    year_level_applicable: Optional[str] = None
    is_past_due: Optional[bool] = None
    is_not_responsible: Optional[bool] = None
    created_at: datetime
    updated_at: Optional[datetime] = None 
    student_shirt_order_id: Optional[int] = None 

    class Config:
        from_attributes = True

class PaymentSchema(BaseModel):
    id: int
    paymaya_payment_id: Optional[str] = None
    amount: float
    status: str 
    created_at: datetime
    updated_at: Optional[datetime] = None 
    user_id: Optional[int] = None 
    payment_item_id: Optional[int] = None 
    
    payment_item: Optional[PaymentItemBase] = None

    class Config:
        from_attributes = True

class StudentShirtOrderBase(BaseModel):
    student_name: str
    student_year_section: str
    student_email: Optional[str] = None
    student_phone: Optional[str] = None
    shirt_size: str
    quantity: int = 1
    order_total_amount: Optional[float] = None 

class StudentShirtOrderCreate(StudentShirtOrderBase):
    campaign_id: int
    student_id: int

class StudentShirtOrderUpdate(BaseModel):
    student_name: Optional[str] = None
    student_year_section: Optional[str] = None
    student_email: Optional[str] = None
    student_phone: Optional[str] = None
    shirt_size: Optional[str] = None
    quantity: Optional[int] = None
    order_total_amount: Optional[float] = None
    status: Optional[str] = None

class StudentShirtOrder(StudentShirtOrderBase):
    id: int
    campaign_id: int
    student_id: int
    ordered_at: datetime
    updated_at: datetime
    payment_id: Optional[int] = None 

    campaign: Optional[ShirtCampaign] = None
    payment: Optional[PaymentSchema] = None

    class Config:
        from_attributes = True
class OrgChartNodeDisplay(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    position: Optional[str] = None
    chart_picture_url: Optional[str] = None
    organization_name: Optional[str] = None

    class Config:
        from_attributes = True 
class UpdateOrgChartNodeTextRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    position: Optional[str] = None

class OrgChartNodeUpdateResponse(BaseModel):
    message: str
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    position: Optional[str] = None
    chart_picture_url: Optional[str] = None 

class AdminDisplay(BaseModel):
    id: int = Field(alias="admin_id") 
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    position: Optional[str] = None
    profile_picture: Optional[str] = None 

    class Config:
        orm_mode = True 
        populate_by_name = True 
class UserLikedPost(BaseModel): 
    id: int
    first_name: str
    last_name: str
    profile_picture: Optional[str] = None 

    class Config:
        from_attributes = True 
class LikedUsersResponse(BaseModel):
    post_id: int
    title: str
    likers: List[UserLikedPost] 

class OrgChartNodeOverwriteRequest(BaseModel):
    existing_admin_id: int 