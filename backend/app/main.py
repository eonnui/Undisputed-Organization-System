from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Form, APIRouter, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_, or_, extract
from . import models, schemas, crud
from .database import SessionLocal, engine
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from io import BytesIO
from PIL import Image
from collections import defaultdict, OrderedDict
import os
import secrets
import re
import requests
import base64
import bcrypt
import shutil
import calendar
from dateutil.relativedelta import relativedelta
import logging

# Import SessionMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Import text extraction functions
from .text import extract_text_from_pdf, extract_student_info


# Initialize database and FastAPI app
models.Base.metadata.create_all(bind=engine)
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

# Define base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static"
UPLOAD_BASE_DIRECTORY = STATIC_DIR / "images"
UPLOAD_BASE_DIRECTORY.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory=BASE_DIR / "frontend" / "templates")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function to generate secure filenames
def generate_secure_filename(original_filename: str) -> str:
    _, file_extension = os.path.splitext(original_filename)
    random_prefix = secrets.token_hex(16)
    return f"{random_prefix}{file_extension}"

# Helper to delete old files
def delete_file_from_path(file_path: Optional[str]):
    if file_path:
        full_path = STATIC_DIR / file_path.lstrip("/")
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                logging.error(f"Error deleting old file {full_path}: {e}")

# Helper to handle file uploads
async def handle_file_upload(
    upload_file: UploadFile,
    subdirectory: str,
    allowed_types: List[str],
    max_size_bytes: Optional[int] = None,
    old_file_path: Optional[str] = None
) -> str:
    if upload_file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only {', '.join(allowed_types)} are allowed for {subdirectory}.",
        )

    if old_file_path:
        delete_file_from_path(old_file_path)

    file_content = await upload_file.read()
    if max_size_bytes and len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size too large. Maximum allowed size is {max_size_bytes} bytes.",
        )

    filename = generate_secure_filename(upload_file.filename)
    save_path = STATIC_DIR / subdirectory / filename
    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(save_path, "wb") as f:
            f.write(file_content)
        return f"/static/{subdirectory}/{filename}"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file to {save_path}: {e}",
        )

# Helper to get current admin and their organization
def get_current_admin_with_org(request: Request, db: Session = Depends(get_db)) -> Tuple[models.Admin, models.Organization]:
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as admin.")
    admin = db.query(models.Admin).options(joinedload(models.Admin.organizations)).filter(models.Admin.admin_id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found.")
    if not admin.organizations:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin is not associated with an organization.")
    return admin, admin.organizations[0]

# Helper to get current user and their organization
def get_current_user_with_org(request: Request, db: Session = Depends(get_db)) -> Tuple[models.User, Optional[models.Organization]]:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as user.")
    user = db.query(models.User).options(joinedload(models.User.organization)).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user, user.organization

# Helper to prepare common template context
async def get_base_template_context(request: Request, db: Session) -> Dict[str, Any]:
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")
    user_role = request.session.get("user_role")

    logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    organization_id = None

    if user_role == "Admin" and admin_id:
        admin = db.query(models.Admin).options(joinedload(models.Admin.organizations)).filter(models.Admin.admin_id == admin_id).first()
        if admin and admin.organizations:
            organization = admin.organizations[0]
            organization_id = organization.id
            if organization.logo_url:
                logo_url = organization.logo_url
    elif user_role == "user" and user_id:
        user = db.query(models.User).options(joinedload(models.User.organization)).filter(models.User.id == user_id).first()
        if user and user.organization:
            organization_id = user.organization.id
            if user.organization.logo_url:
                logo_url = user.organization.logo_url

    return {
        "request": request,
        "year": str(datetime.now().year),
        "logo_url": logo_url,
        "organization_id": organization_id,
        "current_user_id": user_id 
    }

# Router for API endpoints
router = APIRouter()

@router.get("/get_user_notifications", response_class=JSONResponse)
async def get_notifications_route(
    request: Request,
    db: Session = Depends(get_db),
    organization_id: Optional[int] = Query(None, description="Optional organization ID to filter notifications.")
) -> JSONResponse:
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")

    raw_notifications = []
    if user_id:
        raw_notifications = crud.get_notifications(db, user_id=user_id)
    elif admin_id:
        raw_notifications = crud.get_notifications(db, admin_id=admin_id)
    elif organization_id:
        raw_notifications = crud.get_notifications(db, organization_id=organization_id)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated or no organization ID provided.")
    
    config_map = crud.get_all_notification_configs_as_map(db)
    final_notifications_data = crud.process_and_format_notifications(db, raw_notifications, config_map)
    return JSONResponse(content={"notifications": final_notifications_data})

# Admin Bulletin Board Post Creation
@router.post("/admin/bulletin_board/post", response_class=HTMLResponse, name="admin_post_bulletin")
async def admin_post_bulletin(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    is_pinned: Optional[bool] = Form(False),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    admin, admin_org = get_current_admin_with_org(request, db)

    image_path = None
    if image and image.filename:
        image_path = await handle_file_upload(
            image,
            "images/bulletin_board",
            ["image/jpeg", "image/png", "image/gif", "image/svg+xml"],
            max_size_bytes=5 * 1024 * 1024 
        )

    db_post = models.BulletinBoard(
        title=title,
        content=content,
        category=category,
        is_pinned=is_pinned,
        admin_id=admin.admin_id,
        image_path=image_path,
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    users_in_org = db.query(models.User).filter(models.User.organization_id == admin_org.id).all()
    for user in users_in_org:
        crud.create_notification(
            db,
            message=f"New bulletin post: '{title}'",
            organization_id=admin_org.id,
            user_id=user.id,
            notification_type="bulletin_post",
            entity_id=db_post.post_id,
            url=f"/BulletinBoard#{db_post.post_id}"
        )
    db.commit() 
    return RedirectResponse(url="/admin/bulletin_board", status_code=status.HTTP_303_SEE_OTHER)

# Admin Settings Page
@router.get("/admin_settings/", response_class=HTMLResponse, name="admin_settings")
async def admin_settings(request: Request, db: Session = Depends(get_db)):
    admin, organization = get_current_admin_with_org(request, db) 

    context = await get_base_template_context(request, db)
    context.update({
        "organization_id": organization.id,
        "current_theme_color": organization.theme_color,
    })
    return templates.TemplateResponse("admin_dashboard/admin_settings.html", context)

# Admin Event Creation
@router.post("/admin/events/create", name="admin_create_event")
async def admin_create_event(
    request: Request,
    title: str = Form(...),
    classification: str = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    max_participants: int = Form(...),
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)

    try:
        event_date = datetime.strptime(date, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date and time format. Please use Year-MM-DDTHH:MM (e.g., 2025-05-27T14:30).")

    db_event = models.Event(
        title=title,
        classification=classification,
        description=description,
        date=event_date,
        location=location,
        max_participants=max_participants,
        admin_id=admin.admin_id,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    users_in_org = db.query(models.User).filter(models.User.organization_id == admin_org.id).all()
    for user in users_in_org:
        crud.create_notification(
            db,
            message=f"New event: '{title}' on {event_date.strftime('%Y-%m-%d at %H:%M')}",
            organization_id=admin_org.id,
            user_id=user.id,
            notification_type="event",
            entity_id=db_event.event_id,
            url=f"/Events#{db_event.event_id}"
        )
    db.commit() 
    return RedirectResponse(url="/admin/events", status_code=status.HTTP_303_SEE_OTHER)

# Admin Event Deletion
@router.post("/admin/events/delete/{event_id}", response_class=HTMLResponse, name="admin_delete_event")
async def admin_delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    db.delete(event)
    db.commit()
    return RedirectResponse(url="/admin/events", status_code=status.HTTP_303_SEE_OTHER)

# Admin Bulletin Post Deletion
@router.post("/admin/bulletin_board/delete/{post_id}", response_class=HTMLResponse, name="admin_delete_bulletin_post")
async def admin_delete_bulletin_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(models.BulletinBoard).filter(models.BulletinBoard.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    db.delete(post)
    db.commit()
    return RedirectResponse(url="/admin/bulletin_board", status_code=status.HTTP_303_SEE_OTHER)

# Admin Payments Page
@router.get("/Admin/payments", response_class=HTMLResponse, name="admin_payments")
async def admin_payments(
    request: Request,
    db: Session = Depends(get_db),
    student_number: Optional[str] = None,
):
    admin, organization = get_current_admin_with_org(request, db)

    query = db.query(models.PaymentItem).join(models.User).filter(models.User.organization_id == organization.id)
    if student_number:
        query = query.filter(models.User.student_number == student_number)
    payment_items = query.all()

    payment_items_with_status = []
    for item in payment_items:
        status_text = "Unpaid"
        if item.is_not_responsible:
            status_text = "Not Responsible"
        elif item.is_paid:
            status_text = "Paid"
        elif item.is_past_due:
            status_text = "Past Due"
        payment_items_with_status.append({
            "item": item,
            "status": status_text,
            "student_number": item.user.student_number if item.user else None,
        })      
    
    context = await get_base_template_context(request, db)
    context.update({
        "payment_items": payment_items_with_status,
        "now": date.today(),
        "student_number": student_number,
    })
    return templates.TemplateResponse("admin_dashboard/admin_payments.html", context)

# Admin Payment History
@router.get("/admin/Payments/History", response_class=JSONResponse, name="admin_payment_history")
async def admin_payment_history(request: Request, db: Session = Depends(get_db)):
    admin, organization = get_current_admin_with_org(request, db)

    member_ids = [member.id for member in db.query(models.User).filter(models.User.organization_id == organization.id).all()]
    payments = db.query(models.Payment).options(joinedload(models.Payment.payment_item), joinedload(models.Payment.user)).filter(
        models.Payment.user_id.in_(member_ids)
    ).order_by(models.Payment.created_at.desc(), models.Payment.id.desc()).all()

    payment_history_data = []
    for payment in payments:
        payment_item = payment.payment_item
        user = payment.user

        if not all([payment_item, user, payment_item.academic_year, payment_item.semester, payment_item.fee, payment.amount, payment.status, payment_item.due_date, payment.created_at, user.first_name, user.last_name, user.student_number]):
            continue

        status_text = payment.status
        if status_text == "pending": status_text = "Pending"
        elif status_text == "success": status_text = "Paid"                
        elif status_text == "failed": status_text = "Failed"
        elif status_text == "cancelled": status_text = "Cancelled"

        payment_history_data.append({
            "item": {
                "id": payment.id,
                "amount": payment.amount,
                "paymaya_payment_id": payment.paymaya_payment_id,
                "status": payment.status,
                "created_at": payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "updated_at": payment.updated_at.strftime('%Y-%m-%d %H:%M:%S') if payment.updated_at else None,
                "payment_item": {
                    "academic_year": payment_item.academic_year,
                    "semester": payment_item.semester,
                    "fee": payment_item.fee,
                    "due_date": payment_item.due_date.strftime('%Y-%m-%d'),
                    "is_not_responsible": payment_item.is_not_responsible
                }
            },
            "status": status_text,
            "user_name": f"{user.first_name} {user.last_name}",
            "student_number": user.student_number,
            "payment_date": payment.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return JSONResponse(content={"payment_history": payment_history_data})

# Update Payment Status
@router.post("/admin/payment/{payment_item_id}/update_status")
async def update_payment_status(
    request: Request,
    payment_item_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    admin, _ = get_current_admin_with_org(request, db) 

    allowed_statuses = ["Unpaid", "Paid", "NOT RESPONSIBLE"]
    if status not in allowed_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {status}. Allowed statuses are: {allowed_statuses}")

    payment_item = db.query(models.PaymentItem).get(payment_item_id)
    if not payment_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment item {payment_item_id} not found")

    if status == "Unpaid":
        payment_item.is_past_due = False
        payment_item.is_paid = False
        payment_item.is_not_responsible = False
    elif status == "Paid":
        payment_item.is_past_due = False
        payment_item.is_paid = True
        payment_item.is_not_responsible = False
        existing_payment = db.query(models.Payment).filter(models.Payment.payment_item_id == payment_item_id).first()
        if existing_payment:
            existing_payment.amount = payment_item.fee
            existing_payment.status = "success"
        else:
            new_payment = models.Payment(user_id=payment_item.user_id, amount=payment_item.fee, payment_item_id=payment_item_id, status="success")
            db.add(new_payment)
    elif status == "NOT RESPONSIBLE":
        payment_item.is_not_responsible = True
        payment_item.is_paid = False
        payment_item.is_past_due = False
        payment_item.fee = 0.0
        existing_payment = db.query(models.Payment).filter(models.Payment.payment_item_id == payment_item_id).first()
        if existing_payment:
            db.delete(existing_payment)
            
    db.commit()
    db.refresh(payment_item)
    return {"message": f"Payment item {payment_item_id} status updated to {status}"}

# Admin Membership Data (Sections)
@router.get("/admin/membership/")
async def admin_membership(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: Optional[str] = None,
    semester: Optional[str] = None,
) -> List[Dict]:
    admin, admin_org = get_current_admin_with_org(request, db)

    users = db.query(models.User).options(
        joinedload(models.User.payment_items)
    ).filter(models.User.organization_id == admin_org.id).all()
    
    membership_data = []
    processed_sections = set()

    for user in users:
        if user.section not in processed_sections:
            section_users = [u for u in users if u.section == user.section]
            section_paid_count = 0
            overall_section_total_amount = 0.0
            overall_section_total_paid = 0.0

            for other_user in section_users:
                user_relevant_payment_items = [
                    pi for pi in other_user.payment_items
                    if (academic_year is None or pi.academic_year == academic_year) and
                       (semester is None or pi.semester == semester)
                ]
                
                is_user_fully_paid_for_period = False
                if user_relevant_payment_items:
                    is_user_fully_paid_for_period = all((pi.is_paid or pi.is_not_responsible) for pi in user_relevant_payment_items)
                
                if is_user_fully_paid_for_period:
                    section_paid_count += 1
                
                for pi in user_relevant_payment_items:
                    if not pi.is_not_responsible:
                        overall_section_total_amount += pi.fee
                        if pi.is_paid:
                            overall_section_total_paid += pi.fee

            status_text = f"{section_paid_count}/{len(section_users)}" if academic_year and semester else str(len(section_users))
            
            membership_data.append({
                'student_number': section_users[0].student_number, 
                'email': section_users[0].email,
                'first_name': section_users[0].first_name,
                'last_name': section_users[0].last_name,
                'year_level': section_users[0].year_level,
                'section': section_users[0].section,
                'status': status_text,
                'total_paid': overall_section_total_paid, 
                'total_amount': overall_section_total_amount,
                'academic_year': academic_year,
                'semester': semester,
                'section_users_count': len(section_users),
                'section_paid_count': section_paid_count
            })
            processed_sections.add(user.section)
    return membership_data

# Admin Individual Members Data
@router.get("/admin/individual_members/")
async def admin_individual_members(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: Optional[str] = None,
    semester: Optional[str] = None,
) -> List[Dict]:
    admin, admin_org = get_current_admin_with_org(request, db)

    query = db.query(models.User).options(
        joinedload(models.User.payment_items).options(joinedload(models.PaymentItem.payments))
    ).filter(models.User.organization_id == admin_org.id)

    filters = []
    if academic_year: filters.append(models.PaymentItem.academic_year == academic_year)
    if semester: filters.append(models.PaymentItem.semester == semester)
    if filters: query = query.join(models.PaymentItem).filter(*filters)

    users = query.all()
    membership_data = []
    for user in users:
        total_paid = 0
        total_amount = 0
        payment_status = "No Dues" if not (academic_year or semester) else "Not Applicable"

        for pi in user.payment_items:
            if (academic_year is None or pi.academic_year == academic_year) and \
               (semester is None or pi.semester == semester):
                total_amount += pi.fee
                for p in pi.payments:
                    if p.status == 'success':
                        total_paid += p.amount

        if total_amount > 0:
            payment_status = "Paid" if total_paid >= total_amount else "Partially Paid"

        membership_data.append({
            'student_number': user.student_number, 'email': user.email, 'first_name': user.first_name,
            'last_name': user.last_name, 'year_level': user.year_level, 'section': user.section,
            'total_paid': total_paid, 'total_amount': total_amount, 'payment_status': payment_status,
            'academic_year': academic_year, 'semester': semester,
        })
    return membership_data

# Financial Trends (Monthly Revenue)
@router.get("/financial_trends")
async def get_financial_trends(request: Request, db: Session = Depends(get_db)):
    admin, admin_org = get_current_admin_with_org(request, db)

    num_months_to_display = 12
    today = date.today()
    all_months_data = OrderedDict()

    for i in range(num_months_to_display - 1, -1, -1):
        target_date = today - relativedelta(months=i)
        all_months_data[(target_date.year, target_date.month)] = 0.0
    
    earliest_year, earliest_month = next(iter(all_months_data.keys()))
    earliest_date_for_filter = datetime(earliest_year, earliest_month, 1)

    financial_data_raw = db.query(
        func.extract('year', models.Payment.created_at).label('year'),
        func.extract('month', models.Payment.created_at).label('month'),
        func.sum(models.Payment.amount).label('total'),
    ).join(models.Payment.user).filter(
        models.Payment.status == "success",
        models.User.organization_id == admin_org.id,
        models.Payment.created_at >= earliest_date_for_filter,
        models.Payment.created_at <= today
    ).group_by('year', 'month').all()

    for row in financial_data_raw:
        key = (int(row.year), int(row.month))
        if key in all_months_data:
            all_months_data[key] = float(row.total)

    labels = [f"{year}-{month:02d}" for year, month in all_months_data.keys()]
    data = list(all_months_data.values())
    return {"labels": labels, "data": data}

# Expenses by Category
@router.get("/expenses_by_category")
async def get_expenses_by_category(request: Request, db: Session = Depends(get_db)):
    admin, admin_org = get_current_admin_with_org(request, db)

    expenses_data = db.query(models.Expense.category, func.sum(models.Expense.amount)).filter(
        models.Expense.organization_id == admin_org.id
    ).group_by(models.Expense.category).all()

    labels = [category if category else "Uncategorized" for category, total in expenses_data]
    data = [float(total) for category, total in expenses_data]
    return {"labels": labels, "data": data}

# Fund Distribution by Academic Year
@router.get("/fund_distribution")
async def get_fund_distribution(request: Request, db: Session = Depends(get_db)):
    admin, admin_org = get_current_admin_with_org(request, db)

    fund_allocation = db.query(models.PaymentItem.academic_year, func.sum(models.Payment.amount)).join(
        models.Payment, models.PaymentItem.id == models.Payment.payment_item_id
    ).join(models.PaymentItem.user).filter(
        models.Payment.status == "success",
        models.User.organization_id == admin_org.id
    ).group_by(models.PaymentItem.academic_year).all()

    distribution_data = {}
    for academic_year, total_amount in fund_allocation:
        category = academic_year if academic_year else "General Funds"
        distribution_data[category] = distribution_data.get(category, 0.0) + float(total_amount)

    return {"labels": list(distribution_data.keys()), "data": list(distribution_data.values())}

# Outstanding Dues
@router.get("/admin/outstanding_dues/")
async def admin_outstanding_dues(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: Optional[str] = None,
) -> List[Dict[str, Any]]:
    admin, admin_org = get_current_admin_with_org(request, db)

    today = date.today() 

    if academic_year:
        resolved_academic_year = academic_year
    else:       
        start_year = today.year - 1 if today.month < 9 else today.year
        resolved_academic_year = f"{start_year}-{start_year + 1}"
    
    current_semester_name = None
    if 9 <= today.month <= 12 or today.month == 1:
        current_semester_name = "1st"
    elif 2 <= today.month <= 6:
        current_semester_name = "2nd"
    elif 7 <= today.month <= 8:
        current_semester_name = "Summer Break"

    total_outstanding_amount = 0.0
    if current_semester_name in ["1st", "2nd"]:
        relevant_payment_items = db.query(models.PaymentItem).join(models.User).filter(
            and_(
                func.lower(models.PaymentItem.academic_year) == resolved_academic_year.lower(),
                models.PaymentItem.semester == current_semester_name,
                models.User.organization_id == admin_org.id,
                models.PaymentItem.is_not_responsible == False
            )
        ).all()
                   
        total_outstanding_amount = sum(
            item.fee for item in relevant_payment_items
            if not item.is_paid
        )
    
    return [{
        "total_outstanding_amount": total_outstanding_amount,
        "semester_status": current_semester_name,
        "academic_year": resolved_academic_year
    }]

# Total Members Page (Admin)
@router.get("/admin/payments/total_members", response_class=HTMLResponse, name="payments_total_members")
async def payments_total_members(
    request: Request,
    db: Session = Depends(get_db),
    section: Optional[str] = None,
    year_level: Optional[str] = None,
    student_number: Optional[str] = None
):
    admin, admin_org = get_current_admin_with_org(request, db)

    query = db.query(models.User).filter(models.User.organization_id == admin_org.id)
    if section: query = query.filter(models.User.section == section)
    if year_level: query = query.filter(models.User.year_level == year_level)
    if student_number: query = query.filter(models.User.student_number == student_number)
    users = query.all()

    context = await get_base_template_context(request, db)
    context.update({
        "members": users,
        "section": section,
        "year_level": year_level,
        "student_number": student_number,
    })
    return templates.TemplateResponse("admin_dashboard/payments/total_members.html", context)

# Admin Bulletin Board Page
@router.get('/admin/bulletin_board', response_class=HTMLResponse)
async def admin_bulletin_board(request: Request, db: Session = Depends(get_db)):
    admin, admin_org = get_current_admin_with_org(request, db)
    posts = db.query(models.BulletinBoard).join(models.Admin).join(models.Admin.organizations).filter(
        models.Organization.id == admin_org.id
    ).order_by(models.BulletinBoard.created_at.desc()).all()
    
    context = await get_base_template_context(request, db)
    context.update({"posts": posts})
    return templates.TemplateResponse("admin_dashboard/admin_bulletin_board.html", context)

# Admin Events Page
@router.get('/admin/events', response_class=HTMLResponse)
async def admin_events(request: Request, db: Session = Depends(get_db)):
    admin, admin_org = get_current_admin_with_org(request, db)
    events = db.query(models.Event).options(joinedload(models.Event.participants)).join(models.Admin).join(models.Admin.organizations).filter(
        models.Organization.id == admin_org.id
    ).order_by(models.Event.created_at.desc()).all()
    
    context = await get_base_template_context(request, db)
    context.update({"events": events})
    return templates.TemplateResponse("admin_dashboard/admin_events.html", context)

# Admin Financial Statement Page
@router.get("/admin/financial_statement", response_class=HTMLResponse, name="admin_financial_statement")
async def admin_financial_statement_page(request: Request, db: Session = Depends(get_db)):
    admin, _ = get_current_admin_with_org(request, db) 
    context = await get_base_template_context(request, db)
    return templates.TemplateResponse("admin_dashboard/admin_financial_statement.html", context)

# Get Expenses
@router.get("/expenses/", response_model=List[schemas.Expense], status_code=status.HTTP_200_OK)
async def get_expenses(request: Request, db: Session = Depends(get_db)):
    admin, organization = get_current_admin_with_org(request, db)
    expenses = db.query(models.Expense).filter(models.Expense.organization_id == organization.id).order_by(models.Expense.incurred_at.desc()).all()
    for expense in expenses:
        if expense.admin and expense.admin.position is None:
            expense.admin.position = ""
    return expenses

# Create Expense
@router.post("/expenses/", response_model=schemas.Expense, status_code=status.HTTP_201_CREATED)
async def create_expense(request: Request, expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    admin, organization = get_current_admin_with_org(request, db)
    
    total_revenue = db.query(func.sum(models.PaymentItem.fee)).join(models.User).filter(
        models.User.organization_id == organization.id, models.PaymentItem.is_paid.is_(True)
    ).scalar() or 0.0
    total_expenses = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.organization_id == organization.id
    ).scalar() or 0.0

    if (total_expenses + expense.amount) > total_revenue:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expense amount ({expense.amount:.2f}) exceeds available revenue. "
                   f"Remaining budget: {(total_revenue - total_expenses):.2f}"
        )

    db_expense = models.Expense(
        description=expense.description, amount=expense.amount, category=expense.category,
        incurred_at=expense.incurred_at if expense.incurred_at else date.today(),
        admin_id=admin.admin_id, organization_id=organization.id
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense, attribute_names=["admin"])     
    if db_expense.admin and db_expense.admin.position is None:
        db_expense.admin.position = ""
    return db_expense

# Admin Financial Data API
@router.get("/api/admin/financial_data", response_class=JSONResponse, name="admin_financial_data_api")
async def admin_financial_data_api(request: Request, db: Session = Depends(get_db)):
    admin, organization = get_current_admin_with_org(request, db)
    
    current_year = datetime.now().year
    today = datetime.now().date()

    total_revenue_ytd = db.query(func.sum(models.PaymentItem.fee)).join(models.User).filter(
        extract('year', models.PaymentItem.updated_at) == current_year,
        models.PaymentItem.is_paid == True,
        models.User.organization_id == organization.id
    ).scalar() or 0.0
    total_expenses_ytd = db.query(func.sum(models.Expense.amount)).filter(
        extract('year', models.Expense.incurred_at) == current_year,
        models.Expense.organization_id == organization.id
    ).scalar() or 0.0

    net_income_ytd = total_revenue_ytd - total_expenses_ytd
    profit_margin_ytd = round((net_income_ytd / total_revenue_ytd) * 100, 2) if total_revenue_ytd != 0 else 0.0

    top_revenue_source_query = db.query(models.PaymentItem.academic_year, models.PaymentItem.semester, func.sum(models.PaymentItem.fee).label('total_fee')).join(models.User).filter(
        extract('year', models.PaymentItem.updated_at) == current_year, models.PaymentItem.is_paid == True, models.User.organization_id == organization.id
    ).group_by(models.PaymentItem.academic_year, models.PaymentItem.semester).order_by(func.sum(models.PaymentItem.fee).desc()).first()
    top_revenue_source = {"name": "N/A", "amount": 0.0}
    if top_revenue_source_query:
        source_name = f"AY {top_revenue_source_query.academic_year} - {top_revenue_source_query.semester} Fees" if top_revenue_source_query.academic_year and top_revenue_source_query.semester else "Miscellaneous Fees"
        top_revenue_source = {"name": source_name, "amount": round(float(top_revenue_source_query.total_fee), 2)}

    largest_expense_query = db.query(models.Expense.category, func.sum(models.Expense.amount).label('total_amount')).filter(
        extract('year', models.Expense.incurred_at) == current_year, models.Expense.organization_id == organization.id
    ).group_by(models.Expense.category).order_by(func.sum(models.Expense.amount).desc()).first()
    largest_expense_category = "N/A"
    largest_expense_amount = 0.0
    if largest_expense_query:
        largest_expense_category = largest_expense_query.category if largest_expense_query.category else "Uncategorized"
        largest_expense_amount = round(float(largest_expense_query.total_amount), 2)

    revenues_breakdown_query = db.query(models.PaymentItem.academic_year, models.PaymentItem.semester, func.sum(models.PaymentItem.fee).label('total_fee')).join(models.User).filter(
        extract('year', models.PaymentItem.updated_at) == current_year, models.PaymentItem.is_paid == True, models.User.organization_id == organization.id
    ).group_by(models.PaymentItem.academic_year, models.PaymentItem.semester).all()
    revenues_breakdown = []
    for item in revenues_breakdown_query:
        source_name = f"AY {item.academic_year} - {item.semester} Fees" if item.academic_year and item.semester else "Miscellaneous Fees"
        percentage = round((float(item.total_fee) / total_revenue_ytd) * 100, 2) if total_revenue_ytd != 0 else 0.0
        revenues_breakdown.append({"source": source_name, "amount": round(float(item.total_fee), 2), "trend": "Stable", "percentage": percentage})
    if not revenues_breakdown and total_revenue_ytd > 0:
        revenues_breakdown.append({"source": "General Collected Fees", "amount": total_revenue_ytd, "trend": "Stable", "percentage": 100.0})

    expenses_breakdown_query = db.query(models.Expense.category, func.sum(models.Expense.amount).label('total_amount')).filter(
        extract('year', models.Expense.incurred_at) == current_year, models.Expense.organization_id == organization.id
    ).group_by(models.Expense.category).all()
    expenses_breakdown = []
    for item in expenses_breakdown_query:
        percentage = round((float(item.total_amount) / total_expenses_ytd) * 100, 2) if total_expenses_ytd != 0 else 0.0
        expenses_breakdown.append({"category": item.category if item.category else "Uncategorized", "amount": round(float(item.total_amount), 2), "trend": "Stable", "percentage": percentage})
    if expenses_breakdown and sum(item['percentage'] for item in expenses_breakdown) != 100 and sum(item['percentage'] for item in expenses_breakdown) != 0:
        adjustment_factor = 100 / sum(item['percentage'] for item in expenses_breakdown)
        for item in expenses_breakdown: item['percentage'] = round(item['percentage'] * adjustment_factor, 2)

    monthly_summary = []
    chart_net_income_trend_data = []
    chart_net_income_trend_labels = []
    for i in range(1, 13):
        dummy_date = date(current_year, i, 1)
        month_name_full = dummy_date.strftime('%B')
        month_name_abbr = dummy_date.strftime('%b')
        chart_net_income_trend_labels.append(month_name_abbr)

        monthly_revenue = db.query(func.sum(models.PaymentItem.fee)).join(models.User).filter(
            extract('year', models.PaymentItem.updated_at) == current_year, extract('month', models.PaymentItem.updated_at) == i,
            models.PaymentItem.is_paid == True, models.User.organization_id == organization.id
        ).scalar() or 0.0
        monthly_expenses = db.query(func.sum(models.Expense.amount)).filter(
            extract('year', models.Expense.incurred_at) == current_year, extract('month', models.Expense.incurred_at) == i,
            models.Expense.organization_id == organization.id
        ).scalar() or 0.0

        monthly_net_income = monthly_revenue - monthly_expenses
        monthly_summary.append({
            "month": month_name_full, "revenue": monthly_revenue, "expenses": monthly_expenses,
            "net_income": monthly_net_income, "net_income_class": "positive" if monthly_net_income >= 0 else "negative"
        })
        chart_net_income_trend_data.append(round(monthly_net_income, 2))

    num_paid_members = db.query(func.count(models.User.id.distinct())).join(models.PaymentItem).filter(
        extract('year', models.PaymentItem.updated_at) == current_year, models.PaymentItem.is_paid == True, models.User.organization_id == organization.id
    ).scalar() or 0
    total_members = db.query(func.count(models.User.id)).filter(models.User.is_active == True, models.User.organization_id == organization.id).scalar() or 0
    num_unpaid_members = max(0, total_members - num_paid_members)

    financial_data = {
        "organization_id": organization.id, "organization_name": organization.name, "year": str(current_year),
        "total_current_balance": net_income_ytd, "total_revenue_ytd": total_revenue_ytd, "total_expenses_ytd": total_expenses_ytd,
        "net_income_ytd": net_income_ytd, "balance_turnover": round(total_revenue_ytd / net_income_ytd, 2) if net_income_ytd != 0 else 0.0,
        "total_funds_available": net_income_ytd, "reporting_date": today.strftime("%B %d, %Y"),
        "top_revenue_source_name": top_revenue_source["name"], "top_revenue_source_amount": top_revenue_source['amount'],
        "largest_expense_category": largest_expense_category, "largest_expense_amount": largest_expense_amount,
        "profit_margin_ytd": profit_margin_ytd, "revenues_breakdown": revenues_breakdown,
        "expenses_breakdown": expenses_breakdown, "monthly_summary": monthly_summary,
        "accounts_balances": [], 
        "chart_revenue_data": [total_revenue_ytd, total_expenses_ytd],
        "chart_net_income_data": chart_net_income_trend_data, "chart_net_income_labels": chart_net_income_trend_labels,
        "num_paid_members": num_paid_members, "num_unpaid_members": num_unpaid_members, "total_members": total_members
    }
    if net_income_ytd >= 0:
        financial_data["accounts_balances"] = [
            {"account": "Main Operating Account", "balance": round(net_income_ytd * 0.7, 2), "last_transaction": today.strftime("%Y-%m-%d"), "status": "Active"},
            {"account": "Savings Account", "balance": round(net_income_ytd * 0.2, 2), "last_transaction": (today - timedelta(days=15)).strftime("%Y-%m-%d"), "status": "Active"},
            {"account": "Petty Cash", "balance": round(net_income_ytd * 0.1, 2), "last_transaction": (today - timedelta(days=3)).strftime("%Y-%m-%d"), "status": "Active"}
        ]
        
        current_sum = sum(acc['balance'] for acc in financial_data["accounts_balances"])
        if abs(current_sum - net_income_ytd) > 0.01:
            financial_data["accounts_balances"][-1]['balance'] += (net_income_ytd - current_sum)
            financial_data["accounts_balances"][-1]['balance'] = round(financial_data["accounts_balances"][-1]['balance'], 2)
    else:
        financial_data["accounts_balances"] = [{"account": "Main Operating Account", "balance": net_income_ytd, "last_transaction": today.strftime("%Y-%m-%d"), "status": "Critical"}]

    return JSONResponse(content=financial_data)

# Create Organization
@router.post("/admin/organizations/", response_model=schemas.Organization, status_code=status.HTTP_201_CREATED)
async def create_organization_route(
    request: Request,
    organization: schemas.OrganizationCreate,
    db: Session = Depends(get_db)
):
    if db.query(models.Organization).filter(models.Organization.name == organization.name).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Organization with name '{organization.name}' already exists.")
    if db.query(models.Organization).filter(models.Organization.primary_course_code == organization.primary_course_code).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Organization with primary course code '{organization.primary_course_code}' already exists.")

    custom_palette = crud.generate_custom_palette(organization.theme_color)
    suggested_filename = f"{organization.name.lower().replace(' ', '_')}_logo.png"
    logo_upload_path = f"/static/images/{suggested_filename}"

    new_org = models.Organization(
        name=organization.name, theme_color=organization.theme_color,
        primary_course_code=organization.primary_course_code,
        custom_palette=custom_palette, logo_url=logo_upload_path
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    logging.info(f"Action Required: Please upload the organization logo to your web server at the path: {new_org.logo_url}. Suggested filename: {suggested_filename}")
    return new_org
    
# Create Admin User
@router.post("/admin/admins/", response_model=schemas.Admin, status_code=status.HTTP_201_CREATED)
async def create_admin_user_route(
    request: Request,
    admin_data: schemas.AdminCreate,
    db: Session = Depends(get_db)
):
    if db.query(models.Admin).filter(models.Admin.email == admin_data.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Admin with email '{admin_data.email}' already exists.")
    
    hashed_password = bcrypt.hashpw(admin_data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    new_admin = models.Admin(name=admin_data.name, email=admin_data.email, password=hashed_password, role="Admin", position=admin_data.position)
    db.add(new_admin)
    db.flush()

    if admin_data.organization_id:
        organization = db.get(models.Organization, admin_data.organization_id)
        if organization: new_admin.organizations.append(organization)
        else: logging.warning(f"Organization with ID {admin_data.organization_id} not found. Admin created without organization link.")
    
    db.commit()
    db.refresh(new_admin)
    return new_admin

# Update Organization Theme Color
@router.put("/admin/organizations/{org_id}/theme", response_model=Dict[str, str])
async def update_organization_theme_color_route(
    request: Request,
    org_id: int,
    theme_update: schemas.OrganizationThemeUpdate,
    db: Session = Depends(get_db)
):
    admin, _ = get_current_admin_with_org(request, db) 
    organization = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organization with ID {org_id} not found.")
    
    organization.theme_color = theme_update.new_theme_color
    organization.custom_palette = crud.generate_custom_palette(theme_update.new_theme_color)
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return {"message": f"Organization '{organization.name}' (ID: {org_id}) theme color updated to {theme_update.new_theme_color} and palette regenerated successfully."}

# Update Organization Logo
@router.put("/admin/organizations/{org_id}/logo", response_model=Dict[str, str])
async def update_organization_logo_route(
    request: Request,
    org_id: int,
    logo_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    admin, _ = get_current_admin_with_org(request, db) 
    organization = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organization with ID {org_id} not found.")

    file_extension = Path(logo_file.filename).suffix.lower()
    allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg']
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid file type. Only {', '.join(allowed_extensions)} are allowed.")

    organization_name_slug = ''.join(e for e in organization.name.lower().replace(' ', '_') if e.isalnum() or e == '_')
    suggested_filename = f"{organization_name_slug}_logo{file_extension}"
    
    
    if organization.logo_url and organization.logo_url != request.url_for('static', path='images/patrick_logo.jpg'):
        delete_file_from_path(organization.logo_url)

    file_path = UPLOAD_BASE_DIRECTORY / suggested_filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(logo_file.file, buffer)
        logo_url = f"/static/images/{suggested_filename}"
        organization.logo_url = logo_url
        db.add(organization)
        db.commit()
        db.refresh(organization)
        return {"message": f"Organization '{organization.name}' (ID: {org_id}) logo updated successfully to {logo_url}."}
    except Exception as e:
        db.rollback()
        if file_path.exists(): os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating organization logo: {e}")

# Create PayMaya Payment Request
@router.post("/payments/paymaya/create", response_class=JSONResponse, name="paymaya_create_payment")
async def paymaya_create_payment(
    request: Request,
    payment_item_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user, _ = get_current_user_with_org(request, db) 

    public_api_key = "pk-Z0OSzLvIcOI2UIvDhdTGVVfRSSeiGStnceqwUE7n0Ah"
    encoded_key = base64.b64encode(f"{public_api_key}:".encode()).decode()
    url = "https://pg-sandbox.paymaya.com/checkout/v1/checkouts"
    headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Basic {encoded_key}"}

    payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if not payment_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment item not found")

    db_payment = crud.create_payment(db, amount=payment_item.fee, user_id=user.id, payment_item_id=payment_item_id)

    payload = {
        "totalAmount": {"currency": "PHP", "value": payment_item.fee},
        "requestReferenceNumber": f"your-unique-ref-{datetime.now().strftime('%Y%m%d%H%M%S')}-{db_payment.id}",
        "redirectUrl": {
            "success": f"http://127.0.0.1:8000/Success?paymentId={db_payment.id}&paymentItemId={payment_item_id}",
            "failure": f"http://127.0.0.1:8000/Failure?paymentId={db_payment.id}&paymentItemId={payment_item_id}",
            "cancel": f"http://127.0.0.1:8000/Cancel?paymentId={db_payment.id}&paymentItemId={payment_item_id}"
        },
        "metadata": {
            "pf": {"smi": "CVSU", "smn": "Undisputed", "mci": "Imus City", "mpc": "608", "mco": "PHL", "postalCode": "1554", "contactNo": "0211111111", "addressLine1": "Palico"},
            "subMerchantRequestReferenceNumber": "63d9934f9281"
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        payment_data = response.json()
        crud.update_payment(db, payment_id=db_payment.id, paymaya_payment_id=payment_data.get("checkoutId"))
        db.commit() 
        db.refresh(db_payment) 
        return payment_data
    except requests.exceptions.RequestException as e:
        db.rollback() 
        crud.update_payment(db, payment_id=db_payment.id, status="failed")
        db.commit() 
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"PayMaya API error: {e.response.text if hasattr(e.response, 'text') else str(e)}")

# Payment Success Callback
@router.get("/Success", response_class=HTMLResponse, name="payment_success")
async def payment_success(
    request: Request, paymentId: int = Query(...), paymentItemId: int = Query(...), db: Session = Depends(get_db),
):
    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if not payment: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

    crud.update_payment(db, payment_id=payment.id, status="success", payment_item_id=paymentItemId)
    payment_item = crud.mark_payment_item_as_paid(db, payment_item_id=paymentItemId)

    user = db.query(models.User).filter(models.User.id == payment.user_id).first()
    if user and user.organization:
        for admin in user.organization.admins:
            message = f"Payment Successful: {user.first_name} {user.last_name} has successfully paid {payment.amount} for {payment_item.academic_year} {payment_item.semester} fees."
            crud.create_notification(db, message, admin_id=admin.admin_id, organization_id=user.organization.id, notification_type="payment_success", entity_id=payment.id, url=f"/admin/payments/total_members?student_number={user.student_number}")
    
    db.commit() 
    context = await get_base_template_context(request, db)
    context.update({"payment_id": payment.paymaya_payment_id, "payment_item_id": paymentItemId, "payment": payment, "payment_item": payment_item})
    return templates.TemplateResponse("student_dashboard/payment_success.html", context)

# Payment Failure Callback
@router.get("/Failure", response_class=HTMLResponse, name="payment_failure")
async def payment_failure(request: Request, paymentId: int = Query(...), db: Session = Depends(get_db)):
    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if not payment: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")
    
    crud.update_payment(db, payment_id=payment.id, status="failed")
    payment_item = crud.get_payment_item_by_id(db, payment.payment_item_id)

    db.commit() 
    context = await get_base_template_context(request, db)
    context.update({"payment_id": payment.paymaya_payment_id, "payment_item": payment_item})
    return templates.TemplateResponse("student_dashboard/payment_failure.html", context)

# Payment Cancellation Callback
@router.get("/Cancel", response_class=HTMLResponse, name="payment_cancel")
async def payment_cancel(request: Request, paymentId: int = Query(...), db: Session = Depends(get_db)):
    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if not payment: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")
    
    crud.update_payment(db, payment_id=payment.id, status="cancelled")
    payment_item = crud.get_payment_item_by_id(db, payment.payment_item_id)

    db.commit() 
    context = await get_base_template_context(request, db)
    context.update({"payment_id": payment.paymaya_payment_id, "payment_item": payment_item})
    return templates.TemplateResponse("student_dashboard/payment_cancel.html", context)

app.include_router(router)

# User Logout
@app.get("/logout", response_class=RedirectResponse, name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# Root Index Page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Home Dashboard (Admin/User)
@app.get("/home", response_class=HTMLResponse, name="home")
async def home(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")
    user_role = request.session.get("user_role")

    if not (user_id or admin_id) or not user_role:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Please log in to access this page."})

    context = await get_base_template_context(request, db)
    latest_bulletin_posts = []

    if context["organization_id"]:
        latest_bulletin_posts = db.query(models.BulletinBoard).join(models.Admin).join(models.Admin.organizations).filter(
            models.Organization.id == context["organization_id"]
        ).order_by(models.BulletinBoard.created_at.desc()).limit(5).all()

    if user_role == "Admin":
        admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
        if admin and context["organization_id"]:
            past_due_users = db.query(models.User).join(models.PaymentItem).filter(
                models.User.organization_id == context["organization_id"],
                models.PaymentItem.is_past_due == True,
                models.PaymentItem.is_paid == False
            ).distinct(models.User.id).all()
            for past_due_user in past_due_users:
                crud.create_notification(db, f"Past Due Payments: {past_due_user.first_name} {past_due_user.last_name} has past due payment items.",
                                         admin_id=admin.admin_id, organization_id=context["organization_id"],
                                         notification_type="past_due_payments", entity_id=past_due_user.id,
                                         url=f"/admin/payments/total_members?student_number={past_due_user.student_number}")
        db.commit() 
        context.update({"bulletin_posts": latest_bulletin_posts})
        return templates.TemplateResponse("admin_dashboard/home.html", context)
    
    elif user_role == "user":
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and context["organization_id"]:
            user_past_due_items = db.query(models.PaymentItem).filter(
                models.PaymentItem.user_id == user_id, models.PaymentItem.is_past_due == True, models.PaymentItem.is_paid == False
            ).all()
            if user_past_due_items:
                crud.create_notification(db, "You have past due payment items. Please check your payments page.",
                                         user_id=user_id, organization_id=context["organization_id"],
                                         notification_type="user_past_due", url="/Payments")
        db.commit() 
        temporary_faqs = [
            {"question": "What is the schedule for student orientation?", "answer": "The student orientation will be held on August 20, 2025, from 9:00 AM to 12:00 PM in the main auditorium."},
            {"question": "How do I access the online learning platform?", "answer": "You can access the online learning platform by visiting our website and clicking on the 'Student Portal' link. Use your student ID and password to log in."},
            {"question": "Who should I contact for academic advising?", "answer": "For academic advising, please contact the Dean's office of your respective faculty. You can find their contact information on the university website under the 'Academics' section."},
        ]
        context.update({"bulletin_posts": latest_bulletin_posts, "faqs": temporary_faqs})
        return templates.TemplateResponse("student_dashboard/home.html", context)
    else:
        raise HTTPException(status_code=403, detail="Invalid user role")

# Bulletin Board Page (User)
@app.get("/BulletinBoard", response_class=HTMLResponse, name="bulletin_board")
async def bulletin_board(request: Request, db: Session = Depends(get_db)):
    user, user_org = get_current_user_with_org(request, db)
    posts = []
    if user_org:
        posts = db.query(models.BulletinBoard).join(models.Admin).join(models.Admin.organizations).filter(
            models.Organization.id == user_org.id
        ).order_by(models.BulletinBoard.created_at.desc()).all()
    
    context = await get_base_template_context(request, db)
    context.update({"posts": posts, "hearted_posts": []})  
    return templates.TemplateResponse("student_dashboard/bulletin_board.html", context)

# Events Page (User)
@app.get("/Events", response_class=HTMLResponse, name="events")
async def events(request: Request, db: Session = Depends(get_db)):
    user, user_org = get_current_user_with_org(request, db)
    events = []
    if user_org:
        events = db.query(models.Event).options(joinedload(models.Event.participants)).join(models.Admin).join(models.Admin.organizations).filter(
            models.Organization.id == user_org.id
        ).order_by(models.Event.created_at.desc()).all()
    
    context = await get_base_template_context(request, db)
    context.update({"events": events})
    return templates.TemplateResponse("student_dashboard/events.html", context)

# Payments Page (User)
@app.get("/Payments", response_class=HTMLResponse, name="payments")
async def payments(request: Request, db: Session = Depends(get_db)):
    user, _ = get_current_user_with_org(request, db)

    payment_items = db.query(models.PaymentItem).filter(
        models.PaymentItem.user_id == user.id, models.PaymentItem.is_not_responsible == False
    ).order_by(models.PaymentItem.academic_year).all()

    past_due_items = [item for item in payment_items if not item.is_paid and item.is_past_due]
    unpaid_upcoming_items = [item for item in payment_items if not item.is_paid and not item.is_past_due]

    context = await get_base_template_context(request, db)
    context.update({
        "past_due_items": past_due_items,
        "unpaid_upcoming_items": unpaid_upcoming_items,
        "current_user": user,
    })
    return templates.TemplateResponse("student_dashboard/payments.html", context)

# Payment History (User)
@app.get("/Payments/History", response_class=HTMLResponse, name="payment_history")
async def payment_history(request: Request, db: Session = Depends(get_db)):
    user, _ = get_current_user_with_org(request, db)

    payments = db.query(models.Payment).options(joinedload(models.Payment.payment_item)).filter(
        models.Payment.user_id == user.id
    ).order_by(models.Payment.created_at.desc(), models.Payment.id.desc()).all()

    payment_history_data = []
    for payment in payments:
        payment_item = payment.payment_item
        if not all([payment_item, payment_item.academic_year, payment_item.semester, payment_item.fee, payment.amount, payment.status, payment_item.due_date, payment.created_at]):
            continue
        status_text = payment.status
        if status_text == "pending": status_text = "Pending"
        elif status_text == "success": status_text = "Paid"
        elif status_text == "failed": status_text = "Failed"
        elif status_text == "cancelled": status_text = "Cancelled"
        payment_history_data.append({"item": payment, "status": status_text})

    context = await get_base_template_context(request, db)
    context.update({"payment_history": payment_history_data, "current_user": user})
    return templates.TemplateResponse("student_dashboard/payment_history.html", context)

# Financial Statement (User)
@app.get("/FinancialStatement", response_class=HTMLResponse, name="financial_statement")
async def financial_statement(request: Request, db: Session = Depends(get_db)):
    user, user_org = get_current_user_with_org(request, db)

    all_user_payment_items = db.query(models.PaymentItem).filter(models.PaymentItem.user_id == user.id).all()
    
    total_paid_by_user = sum(item.fee for item in all_user_payment_items if item.is_paid)
    total_outstanding_fees_user = sum(item.fee for item in all_user_payment_items if not item.is_paid)
    total_past_due_fees_user = sum(item.fee for item in all_user_payment_items if not item.is_paid and item.due_date and item.due_date < date.today())

    collected_fees_by_category_user = defaultdict(float)
    outstanding_fees_by_category_user = defaultdict(float)
    for item in all_user_payment_items:
        category_name = f"AY {item.academic_year} - {item.semester} Fees" if item.academic_year and item.semester else "Miscellaneous Fees"
        if item.is_paid: collected_fees_by_category_user[category_name] += item.fee
        else: outstanding_fees_by_category_user[category_name] += item.fee

    organization_total_revenue = 0.0
    all_org_paid_payment_items = db.query(models.PaymentItem).join(models.User).filter(
        models.PaymentItem.is_paid == True,
        models.User.organization_id == (user_org.id if user_org else None)
    ).all()
    organization_total_revenue = sum(item.fee for item in all_org_paid_payment_items)

    all_expenses_org = db.query(models.Expense).filter(models.Expense.organization_id == (user_org.id if user_org else None)).all()
    total_expenses_org = sum(expense.amount for expense in all_expenses_org)
    net_income_org = organization_total_revenue - total_expenses_org

    expenses_by_category_org = defaultdict(float)
    for expense in all_expenses_org:
        expenses_by_category_org[expense.category if expense.category else "Uncategorized"] += expense.amount

    financial_summary_items_combined = []
    for item in all_user_payment_items:
        if item.is_paid and (item.updated_at or item.created_at):
            relevant_date = item.updated_at or item.created_at
            category_name_summary = f"AY {item.academic_year} - {item.semester} Fees (Your Payment)" if item.academic_year and item.semester else "Miscellaneous Fees (Your Payment)"
            financial_summary_items_combined.append({"date": relevant_date, "event_item": category_name_summary, "inflows": item.fee, "outflows": 0.00})
    for expense in all_expenses_org:
        if expense.incurred_at:
            financial_summary_items_combined.append({"date": expense.incurred_at, "event_item": f"Org Expense - {expense.category if expense.category else 'Uncategorized'}", "inflows": 0.00, "outflows": expense.amount})
    financial_summary_items_combined.sort(key=lambda x: x['date'])
    for item in financial_summary_items_combined:
        item['date'] = item['date'].strftime("%Y-%m-%d")

    months_full = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    org_inflows_by_month_current_year = defaultdict(float)
    for item in all_org_paid_payment_items:
        relevant_date = item.updated_at or item.created_at
        if relevant_date and relevant_date.year == datetime.now().year:
            org_inflows_by_month_current_year[months_full[relevant_date.month - 1].lower()] += item.fee

    expenses_by_month_current_year_org = defaultdict(float)
    for expense in all_expenses_org:
        if expense.incurred_at and expense.incurred_at.year == datetime.now().year:
            expenses_by_month_current_year_org[months_full[expense.incurred_at.month - 1].lower()] += expense.amount

    running_balance_org_level = 0.00
    monthly_data_org = {}
    for i, month_name in enumerate(months_full):
        month_name_lower = month_name.lower()
        inflows_this_month_org = org_inflows_by_month_current_year.get(month_name_lower, 0.00)
        outflows_this_month_org = expenses_by_month_current_year_org.get(month_name_lower, 0.00)
        
        starting_balance = running_balance_org_level
        ending_balance = starting_balance + inflows_this_month_org - outflows_this_month_org
        running_balance_org_level = ending_balance
        
        monthly_data_org[month_name_lower] = {"starting_balance": starting_balance, "inflows": inflows_this_month_org, "outflows": outflows_this_month_org, "ending_balance": ending_balance}

    financial_data = {
        "user_financials": {
            "total_paid_by_user": total_paid_by_user, "total_outstanding_fees": total_outstanding_fees_user,
            "total_past_due_fees": total_past_due_fees_user,
            "collected_fees_by_category": [{"category": k, "amount": v} for k, v in collected_fees_by_category_user.items()],
            "outstanding_fees_by_category": [{"category": k, "amount": v} for k, v in outstanding_fees_by_category_user.items()],
        },
        "organization_financials": {
            "total_revenue_org": organization_total_revenue, "total_expenses_org": total_expenses_org,
            "net_income_org": net_income_org,
            "expenses_by_category_org": [{"category": k, "amount": v} for k, v in expenses_by_category_org.items()],
            "monthly_data_org": monthly_data_org,
        },
        "financial_summary_items_combined": financial_summary_items_combined,
        "current_date": date.today().strftime("%B %d, %Y")
    }
    context = await get_base_template_context(request, db)
    context.update({"financial_data": financial_data})
    return templates.TemplateResponse("student_dashboard/financial_statement.html", context)

# Detailed Monthly Report Page (User)
@router.get("/student_dashboard/detailed_monthly_report_page", response_class=HTMLResponse)
async def detailed_monthly_report_page(
    request: Request, month: str = Query(...), year: int = Query(...), db: Session = Depends(get_db)
):
    user, _ = get_current_user_with_org(request, db) 
    context = await get_base_template_context(request, db)
    context.update({"month": month, "year": year})
    return templates.TemplateResponse("student_dashboard/detailed_monthly_report.html", context)

# Detailed Monthly Report Data (User)
@router.get("/api/detailed_monthly_report", response_class=JSONResponse)
async def get_detailed_monthly_report_json(
    request: Request,
    month: str = Query(..., description="Month name (e.g., 'january')"),
    year: int = Query(..., description="Year (e.g., 2025)"),
    report_type: Optional[str] = Query(None, description="Type of report: 'user' or 'organization' or 'combined'"),
    db: Session = Depends(get_db)
):
    user, user_org = get_current_user_with_org(request, db)

    month_number = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }.get(month.lower())
    if month_number is None: raise HTTPException(status_code=400, detail="Invalid month specified.")

    start_date_of_month = date(year, month_number, 1)
    end_date_of_month = date(year, month_number, calendar.monthrange(year, month_number)[1])

    all_financial_events = []
    if report_type in ['user', 'combined', None]:
        for item in db.query(models.PaymentItem).filter(models.PaymentItem.user_id == user.id).all():
            relevant_date = (item.updated_at or item.created_at).date()
            if start_date_of_month <= relevant_date <= end_date_of_month:
                category_name = f"AY {item.academic_year} - {item.semester} Fee" if item.academic_year and item.semester else "Miscellaneous Fee"
                status_str = "Paid" if item.is_paid else ("Past Due" if not item.is_paid and item.due_date and item.due_date < date.today() else "Unpaid")
                all_financial_events.append((relevant_date, f"Your Payment - {category_name}", item.fee if item.is_paid else 0.00, 0.00, status_str, item.fee, item))

    org_id_for_query = user_org.id if user_org else None
    if report_type in ['organization', 'combined', None]:
        org_inflows_query = db.query(models.PaymentItem).join(models.User).filter(models.PaymentItem.is_paid == True, models.User.organization_id == org_id_for_query)
        if report_type in ['user', 'combined', None]: org_inflows_query = org_inflows_query.filter(models.PaymentItem.user_id != user.id)
        
        org_inflows_for_month = org_inflows_query.filter(
            (func.date(models.PaymentItem.updated_at) >= start_date_of_month) | (func.date(models.PaymentItem.created_at) >= start_date_of_month),
            (func.date(models.PaymentItem.updated_at) <= end_date_of_month) | (func.date(models.PaymentItem.created_at) <= end_date_of_month)
        ).all()
        total_org_inflow_amount = sum(item.fee for item in org_inflows_for_month)
        if total_org_inflow_amount > 0:
            all_financial_events.append((start_date_of_month, "Organization Inflows", total_org_inflow_amount, 0.00, "Received", total_org_inflow_amount, None))

        for expense in db.query(models.Expense).filter(models.Expense.organization_id == org_id_for_query).all():
            if expense.incurred_at and start_date_of_month <= expense.incurred_at <= end_date_of_month:
                all_financial_events.append((expense.incurred_at, f"Org Expense - {expense.category or 'Uncategorized'}", 0.00, expense.amount, "Recorded", expense.amount, expense))

    all_financial_events.sort(key=lambda x: x[0])

    transactions_for_report_month = []
    total_inflows_month = 0.00
    total_outflows_month = 0.00
    total_outstanding_month = 0.00
    total_past_due_month = 0.00
    current_running_balance = 0.00
    starting_balance_month = 0.00

    for event_date, description, inflow, outflow, status_str, original_value, original_item_obj in all_financial_events:
        if event_date < start_date_of_month: current_running_balance += inflow - outflow
        else:
            starting_balance_month = current_running_balance
            break

    for event_date, description, inflow, outflow, status_str, original_value, original_item_obj in all_financial_events:
        if start_date_of_month <= event_date <= end_date_of_month:
            is_user_payment_event = "Your Payment" in description
            is_org_inflow_event = "Organization Inflows" in description
            is_org_expense_event = "Org Expense" in description

            should_include_in_report = False
            if report_type is None or report_type == 'combined': should_include_in_report = True
            elif report_type == 'user' and is_user_payment_event: should_include_in_report = True
            elif report_type == 'organization' and (is_org_inflow_event or is_org_expense_event): should_include_in_report = True

            if should_include_in_report:
                total_inflows_month += inflow
                total_outflows_month += outflow
                if is_user_payment_event and status_str != "Paid" and isinstance(original_item_obj, models.PaymentItem) and not original_item_obj.is_paid:
                    total_outstanding_month += original_item_obj.fee
                    if original_item_obj.due_date and original_item_obj.due_date < date.today(): total_past_due_month += original_item_obj.fee

                current_running_balance += (inflow - outflow)
                transactions_for_report_month.append({
                    "date": event_date.strftime("%Y-%m-%d"), "description": description, "inflow": inflow, "outflow": outflow,
                    "status": status_str, "original_value": original_value, "running_balance": current_running_balance
                })

    response_content = {
        "month_name": month.capitalize(), "year": year, "current_date": date.today().strftime("%B %d, %Y"),
        "starting_balance": starting_balance_month, "total_inflows": total_inflows_month, "total_outflows": total_outflows_month,
        "total_outstanding": total_outstanding_month, "total_past_due": total_past_due_month,
        "ending_balance": starting_balance_month + total_inflows_month - total_outflows_month,
        "transactions": transactions_for_report_month, "user_name": f"{user.first_name} {user.last_name}",
        "total_all_original_fees": sum(item.fee for item in db.query(models.PaymentItem).filter(models.PaymentItem.user_id == user.id).all()) if report_type in ['user', 'combined', None] else 0.00
    }
    return JSONResponse(content=response_content)

# Settings Page (User)
@app.get("/Settings", response_class=HTMLResponse, name="settings")
async def settings(request: Request, db: Session = Depends(get_db)):
    user, _ = get_current_user_with_org(request, db)

    formatted_birthdate = ""
    if user.birthdate:
        try:
            birthdate_object = datetime.strptime(user.birthdate, "%Y-%m-%d %H:%M:%S")
            formatted_birthdate = birthdate_object.strftime("%Y-%m-%d")
        except ValueError:
            try:
                formatted_birthdate = datetime.strptime(user.birthdate, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                try:
                    formatted_birthdate = datetime.strptime(user.birthdate, "%m/%d/%Y").strftime("%Y-%m-%d")
                except ValueError:
                    formatted_birthdate = user.birthdate

    user.verification_status = "Verified" if user.is_verified else "Not Verified"
    context = await get_base_template_context(request, db)
    context.update({"user": user, "formatted_birthdate": formatted_birthdate})
    return templates.TemplateResponse("student_dashboard/settings.html", context)

# Get All Organizations
@app.get("/api/organizations/", response_model=List[schemas.Organization])
async def get_organizations(db: Session = Depends(get_db)):
    return db.query(models.Organization).all()

# User Signup
@app.post("/api/signup/")
async def signup(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user(db, identifier=user_data.student_number):
        raise HTTPException(status_code=400, detail="Student number already registered")
    if db.query(models.User).filter(models.User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.User).filter(models.User.first_name == user_data.first_name, models.User.last_name == user_data.last_name).first():
        raise HTTPException(status_code=400, detail="First and last name combination already registered")

    new_user = crud.create_user(db=db, user=user_data)

    current_year = date.today().year
    start_date = date(current_year, 2, 28)
    for i in range(8):
        academic_year = f"{current_year}-{current_year + 1}"
        due_date = start_date + timedelta(days=i * 6 * 30)
        year_level_applicable = (i // 2) + 1
        semester = "1st" if (i % 2) == 0 else "2nd"
        crud.add_payment_item(
            db=db, user_id=new_user.id, academic_year=academic_year, semester=semester,
            fee=100.00, 
            due_date=due_date,
            year_level_applicable=year_level_applicable,
        )
        if semester == "2nd": current_year += 1
    db.commit() 
    return {"message": "User created successfully", "user_id": new_user.id}

# Get User by ID
@app.get("/api/user/{user_id}", response_model=schemas.User)
async def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, identifier=str(user_id))
    if user is None: raise HTTPException(status_code=404, detail="User not found")
    return user

# Get User Data (for Navbar/Header)
@app.get("/get_user_data", response_model=schemas.UserDataResponse)
async def get_user_data(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")

    current_entity = None
    organization_data = None
    first_name = None
    profile_picture = None
    is_verified_status = None

    if user_id:
        current_entity = db.query(models.User).filter(models.User.id == user_id).first()
        if current_entity:
            first_name = current_entity.first_name
            profile_picture = current_entity.profile_picture
            is_verified_status = current_entity.is_verified
            if current_entity.organization:
                organization_data = schemas.Organization.model_validate(current_entity.organization)
    elif admin_id:
        current_entity = db.query(models.Admin).options(joinedload(models.Admin.organizations)).filter(models.Admin.admin_id == admin_id).first()
        if current_entity:
            first_name = current_entity.name 
            if current_entity.organizations:
                organization_data = schemas.Organization.model_validate(current_entity.organizations[0])

    if not current_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user/admin not found in database for provided session ID.")
    if not user_id and not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authenticated user or admin ID found in session.")

    return schemas.UserDataResponse(first_name=first_name, profile_picture=profile_picture, organization=organization_data, is_verified=is_verified_status)

# User and Admin Login
@app.post("/api/login/")
async def login(request: Request, form_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.identifier, form_data.password)
    if user:
        request.session["user_id"] = user.id
        request.session["user_role"] = getattr(user, 'role', 'user')
        return {"message": "User login successful", "user_id": user.id, "user_role": request.session["user_role"]}
    else:
        admin = crud.authenticate_admin_by_email(db, form_data.identifier, form_data.password)
        if admin:
            request.session["admin_id"] = admin.admin_id
            request.session["user_role"] = admin.role
            return {"message": "Admin login successful", "admin_id": admin.admin_id, "user_role": admin.role}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})

# Heart/Unheart Bulletin Posts
@app.post("/bulletin/heart/{post_id}")
async def heart_post(post_id: int, request: Request, db: Session = Depends(get_db), action: str = Form(...)):
    user, user_org = get_current_user_with_org(request, db)

    post = db.query(models.BulletinBoard).options(joinedload(models.BulletinBoard.admin)).filter(models.BulletinBoard.post_id == post_id).first()
    if not post: raise HTTPException(status_code=404, detail="Post not found")
    if not post.admin or not post.admin.organizations or post.admin.organizations[0].id != user_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only interact with posts from your own organization.")

    if action == 'heart':
        post.heart_count += 1
        crud.create_notification(db, f"{user.first_name} {user.last_name} liked your bulletin post: '{post.title}'",
                                 organization_id=user_org.id, admin_id=post.admin_id, notification_type="bulletin_like",
                                 entity_id=post_id, url=f"/admin/bulletin_board#{post_id}")
    elif action == 'unheart' and post.heart_count > 0:
        post.heart_count -= 1
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'heart' or 'unheart'.")

    db.commit()
    db.refresh(post)
    return {"heart_count": post.heart_count}

# Join Event
@app.post("/Events/join/{event_id}")
async def join_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    user, user_org = get_current_user_with_org(request, db)

    event = db.query(models.Event).options(joinedload(models.Event.participants), joinedload(models.Event.admin)).filter(models.Event.event_id == event_id).first()
    if not event: raise HTTPException(status_code=404, detail="Event not found")
    if not event.admin or not event.admin.organizations or event.admin.organizations[0].id != user_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only join events from your own organization.")

    if user in event.participants: raise HTTPException(status_code=400, detail="You are already joined in this event.")
    if event.joined_count() >= event.max_participants: raise HTTPException(status_code=400, detail="This event is full.")

    event.participants.append(user)
    crud.create_notification(db, f"{user.first_name} {user.last_name} joined your event: '{event.title}'", 
                             organization_id=user_org.id, admin_id=event.admin_id, notification_type="event_join",
                             entity_id=event_id, url=f"/admin/events#{event_id}")
    db.commit() 
    return RedirectResponse(url="/Events", status_code=status.HTTP_303_SEE_OTHER)

# Leave Event
@app.post("/Events/leave/{event_id}")
async def leave_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    user, user_org = get_current_user_with_org(request, db)

    event = db.query(models.Event).options(joinedload(models.Event.participants), joinedload(models.Event.admin)).filter(models.Event.event_id == event_id).first()
    if not event: raise HTTPException(status_code=404, detail="Event not found")
    if not event.admin or not event.admin.organizations or event.admin.organizations[0].id != user_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only leave events from your own organization.")

    if user not in event.participants: raise HTTPException(status_code=400, detail="You are not joined in this event.")

    event.participants.remove(user)
    db.commit()
    return RedirectResponse(url="/Events", status_code=status.HTTP_303_SEE_OTHER)

# Upcoming Events Summary
@app.get("/api/events/upcoming_summary")
async def get_upcoming_events_summary(request: Request, db: Session = Depends(get_db)):
    user, user_org = get_current_user_with_org(request, db)

    now = datetime.now()
    upcoming_events_with_admins = db.query(models.Event).options(joinedload(models.Event.admin).joinedload(models.Admin.organizations)).filter(models.Event.date >= now).order_by(models.Event.date).all()

    filtered_events = []
    if user_org:
        for event in upcoming_events_with_admins:
            if event.admin and event.admin.organizations and user_org.id in [org.id for org in event.admin.organizations]:
                filtered_events.append(event)
    
    limited_events = filtered_events[:5]
    return [{"title": event.title, "date": event.date.isoformat(), "location": event.location, "classification": event.classification} for event in limited_events]

# Generate Email Address
def generate_email(first_name: str, last_name: str) -> str:
    if first_name and last_name: return f"ic.{first_name.lower()}.{last_name.lower()}@cvsu.edu.ph"
    return None

# Update User Profile
@app.post("/api/profile/update/")
async def update_profile(
    request: Request,
    student_number: Optional[str] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),    
    address: Optional[str] = Form(None),
    birthdate: Optional[str] = Form(None), 
    sex: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    course: Optional[str] = Form(None),
    campus: Optional[str] = Form(None),
    semester: Optional[str] = Form(None),
    school_year: Optional[str] = Form(None),
    year_level: Optional[str] = Form(None),
    section: Optional[str] = Form(None),
    guardian_name: Optional[str] = Form(None),
    guardian_contact: Optional[str] = Form(None),
    is_verified: Optional[bool] = Form(None),
    registration_form: Optional[UploadFile] = File(None),
    profilePicture: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    user, _ = get_current_user_with_org(request, db)
    original_is_verified_status = user.is_verified

    for field, value in locals().items():        
        if value is not None and field in user.__table__.columns and field not in ["request", "db", "registration_form", "profilePicture", "name"]:
            if field == "birthdate" and isinstance(value, str):
                try:
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                        user.birthdate = value
                    elif re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", value):
                        user.birthdate = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                    elif re.match(r"^\d{2}/\d{2}/\d{4}$", value):
                        user.birthdate = datetime.strptime(value, "%m/%d/%Y").strftime("%Y-%m-%d")
                    else:
                        user.birthdate = value
                        logging.warning(f"Unexpected birthdate format for user {user.id}: {value}. Saving as-is.")
                except ValueError:
                    logging.error(f"Failed to parse birthdate string '{value}' for user {user.id}. Saving as-is.")
                    user.birthdate = value
            else:
                setattr(user, field, value)

    if registration_form:
        pdf_path = await handle_file_upload(registration_form, "documents/registration_forms", ["application/pdf"], old_file_path=user.registration_form)
        user.registration_form = pdf_path
        
        local_pdf_path = STATIC_DIR / pdf_path.lstrip("/static/")
        extracted_text = extract_text_from_pdf(local_pdf_path)

        student_info = extract_student_info(extracted_text)

        FIELDS_TO_OVERWRITE_FROM_PDF = [
            "student_number", "email", "first_name", "last_name", "name",
            "campus", "semester", "course", "school_year", "year_level",
            "section", "address", "birthdate", "sex", "contact",
            "guardian_name", "guardian_contact"
        ]

        if student_info.get("name"):
            name_str = re.sub(r"\s+[a-zA-Z]\.\s+|\s+[a-zA-Z]\.$|\s+[a-zA-Z]\.(?=\s)", " ", student_info["name"]).strip()
            name_parts = name_str.split()
            if len(name_parts) >= 2:
                user.first_name = " ".join(name_parts[:-1]).title()
                user.last_name = name_parts[-1].title()
            elif len(name_parts) == 1:
                user.first_name = name_parts[0].title()
            if "name" in student_info and "name" in user.__table__.columns:
                 user.name = student_info["name"]

        for key, value in student_info.items():
            if value is not None and key in user.__table__.columns and key in FIELDS_TO_OVERWRITE_FROM_PDF:
                if key == "birthdate" and isinstance(value, str):
                    try:
                        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                            user.birthdate = value
                        elif re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", value):
                            user.birthdate = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                        elif re.match(r"^\d{2}/\d{2}/\d{4}$", value):
                            user.birthdate = datetime.strptime(value, "%m/%d/%Y").strftime("%Y-%m-%d")
                        else:
                            user.birthdate = value
                    except ValueError:
                        logging.error(f"Failed to parse PDF extracted birthdate string '{value}' for user {user.id}. Saving as-is.")
                        user.birthdate = value
                elif key not in ["first_name", "last_name", "email"]:
                    setattr(user, key, value)
        
        user.is_verified = True
        if user.first_name and user.last_name:
            user.email = generate_email(user.first_name.replace(" ", ""), user.last_name)

    if profilePicture:
        profile_pic_path = await handle_file_upload(profilePicture, "images/profile_pictures", ["image/jpeg", "image/png", "image/gif"], max_size_bytes=2 * 1024 * 1024, old_file_path=user.profile_picture)
        user.profile_picture = profile_pic_path
    
    current_date = datetime.now()
    year_level_map = {"1st": 1, "first": 1, "1": 1, "2nd": 2, "second": 2, "2": 2, "3rd": 3, "third": 3, "3": 3, "4th": 4, "fourth": 4, "4": 4}
    student_year = year_level_map.get(str(user.year_level).lower().strip(), 1)
    first_academic_year_start = current_date.year - (student_year - 1)
    if current_date.month < 9: first_academic_year_start -= 1

    for i, item in enumerate(user.payment_items):
        item_academic_year_start = first_academic_year_start + (i // 2)
        item.academic_year = f"{item_academic_year_start}-{item_academic_year_start + 1}"
        academic_year_end_year = int(item.academic_year.split("-")[1])

        if (i % 2) == 0:
            due_date = datetime(academic_year_end_year, 1, 1) + timedelta(days=(6 - datetime(academic_year_end_year, 1, 1).weekday()) % 7)
        else:
            due_date = datetime(academic_year_end_year, 6, 1) + timedelta(days=(6 - datetime(academic_year_end_year, 6, 1).weekday()) % 7) + timedelta(days=14)
        
        item.due_date = due_date.date()
        item.is_past_due = item.due_date < current_date.date() and not item.is_paid
        db.add(item)
    db.flush()

    if not original_is_verified_status and user.is_verified and user.organization_id:
        for admin in db.query(models.Admin).join(models.organization_admins).filter(models.organization_admins.c.organization_id == user.organization_id).all():
            crud.create_notification(db=db, message=f"Member {user.first_name} {user.last_name} has been verified.",
                                     organization_id=user.organization_id, admin_id=admin.admin_id, notification_type="member_verification",
                                     entity_id=user.id, url=f"/admin/payments/total_members?student_number={user.student_number}")

    db.commit()
    db.refresh(user)
    user.verification_status = "Verified" if user.is_verified else "Not Verified"
    return {"message": "Profile updated successfully", "user": user}
