from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Form, APIRouter, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_, extract
from . import models, schemas, crud # Assuming models, schemas, and crud are in the same package
from .database import SessionLocal, engine # Assuming database.py is in the same package
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from io import BytesIO
from PIL import Image
from collections import defaultdict
import os
import secrets
import re
import requests
import base64
import logging
import bcrypt
import shutil
import calendar
import random
from dateutil.relativedelta import relativedelta

from starlette.middleware.sessions import SessionMiddleware

from .text import extract_text_from_pdf, extract_student_info # Assuming text.py is in the same package

# Create all database tables defined in models.Base
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI()

# Add SessionMiddleware for managing user sessions
app.add_middleware(SessionMiddleware, secret_key="your_secret_key") # Replace with a strong, secret key

# Define base directory for static files and templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Mount static files directory
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "frontend" / "static"),
    name="static"
)

# Initialize APIRouter for organizing routes
router = APIRouter()

# Initialize Jinja2Templates for rendering HTML templates
templates = Jinja2Templates(directory=BASE_DIR / "frontend" / "templates")

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Set to DEBUG to capture all messages


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper function to generate a secure filename
def generate_secure_filename(original_filename: str) -> str:
    _, file_extension = os.path.splitext(original_filename)
    random_prefix = secrets.token_hex(16)
    return f"{random_prefix}{file_extension}"

UPLOAD_BASE_DIRECTORY = Path(__file__).parent.parent.parent / "frontend" / "static" / "images"
UPLOAD_BASE_DIRECTORY.mkdir(parents=True, exist_ok=True) # Ensure the directory exists

# Admin Bulletin Board Post Route
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
    try:
        admin_id = request.session.get("admin_id")
        if not admin_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated as admin",
            )

        admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin user not found",
            )

        image_path = None
        if image and image.filename:
            if image.content_type.startswith("image/"):
                try:
                    filename = generate_secure_filename(image.filename)
                    file_path = os.path.join(
                        "..", "frontend", "static", "images", "bulletin_board", filename
                    )
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "wb") as f:
                        f.write(await image.read())
                    image_path = f"/static/images/bulletin_board/{filename}"
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to save image: {e}",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image file type",
                )

        db_post = models.BulletinBoard(
            title=title,
            content=content,
            category=category,
            is_pinned=is_pinned,
            admin_id=admin_id,
            image_path=image_path,
        )
        db.add(db_post)
        db.commit()
        db.refresh(db_post)

        return RedirectResponse(url="/admin/bulletin_board",
                                    status_code=status.HTTP_303_SEE_OTHER)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during post creation",
        )

# Admin Settings Page Route
@router.get("/admin_settings/", response_class=HTMLResponse, name="admin_settings")
async def admin_settings(request: Request, db: Session = Depends(get_db)):
    current_user_id: Optional[int] = request.session.get("user_id") or request.session.get("admin_id")
    user_role: Optional[str] = request.session.get("user_role")
    admin_id = request.session.get("admin_id")

    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if user_role != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions. Admin access required.")

    # Default logo URL if no organization logo is found
    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')

    organization_id = None # Initialize organization_id
    current_theme_color = "#6B00B9" # Default theme color
    logo_url = default_logo_url # Initialize the logo_url that admin_base expects

    if admin_id:
        admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
        if admin and admin.organizations:
            first_org = admin.organizations[0] # Assuming an admin manages the first organization in the list
            organization_id = first_org.id # Get the organization ID
            
            if first_org.logo_url:
                logo_url = first_org.logo_url # Assign the organization's specific logo URL to logo_url
            
            if first_org.theme_color:
                current_theme_color = first_org.theme_color # Get the current theme color

    return templates.TemplateResponse(
        "admin_dashboard/admin_settings.html", # Ensure this path is correct for your template
        {
            "request": request,
            "year": "2025",
            "organization_id": organization_id, # Pass organization_id to the template
            "current_theme_color": current_theme_color, # Pass current theme color
            "logo_url": logo_url # Changed this from "organization_logo_url" to "logo_url"
        },
    )

# Admin Create Event Route
@router.post("/admin/events/create", name="admin_create_event")
async def admin_create_event(
    request: Request,
    title: str = Form(...),
    classification: str = Form(...),
    description: str = Form(...),
    date: str = Form(...), # This is the date string from the form (e.g., "2025-05-27T14:30")
    location: str = Form(...),
    max_participants: int = Form(...),
    db: Session = Depends(get_db)
):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated as admin",
        )

    admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found",
        )

    try:
        # Parse the datetime-local format (YYYY-MM-DDTHH:MM)
        event_date = datetime.strptime(date, "%Y-%m-%dT%H:%M") # <--- MODIFIED THIS LINE
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date and time format. Please use YYYY-MM-DDTHH:MM (e.g., 2025-05-27T14:30).",
        )

    # Ensure admin_org_id is correctly retrieved
    admin_org_id = None
    try:
        admin_org_id = get_entity_organization_id(db, admin_id)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin not associated with an organization.",
        )

    if not admin_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin not associated with an organization.",
        )

    db_event = models.Event(
        title=title,
        classification=classification,
        description=description,
        date=event_date, # Use the parsed datetime object
        location=location,
        max_participants=max_participants,
        admin_id=admin_id, # Assign the admin who created it
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return RedirectResponse(url="/admin/events", status_code=status.HTTP_303_SEE_OTHER)

# Admin Delete Event Route
@router.post("/admin/events/delete/{event_id}", response_class=HTMLResponse, name="admin_delete_event")
async def admin_delete_event(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    try:
        event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        db.delete(event)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    finally:
        db.close()
    return RedirectResponse(url="/admin/events", status_code=status.HTTP_303_SEE_OTHER)

# Admin Delete Bulletin Post Route
@router.post("/admin/bulletin_board/delete/{post_id}", response_class=HTMLResponse, name="admin_delete_bulletin_post")
async def admin_delete_bulletin_post(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db),
):
    try:
        post = db.query(models.BulletinBoard).filter(models.BulletinBoard.post_id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )
        db.delete(post)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    finally:
        db.close()
    return RedirectResponse(url="/admin/bulletin_board", status_code=status.HTTP_303_SEE_OTHER)

# Admin Payments Page Route
@router.get("/Admin/payments", response_class=HTMLResponse, name="admin_payments")
async def admin_payments(
    request: Request,
    db: Session = Depends(get_db),
    student_number: Optional[str] = None,
):
    """
    Displays all payment items for administrators, with accurate payment status
    respecting the is_past_due and is_not_responsible flags, and student number.
    Filters payment items by the admin's organization.
    """
    current_user_id: Optional[int] = request.session.get("user_id") or request.session.get("admin_id")
    user_role: Optional[str] = request.session.get("user_role")
    admin_id = request.session.get("admin_id")

    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if user_role != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions. Admin access required.")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url
    
    admin_org_id = None
    if admin_id:
        admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
        if admin and admin.organizations:
            first_org = admin.organizations[0]
            if first_org.logo_url:
                logo_url = first_org.logo_url
            admin_org_id = first_org.id # Get the admin's organization ID

    query = db.query(models.PaymentItem).join(models.User)

    if admin_org_id:
        query = query.filter(models.User.organization_id == admin_org_id) # Filter by organization

    if student_number:
        query = query.filter(models.User.student_number == student_number)

    payment_items = query.all()

    payment_items_with_status = []
    today = date.today()
    for item in payment_items:
        status_text = "Unpaid"
        retrieved_student_number = None
        if item.user:
            retrieved_student_number = item.user.student_number

        if item.is_not_responsible:
            status_text = "Not Responsible"
        elif item.is_paid:
            status_text = "Paid"
        elif item.is_past_due:
            status_text = "Past Due"

        payment_items_with_status.append(
            {
                "item": item,
                "status": status_text,
                "student_number": retrieved_student_number,
            }
        )

    return templates.TemplateResponse(
        "admin_dashboard/admin_payments.html",
        {
            "request": request,
            "year": "2025",
            "payment_items": payment_items_with_status,
            "now": today,
            "student_number": student_number,
            "logo_url": logo_url,
        },
    )



@router.post("/admin/payment/{payment_item_id}/update_status")
async def update_payment_status(
    request: Request,
    payment_item_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Updates the status of a specific payment item and handles payment creation
    or updates based on the selected status. Includes marking item as 'not responsible'
    and explicitly handles 'Unpaid' status with past due override.
    """
    current_user_id: Optional[int] = request.session.get("user_id") or request.session.get("admin_id")
    user_role: Optional[str] = request.session.get("user_role")

    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if user_role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin access required.",
        )

    allowed_statuses = ["Unpaid", "Paid", "NOT RESPONSIBLE"]
    if status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status}. Allowed statuses are: {allowed_statuses}",
        )

    try:
        payment_item = db.query(models.PaymentItem).get(payment_item_id)
        if not payment_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment item {payment_item_id} not found",
            )

        payment_item.is_paid = (status == "Paid")
        payment_item.is_not_responsible = (status == "NOT RESPONSIBLE")
        if status == "Unpaid":
            payment_item.is_past_due = False
        elif status == "Paid":
            payment_item.is_past_due = False

            existing_payment = db.query(models.Payment).filter(models.Payment.payment_item_id == payment_item_id).first()

            if existing_payment:
                existing_payment.amount = payment_item.fee
                existing_payment.status = "success"
            else:
                new_payment = models.Payment(
                    user_id=payment_item.user_id,
                    amount=payment_item.fee,
                    payment_item_id=payment_item_id,
                    status="success"
                )
                db.add(new_payment)
            db.commit()
        elif status == "NOT RESPONSIBLE":
            existing_payment = db.query(models.Payment).filter(models.Payment.payment_item_id == payment_item_id).first()
            if existing_payment:
                db.delete(existing_payment)
                db.commit()

        db.commit()
        db.refresh(payment_item)
        return {"message": f"Payment item {payment_item_id} status updated to {status}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update payment item status: {e}",
        )


@router.get("/admin/membership/")
async def admin_membership(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: Optional[str] = None,
    semester: Optional[str] = None,
) -> List[Dict]:
    """
    Retrieves membership data, optionally filtered by academic year and semester,
    ensuring no duplicate sections are displayed. Filters members by the admin's organization.
    """
    try:
        admin_id = request.session.get("admin_id")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as admin")

        admin_org_id = get_entity_organization_id(db, admin_id)

        query = db.query(models.User).options(
            joinedload(models.User.payment_items).options(joinedload(models.PaymentItem.payments))
        ).filter(models.User.organization_id == admin_org_id) # Filter by organization
        
        users = query.all()

        membership_data = []
        processed_sections = set()

        for user in users:
            if user.section not in processed_sections:
                section_total_paid = 0
                section_total_amount = 0
                displayed_school_year = None
                displayed_semester = None
                section_users_count = 0
                section_paid_count = 0

                section_users = [u for u in users if u.section == user.section]

                for other_user in section_users:
                    filtered_payment_items = [
                        pi for pi in other_user.payment_items
                        if (academic_year is None or pi.academic_year == academic_year) and
                        (semester is None or pi.semester == semester)
                    ]

                    other_user_total_paid = 0
                    other_user_total_amount = 0
                    for pi in filtered_payment_items:
                        other_user_total_amount += pi.fee
                        for p in pi.payments:
                            if p.status == 'success':
                                other_user_total_paid += p.amount

                    section_total_paid += other_user_total_paid
                    section_total_amount += other_user_total_amount
                    section_users_count += 1

                    if other_user_total_paid >= other_user_total_amount and other_user_total_amount > 0:
                        section_paid_count += 1

                    if filtered_payment_items and displayed_school_year is None:
                        displayed_school_year = filtered_payment_items[0].academic_year
                        displayed_semester = filtered_payment_items[0].semester

                if academic_year is None and semester is None:
                    status = str(section_users_count)
                elif academic_year is not None and semester is not None:
                    status = f"{section_paid_count}/{section_users_count}"
                else:
                    status = str(section_users_count)

                representative_user = section_users[0]
                membership_data.append(
                    {
                        'student_number': representative_user.student_number,
                        'email': representative_user.email,
                        'first_name': representative_user.first_name,
                        'last_name': representative_user.last_name,
                        'year_level': representative_user.year_level,
                        'section': representative_user.section,
                        'status': status,
                        'total_paid': section_total_paid,
                        'total_amount': section_total_amount,
                        'academic_year': displayed_school_year,
                        'semester': displayed_semester,
                        'section_users_count': section_users_count,
                        'section_paid_count': section_paid_count
                    }
                )
                processed_sections.add(user.section)

        return membership_data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch membership data")


@router.get("/admin/individual_members/")
async def admin_individual_members(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: Optional[str] = None,
    semester: Optional[str] = None,
) -> List[Dict]:
    """
    Retrieves individual membership data, optionally filtered by academic year and semester.
    This route is specifically for displaying each individual member.
    Filters individual members by the admin's organization.
    """
    try:
        admin_id = request.session.get("admin_id")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as admin")

        admin_org_id = get_entity_organization_id(db, admin_id)

        query = db.query(models.User).options(
            joinedload(models.User.payment_items).options(joinedload(models.PaymentItem.payments))
        ).filter(models.User.organization_id == admin_org_id) # Filter by organization

        filters = []
        if academic_year:
            filters.append(models.PaymentItem.academic_year == academic_year)
        if semester:
            filters.append(models.PaymentItem.semester == semester)

        if filters:
            # Apply filters only if payment items are loaded, otherwise it might cause issues
            # if a user has no payment items for the given filter but belongs to the org.
            # This logic needs to be carefully considered if a user can exist without payment items.
            # For now, assuming payment items are always present if filters are applied.
            query = query.join(models.PaymentItem).filter(*filters)

        users = query.all()

        membership_data = []
        for user in users:
            total_paid = 0
            total_amount = 0
            payment_status = "Not Applicable"

            for pi in user.payment_items:
                if (academic_year is None or pi.academic_year == academic_year) and \
                   (semester is None or pi.semester == semester):
                    total_amount += pi.fee
                    for p in pi.payments:
                        if p.status == 'success':
                            total_paid += p.amount

            if total_amount > 0:
                if total_paid >= total_amount:
                    payment_status = "Paid"
                else:
                    payment_status = "Partially Paid"
            elif academic_year is None and semester is None:
                payment_status = "No Dues"

            membership_data.append(
                {
                    'student_number': user.student_number,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'year_level': user.year_level,
                    'section': user.section,
                    'total_paid': total_paid,
                    'total_amount': total_amount,
                    'payment_status': payment_status,
                    'academic_year': academic_year,
                    'semester': semester,
                }
            )

        return membership_data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch individual membership data")

    
@router.get("/financial_trends")
async def get_financial_trends(request: Request, db: Session = Depends(get_db)):
    """
    Returns monthly trends of total successful membership fees collected, filtered by the admin's organization.
    """
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as admin")

    admin_org_id = get_entity_organization_id(db, admin_id)

    financial_data = db.query(
        func.extract('year', models.Payment.created_at),
        func.extract('month', models.Payment.created_at),
        func.sum(models.Payment.amount)
    ).join(
        models.Payment.user # Join with User to access organization_id
    ).filter(
        models.Payment.status == "success",
        models.User.organization_id == admin_org_id # Filter by organization
    ).group_by(
        func.extract('year', models.Payment.created_at),
        func.extract('month', models.Payment.created_at)
    ).order_by(
        func.extract('year', models.Payment.created_at),
        func.extract('month', models.Payment.created_at)
    ).all()

    labels = [f"{year}-{month}" for year, month, total in financial_data]
    data = [float(total) for year, month, total in financial_data]

    return {"labels": labels, "data": data}

@router.get("/expenses_by_category")
async def get_expenses_by_category(request: Request, db: Session = Depends(get_db)):
    """
    Returns total fees per academic year from PaymentItem, filtered by the admin's organization.
    """
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as admin")

    admin_org_id = get_entity_organization_id(db, admin_id)

    expenses_data = db.query(
        models.PaymentItem.academic_year,
        func.sum(models.PaymentItem.fee)
    ).join(
        models.PaymentItem.user # Join with User to access organization_id
    ).filter(
        models.User.organization_id == admin_org_id # Filter by organization
    ).group_by(
        models.PaymentItem.academic_year
    ).all()

    labels = [category if category else "Unknown Year" for category, total in expenses_data]
    data = [float(total) for category, total in expenses_data]

    return {"labels": labels, "data": data}

@router.get("/fund_distribution")
async def get_fund_distribution(request: Request, db: Session = Depends(get_db)):
    """
    Distributes collected *successful* funds based on the academic year
    of the associated PaymentItem, filtered by the admin's organization.
    """
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as admin")

    admin_org_id = get_entity_organization_id(db, admin_id)

    fund_allocation = db.query(
        models.PaymentItem.academic_year,
        func.sum(models.Payment.amount)
    ).join(
        models.Payment, models.PaymentItem.id == models.Payment.payment_item_id
    ).join(
        models.PaymentItem.user # Join with User to access organization_id
    ).filter(
        models.Payment.status == "success",
        models.User.organization_id == admin_org_id # Filter by organization
    ).group_by(
        models.PaymentItem.academic_year
    ).all()

    distribution_data = {}
    for academic_year, total_amount in fund_allocation:
        category = academic_year if academic_year else "General Funds"
        distribution_data[category] = distribution_data.get(category, 0.0) + float(total_amount)

    labels = list(distribution_data.keys())
    data = list(distribution_data.values())

    return {"labels": labels, "data": data}


@router.get("/admin/outstanding_dues/")
async def admin_outstanding_dues(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: Optional[str] = None,
) -> List[Dict]:
    """
    Retrieves the total outstanding dues amount, filtered by academic year,
    CURRENT semester, and the admin's organization.
    This version uses case-insensitive comparison for academic year. The semester
    is always the *current* semester, determined by the server.
    """
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as admin")

    admin_org_id = get_entity_organization_id(db, admin_id)
    if not admin_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin organization not found or accessible")

    try:
        today = datetime.now()
        month = today.month
        
        current_semester = "1st" if 6 <= month <= 11 else "2nd"

        resolved_academic_year = academic_year
        if not resolved_academic_year:
            current_year = today.year
            start_year = current_year - 1 if today.month < 6 else current_year
            end_year = start_year + 1
            resolved_academic_year = f"{start_year}-{end_year}"

        # Join PaymentItem directly to User and filter by organization, academic year, and semester
        query = db.query(models.PaymentItem).join(
            models.User, models.PaymentItem.user_id == models.User.id
        ).filter(
            and_(
                func.lower(models.PaymentItem.academic_year) == resolved_academic_year.lower(),
                models.PaymentItem.semester == current_semester,
                models.User.organization_id == admin_org_id,
                models.PaymentItem.is_not_responsible == False # Only consider those responsible
            )
        )
        
        relevant_payment_items = query.all()
        
        total_outstanding_amount = 0.0

        for item in relevant_payment_items:
            # If the PaymentItem is not marked as paid, add its fee to the outstanding total
            if not item.is_paid:
                total_outstanding_amount += item.fee

        return [{"total_outstanding_amount": total_outstanding_amount}]

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch outstanding dues data")



@router.get("/admin/payments/total_members", response_class=HTMLResponse, name="payments_total_members")
async def payments_total_members(
    request: Request,
    db: Session = Depends(get_db),
    section: Optional[str] = None,
    year_level: Optional[str] = None,
    student_number: Optional[str] = None
):
    """
    Displays total members, filtered by the admin's organization, and optionally by section, year level, or student number.
    """
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as admin")

    admin_org_id = get_entity_organization_id(db, admin_id)

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url
    admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
    if admin and admin.organizations:
        first_org = admin.organizations[0]
        if first_org.logo_url:
            logo_url = first_org.logo_url

    query = db.query(models.User).filter(models.User.organization_id == admin_org_id) # Filter by organization

    if section:
        query = query.filter(models.User.section == section)

    if year_level:
        query = query.filter(models.User.year_level == year_level)

    if student_number:
        query = query.filter(models.User.student_number == student_number)

    users = query.all()

    return templates.TemplateResponse(
        "admin_dashboard/payments/total_members.html",
        {
            "request": request,
            "members": users,
            "section": section,
            "year": 2025,
            "year_level": year_level,
            "student_number": student_number,
            "logo_url": logo_url,
        },
    )

# Admin Bulletin Board Page Route
@router.get('/admin/bulletin_board', response_class=HTMLResponse)
async def admin_bulletin_board(request: Request, db: Session = Depends(get_db)):
    """
    Displays the admin bulletin board page with recent posts, filtered by the admin's organization.
    """
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    admin_org_id = None
    try:
        admin_org_id = get_entity_organization_id(db, admin_id)
    except HTTPException as e:
        raise e # Re-raise if admin not found or not associated with org

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url
    admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
    if admin and admin.organizations:
        first_org = admin.organizations[0]
        if first_org.logo_url:
            logo_url = first_org.logo_url

    posts: List[models.BulletinBoard] = []
    if admin_org_id:
        posts = db.query(models.BulletinBoard).join(models.Admin).join(models.Admin.organizations).filter(
            models.Organization.id == admin_org_id
        ).order_by(models.BulletinBoard.created_at.desc()).all()

    return templates.TemplateResponse(
        "admin_dashboard/admin_bulletin_board.html",
        {
            "request": request,
            "posts": posts,
            "logo_url": logo_url,
        },
    )

# Admin Events Page Route
@router.get('/admin/events', response_class=HTMLResponse)
async def admin_events(request: Request, db: Session = Depends(get_db)):
    """
    Displays the admin events page with a list of events.
    """
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    admin_org_id = None
    try:
        admin_org_id = get_entity_organization_id(db, admin_id)
    except HTTPException as e:
        raise e

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url
    admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
    if admin and admin.organizations:
        first_org = admin.organizations[0]
        if first_org.logo_url:
            logo_url = first_org.logo_url

    events: List[models.Event] = []
    if admin_org_id:
        events = db.query(models.Event).join(models.Admin).join(models.Admin.organizations).filter(
            models.Organization.id == admin_org_id
        ).order_by(models.Event.created_at.desc()).all()

    return templates.TemplateResponse(
        "admin_dashboard/admin_events.html",
        {
            "request": request,
            "events": events,
            "logo_url": logo_url,
        },
    )

# Admin Financial Statement Page Route
# 1. Existing route to serve the HTML dashboard page (no change here)
@router.get("/admin/financial_statement", response_class=HTMLResponse, name="admin_financial_statement")
async def admin_financial_statement_page(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")

    # Basic authentication check for rendering the page
    if not admin_id:
        # Redirect to login or show an unauthorized message
        # For a full application, you'd use a proper redirect or authentication middleware
        return templates.TemplateResponse(
            "admin_dashboard/unauthorized.html", # Or redirect using RedirectResponse
            {"request": request, "message": "You must be logged in as an admin to view this page."}
        )

    # Optional: Fetch admin and organization details for logo etc.
    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url
    admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
    if admin and admin.organizations:
        first_org = admin.organizations[0]
        if first_org.logo_url:
            logo_url = first_org.logo_url

    return templates.TemplateResponse(
        "admin_dashboard/admin_financial_statement.html",
        {
            "request": request,
            "year": str(datetime.now().year),
            "logo_url": logo_url,
            # IMPORTANT: Do NOT pass all financial_data here if you intend to fetch it via AJAX.
            # Only pass data needed for the initial page render that doesn't change with AJAX.
            # The JavaScript will fetch the dynamic financial_data separately.
        },
    )

# 2. NEW route to serve the financial data as JSON (this is what your JS will call)
@router.get("/api/admin/financial_data", response_class=JSONResponse, name="admin_financial_data_api")
async def admin_financial_data_api(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")

    if not admin_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    organization = db.query(models.Organization).\
        join(models.organization_admins).\
        filter(models.organization_admins.c.admin_id == admin_id).\
        first()

    if not organization:
        raise HTTPException(status_code=403, detail="Admin not linked to an organization or organization not found.")
    
    organization_id = organization.id
    organization_name = organization.name

    current_year = datetime.now().year
    today = datetime.now().date()

    total_revenue_ytd_query = db.query(func.sum(models.PaymentItem.fee)).\
        join(models.User).\
        filter(
            and_(
                extract('year', models.PaymentItem.created_at) == current_year,
                models.PaymentItem.is_paid == True,
                models.User.organization_id == organization_id
            )
        ).scalar()
    total_revenue_ytd = float(total_revenue_ytd_query) if total_revenue_ytd_query else 0.0

    total_expenses_ytd_query = db.query(func.sum(models.Expense.amount)).\
        filter(
            and_(
                extract('year', models.Expense.incurred_at) == current_year,
                models.Expense.organization_id == organization_id
            )
        ).scalar()
    total_expenses_ytd = float(total_expenses_ytd_query) if total_expenses_ytd_query else 0.0

    net_income_ytd = total_revenue_ytd - total_expenses_ytd

    total_current_balance = net_income_ytd
    total_funds_available = total_current_balance

    balance_turnover = 0.0
    if total_current_balance > 0:
        balance_turnover = round(total_revenue_ytd / total_current_balance, 2)

    reporting_date = today.strftime("%B %d, %Y")

    top_revenue_source_query = db.query(
        models.PaymentItem.academic_year,
        models.PaymentItem.semester,
        func.sum(models.PaymentItem.fee).label('total_fee')
    ).join(models.User).\
    filter(
        and_(
            extract('year', models.PaymentItem.created_at) == current_year,
            models.PaymentItem.is_paid == True,
            models.User.organization_id == organization_id
        )
    ).group_by(
        models.PaymentItem.academic_year,
        models.PaymentItem.semester
    ).order_by(
        func.sum(models.PaymentItem.fee).desc()
    ).first()

    top_revenue_source = {"name": "N/A", "amount": 0.0}
    if top_revenue_source_query:
        source_name = f"{top_revenue_source_query.academic_year} {top_revenue_source_query.semester} Fees" \
            if top_revenue_source_query.academic_year and top_revenue_source_query.semester \
            else "Collected Fees"
        top_revenue_source = {
            "name": source_name,
            "amount": round(float(top_revenue_source_query.total_fee), 2)
        }

    largest_expense_query = db.query(
        models.Expense.category,
        func.sum(models.Expense.amount).label('total_amount')
    ).filter(
        and_(
            extract('year', models.Expense.incurred_at) == current_year,
            models.Expense.organization_id == organization_id
        )
    ).group_by(
        models.Expense.category
    ).order_by(
        func.sum(models.Expense.amount).desc()
    ).first()

    largest_expense_category = "N/A"
    largest_expense_amount = 0.0
    if largest_expense_query:
        largest_expense_category = largest_expense_query.category
        largest_expense_amount = round(float(largest_expense_query.total_amount), 2)

    profit_margin_ytd = round((net_income_ytd / total_revenue_ytd) * 100, 2) if total_revenue_ytd != 0 else 0.0

    revenues_breakdown_query = db.query(
        models.PaymentItem.academic_year,
        models.PaymentItem.semester,
        func.sum(models.PaymentItem.fee).label('total_fee')
    ).join(models.User).\
    filter(
        and_(
            extract('year', models.PaymentItem.created_at) == current_year,
            models.PaymentItem.is_paid == True,
            models.User.organization_id == organization_id
        )
    ).group_by(
        models.PaymentItem.academic_year,
        models.PaymentItem.semester
    ).all()

    revenues_breakdown = []
    for item in revenues_breakdown_query:
        source_name = f"{item.academic_year} {item.semester} Fees" \
            if item.academic_year and item.semester \
            else "Uncategorized Fees"
        percentage = round((float(item.total_fee) / total_revenue_ytd) * 100, 2) if total_revenue_ytd != 0 else 0.0
        revenues_breakdown.append({
            "source": source_name,
            "amount": round(float(item.total_fee), 2),
            "trend": "Stable",
            "percentage": percentage
        })
    if not revenues_breakdown and total_revenue_ytd > 0:
        revenues_breakdown.append({
            "source": "General Collected Fees",
            "amount": total_revenue_ytd,
            "trend": "Stable",
            "percentage": 100.0
        })

    expenses_breakdown_query = db.query(
        models.Expense.category,
        func.sum(models.Expense.amount).label('total_amount')
    ).filter(
        and_(
            extract('year', models.Expense.incurred_at) == current_year,
            models.Expense.organization_id == organization_id
        )
    ).group_by(
        models.Expense.category
    ).all()

    expenses_breakdown = []
    for item in expenses_breakdown_query:
        percentage = round((float(item.total_amount) / total_expenses_ytd) * 100, 2) if total_expenses_ytd != 0 else 0.0
        expenses_breakdown.append({
            "category": item.category,
            "amount": round(float(item.total_amount), 2),
            "trend": "Stable",
            "percentage": percentage
        })
    if expenses_breakdown and total_expenses_ytd > 0:
        current_sum_percentage = sum(item['percentage'] for item in expenses_breakdown)
        if current_sum_percentage != 100 and current_sum_percentage != 0:
            adjustment_factor = 100 / current_sum_percentage
            for item in expenses_breakdown:
                item['percentage'] = round(item['percentage'] * adjustment_factor, 2)

    monthly_summary = []
    chart_net_income_trend_data = []
    chart_net_income_trend_labels = []

    for i in range(12):
        target_date = today - relativedelta(months=11 - i)

        target_month_num = target_date.month
        target_year = target_date.year

        month_name_full = target_date.strftime('%B')
        month_name_abbr = target_date.strftime('%b')
        chart_net_income_trend_labels.append(month_name_abbr)

        monthly_revenue_query = db.query(func.sum(models.PaymentItem.fee)).\
            join(models.User).\
            filter(
                and_(
                    extract('year', models.PaymentItem.created_at) == target_year,
                    extract('month', models.PaymentItem.created_at) == target_month_num,
                    models.PaymentItem.is_paid == True,
                    models.User.organization_id == organization_id
                )
            ).scalar()
        monthly_revenue = float(monthly_revenue_query) if monthly_revenue_query else 0.0

        monthly_expenses_query = db.query(func.sum(models.Expense.amount)).\
            filter(
                and_(
                    extract('year', models.Expense.incurred_at) == target_year,
                    extract('month', models.Expense.incurred_at) == target_month_num,
                    models.Expense.organization_id == organization_id
                )
                
            ).scalar()
        monthly_expenses = float(monthly_expenses_query) if monthly_expenses_query else 0.0

        monthly_net_income = monthly_revenue - monthly_expenses
        net_income_class = "positive" if monthly_net_income >= 0 else "negative"

        monthly_summary.append({
            "month": month_name_full,
            "revenue": monthly_revenue,
            "expenses": monthly_expenses,
            "net_income": monthly_net_income,
            "net_income_class": net_income_class
        })
        
        chart_net_income_trend_data.append(round(monthly_net_income, 2))

    accounts_balances = []
    if total_current_balance >= 0:
        accounts_balances = [
            {
                "account": "Main Operating Account",
                "balance": round(total_current_balance * 0.7, 2),
                "last_transaction": today.strftime("%Y-%m-%d"),
                "status": "Active"
            },
            {
                "account": "Savings Account",
                "balance": round(total_current_balance * 0.2, 2),
                "last_transaction": (today - timedelta(days=random.randint(10, 60))).strftime("%Y-%m-%d"),
                "status": "Active"
            },
            {
                "account": "Petty Cash",
                "balance": round(total_current_balance * 0.1, 2),
                "last_transaction": (today - timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d"),
                "status": "Active"
            }
        ]
        if accounts_balances:
            current_sum_balances = sum(acc['balance'] for acc in accounts_balances)
            if abs(current_sum_balances - total_current_balance) > 0.01:
                accounts_balances[-1]['balance'] += (total_current_balance - current_sum_balances)
                accounts_balances[-1]['balance'] = round(accounts_balances[-1]['balance'], 2)
    else:
        accounts_balances = [
            {
                "account": "Main Operating Account",
                "balance": total_current_balance,
                "last_transaction": today.strftime("%Y-%m-%d"),
                "status": "Critical"
            }
        ]

    paid_members_query = db.query(func.count(models.User.id.distinct())).\
        join(models.PaymentItem).\
        filter(
            and_(
                extract('year', models.PaymentItem.created_at) == current_year,
                models.PaymentItem.is_paid == True,
                models.User.organization_id == organization_id
            )
        ).scalar()
    num_paid_members = paid_members_query if paid_members_query else 0

    total_members_query = db.query(func.count(models.User.id)).\
        filter(
            and_(
                models.User.is_active == True,
                models.User.organization_id == organization_id
            )
        ).scalar()
    total_members = total_members_query if total_members_query else 0

    num_unpaid_members = total_members - num_paid_members
    if num_unpaid_members < 0:
        num_unpaid_members = 0

    financial_data = {
        "organization_id": organization_id,
        "organization_name": organization_name,
        "year": str(current_year),
        "total_current_balance": f"{total_current_balance:,.2f}",
        "total_revenue_ytd": f"{total_revenue_ytd:,.2f}",
        "total_expenses_ytd": f"{total_expenses_ytd:,.2f}",
        "net_income_ytd": f"{net_income_ytd:,.2f}",
        "balance_turnover": f"{balance_turnover:,.2f}",
        "total_funds_available": f"{total_funds_available:,.2f}",
        "reporting_date": reporting_date,
        "top_revenue_source_name": top_revenue_source["name"],
        "top_revenue_source_amount": f"{top_revenue_source['amount']:,.2f}",
        "largest_expense_category": largest_expense_category,
        "largest_expense_amount": f"{largest_expense_amount:,.2f}",
        "profit_margin_ytd": f"{profit_margin_ytd:,.2f}",
        "revenues_breakdown": revenues_breakdown,
        "expenses_breakdown": expenses_breakdown,
        "monthly_summary": monthly_summary,
        "accounts_balances": accounts_balances,
        "chart_revenue_data": [total_revenue_ytd, total_expenses_ytd],
        "chart_net_income_data": chart_net_income_trend_data,
        "chart_net_income_labels": chart_net_income_trend_labels,
        "num_paid_members": num_paid_members,
        "num_unpaid_members": num_unpaid_members,
        "total_members": total_members
    }

    return JSONResponse(content=financial_data)


# Create organization route
@router.post("/admin/organizations/", response_model=schemas.Organization, status_code=status.HTTP_201_CREATED)
async def create_organization_route(
    request: Request,
    organization: schemas.OrganizationCreate, # Use schema from schemas.py
    db: Session = Depends(get_db)
):
    """
    Creates a new organization in the database with an auto-generated custom palette and logo URL.
    This route is intended for initial setup and does NOT require admin authentication.
    """
    # Removed current_admin_id check to allow unauthenticated access for initial setup.

    # Check if the organization name already exists
    existing_organization = db.query(models.Organization).filter(
        models.Organization.name == organization.name
    ).first()
    if existing_organization:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with name '{organization.name}' already exists."
        )

    # NEW: Check if the primary course code already exists for an organization
    # This assumes you want a unique primary course code per organization.
    # If an organization can have multiple primary courses, you'd adjust this logic.
    existing_course_org = db.query(models.Organization).filter(
        models.Organization.primary_course_code == organization.primary_course_code
    ).first()
    if existing_course_org:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with primary course code '{organization.primary_course_code}' already exists."
        )

    try:
        # Generate custom_palette from theme_color
        # Ensure crud.generate_custom_palette is defined or imported
        custom_palette = crud.generate_custom_palette(organization.theme_color)

        # Generate a suggested filename for the logo based on the organization name
        suggested_filename = f"{organization.name.lower().replace(' ', '_')}_logo.png"
        logo_upload_path = f"/static/images/{suggested_filename}" # Keeping the path as provided by user

        new_org = models.Organization(
            name=organization.name,
            theme_color=organization.theme_color,
            primary_course_code=organization.primary_course_code, # NEW: Pass primary_course_code
            custom_palette=custom_palette,
            logo_url=logo_upload_path # Store the generated path
        )
        db.add(new_org)
        db.commit()
        db.refresh(new_org)

        # Inform the user about the required logo upload
        print(f"\n**Action Required:** Please upload the organization logo to your web server at the path: **{new_org.logo_url}**")
        print(f"The suggested filename for the image file is: **{suggested_filename}**")

        return new_org
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating organization: {e}"
        )
    
@router.post("/admin/admins/", response_model=schemas.Admin, status_code=status.HTTP_201_CREATED)
async def create_admin_user_route(
    request: Request,
    admin_data: schemas.AdminCreate, # Use schema from schemas.py
    db: Session = Depends(get_db)
):
    """
    Creates a new admin user in the database. This route is intended for initial setup
    and does NOT require existing admin authentication.
    """
    # Removed current_admin_id check to allow unauthenticated access for initial setup.

    # Check if the email already exists
    existing_admin = db.query(models.Admin).filter(models.Admin.email == admin_data.email).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Admin with email '{admin_data.email}' already exists."
        )
    try:
        hashed_password = bcrypt.hashpw(
            admin_data.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        new_admin = models.Admin(
            name=admin_data.name,
            email=admin_data.email,
            password=hashed_password,
            role="Admin", # Force role to Admin for this route
            position=admin_data.position # <--- THIS LINE WAS ADDED/CONFIRMED FOR FIX
        )
        db.add(new_admin)
        db.flush() # Flush to get admin_id before linking organization

        if admin_data.organization_id:
            organization = db.get(models.Organization, admin_data.organization_id)
            if organization:
                new_admin.organizations.append(organization)
            else:
                # Log a warning but don't fail the admin creation if org not found
                print(f"Warning: Organization with ID {admin_data.organization_id} not found. Admin created without organization link.")
        
        db.commit()
        db.refresh(new_admin)
        return new_admin
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating admin user: {e}"
        )


@router.put("/admin/organizations/{org_id}/theme", response_model=Dict[str, str])
async def update_organization_theme_color_route(
    request: Request,
    org_id: int,
    theme_update: schemas.OrganizationThemeUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates the theme color of an existing organization and regenerates its custom palette.
    Requires admin authentication.
    """
    current_admin_id = request.session.get("admin_id")
    if not current_admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated as admin",
        )

    try:
        organization = db.query(models.Organization).filter(models.Organization.id == org_id).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with ID {org_id} not found."
            )
        organization.theme_color = theme_update.new_theme_color
        # Use crud.generate_custom_palette
        organization.custom_palette = crud.generate_custom_palette(theme_update.new_theme_color)
        db.add(organization)
        db.commit()
        db.refresh(organization)
        return {"message": f"Organization '{organization.name}' (ID: {org_id}) theme color updated to {theme_update.new_theme_color} and palette regenerated successfully."}
    except HTTPException:
        raise # Re-raise HTTPExceptions
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating organization theme color: {e}"
        )

@router.put("/admin/organizations/{org_id}/logo", response_model=Dict[str, str])
async def update_organization_logo_route(
    request: Request,
    org_id: int,
    logo_file: UploadFile = File(...), # Expect a file upload
    db: Session = Depends(get_db)
):
    """
    Uploads and updates the logo for an existing organization.
    The logo will be named based on the organization's name and saved
    as /static/images/{organization_name_slug}_logo.{extension}.
    Requires admin authentication.
    """
    current_admin_id = request.session.get("admin_id")
    if not current_admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated as admin",
        )

    organization = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found."
        )

    # --- Implement your desired naming convention here ---
    # 1. Slugify the organization name
    organization_name_slug = organization.name.lower().replace(' ', '_')
    # Remove any characters that might cause issues in a URL or filename
    organization_name_slug = ''.join(e for e in organization_name_slug if e.isalnum() or e == '_')

    # 2. Get the actual file extension from the uploaded file
    file_extension = Path(logo_file.filename).suffix.lower()
    
    # 3. Ensure allowed image file types
    allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg']
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only {', '.join(allowed_extensions)} are allowed."
        )

    # 4. Construct the final suggested filename as requested
    suggested_filename = f"{organization_name_slug}_logo{file_extension}"
    
    # 5. Define the full server-side path where the file will be stored
    file_path = UPLOAD_BASE_DIRECTORY / suggested_filename

    try:
        # Save the uploaded file to the constructed path
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(logo_file.file, buffer)
        
        # Construct the URL path to serve the image, exactly as desired
        logo_url = f"/static/images/{suggested_filename}"

        # Update the organization's logo_url in the database
        organization.logo_url = logo_url
        db.add(organization)
        db.commit()
        db.refresh(organization)

        return {"message": f"Organization '{organization.name}' (ID: {org_id}) logo updated successfully to {logo_url}."}

    except HTTPException:
        raise # Re-raise HTTPExceptions
    except Exception as e:
        db.rollback()
        # Clean up the partially uploaded file if an error occurred after saving
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating organization logo: {e}"
        )


# PayMaya Create Payment Route
@router.post("/payments/paymaya/create", response_class=JSONResponse, name="paymaya_create_payment")
async def paymaya_create_payment(
    request: Request,
    payment_item_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """
    Creates a PayMaya payment request. Handles cases where the amount is
    provided directly or needs to be retrieved from a payment item.
    """
    public_api_key = "pk-Z0OSzLvIcOI2UIvDhdTGVVfRSSeiGStnceqwUE7n0Ah" # This should ideally be in environment variables
    encoded_key = base64.b64encode(f"{public_api_key}:".encode()).decode()
    url = "https://pg-sandbox.paymaya.com/checkout/v1/checkouts"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Basic {encoded_key}"
    }

    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")

    payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if not payment_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment item not found")

    payment_amount = payment_item.fee

    db_payment = crud.create_payment(db, amount=payment_amount, user_id=user_id)

    payload = {
        "totalAmount": {
            "currency": "PHP",
            "value": payment_amount
        },
        "requestReferenceNumber": f"your-unique-ref-{datetime.now().strftime('%Y%m%d%H%M%S')}-{db_payment.id}",
        "redirectUrl": {
            "success": f"http://127.0.0.1:8000/Success?paymentId={db_payment.id}&paymentItemId={payment_item_id}",
            "failure": f"http://127.0.0.1:8000/Failure?paymentId={db_payment.id}&paymentItemId={payment_item_id}",
            "cancel": f"http://127.0.0.1:8000/Cancel?paymentId={db_payment.id}&paymentItemId={payment_item_id}"
        },
        "metadata": {
            "pf": {
                "smi": "CVSU",
                "smn": "Undisputed",
                "mci": "Imus City",
                "mpc": "608",
                "mco": "PHL",
                "postalCode": "1554",
                "contactNo": "0211111111",
                "addressLine1": "Palico",
            },
            "subMerchantRequestReferenceNumber": "63d9934f9281"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        payment_data = response.json()
        paymaya_payment_id = payment_data.get("checkoutId")
        crud.update_payment(db, payment_id=db_payment.id, paymaya_payment_id=paymaya_payment_id)

        return payment_data

    except requests.exceptions.RequestException as e:
        crud.update_payment(db, payment_id=db_payment.id, status="failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PayMaya API error: {e.response.text if hasattr(e.response, 'text') else str(e)}"
        )

# Payment Success Callback Route
@router.get("/Success", response_class=HTMLResponse, name="payment_success")
async def payment_success(
    request: Request,
    paymentId: int = Query(...),
    paymentItemId: int = Query(...),
    db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if user_role == "user":
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.organization and user.organization.logo_url:
            logo_url = user.organization.logo_url

    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

    updated_payment = crud.update_payment(
        db, payment_id=payment.id, status="success", payment_item_id=paymentItemId
    )

    payment_item = crud.get_payment_item_by_id(db, payment_item_id=paymentItemId)
    if payment_item:
        updated_item = crud.mark_payment_item_as_paid(db, payment_item_id=paymentItemId)
        return templates.TemplateResponse(
            "student_dashboard/payment_success.html",
            {
                "request": request,
                "payment_id": payment.paymaya_payment_id,
                "payment_item_id": paymentItemId,
                "payment": payment,
                "payment_item": payment_item,
                "logo_url": logo_url,
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PaymentItem with ID {paymentItemId} not found."
        )

# Payment Failure Callback Route
@router.get("/Failure", response_class=HTMLResponse, name="payment_failure")
async def payment_failure(request: Request, paymentId: int = Query(...), db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if user_role == "user":
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.organization and user.organization.logo_url:
            logo_url = user.organization.logo_url

    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if payment:
        crud.update_payment(db, payment_id=payment.id, status="failed")
        payment_item = await _get_related_payment_item(db, payment.payment_item_id)
        return templates.TemplateResponse(
            "student_dashboard/payment_failure.html",
            {
                "request": request,
                "payment_id": payment.paymaya_payment_id,
                "payment_item": payment_item,
                "logo_url": logo_url,
            },
        )
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

# Payment Cancel Callback Route
@router.get("/Cancel", response_class=HTMLResponse, name="payment_cancel")
async def payment_cancel(request: Request, paymentId: int = Query(...), db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if user_role == "user":
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.organization and user.organization.logo_url:
            logo_url = user.organization.logo_url

    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if payment:
        crud.update_payment(db, payment_id=payment.id, status="cancelled")
        payment_item = await _get_related_payment_item(db, payment.payment_item_id)
        return templates.TemplateResponse(
            "student_dashboard/payment_cancel.html",
            {
                "request": request,
                "payment_id": payment.paymaya_payment_id,
                "payment_item": payment_item,
                "logo_url": logo_url,
            },
        )
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

# Helper function to get related PaymentItem
async def _get_related_payment_item(db: Session, payment_item_id: int | None) -> models.PaymentItem | None:
    """Helper function to fetch the PaymentItem if payment_item_id is available."""
    if payment_item_id:
        return crud.get_payment_item_by_id(db, payment_item_id=payment_item_id)
    return None

# Include the router in the main FastAPI app
app.include_router(router)

# Logout Route
@app.get("/logout", response_class=RedirectResponse, name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# Root Route (Index page)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Home Route (Dashboard for both Admin and User)
@app.get("/home", response_class=HTMLResponse, name="home")
async def home(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handles the /home route, displaying either the student or admin dashboard
    depending on the user's role stored in the session, and passes the
    organization's logo URL to the template. Bulletin posts are filtered by organization.
    """
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")
    user_role = request.session.get("user_role")

    current_year = "2025"
    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if not (user_id or admin_id) or not user_role:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Please log in to access this page."})

    # Determine the organization ID for the current user/admin
    current_org_id = None
    try:
        current_org_id = await get_user_organization_id(request, db)
    except HTTPException:
        # If no organization found, posts/events will be empty
        pass

    if user_role == "Admin":
        admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
        if admin and admin.organizations:
            first_org = admin.organizations[0]
            if first_org.logo_url:
                logo_url = first_org.logo_url
        
        latest_bulletin_posts = []
        if current_org_id:
            latest_bulletin_posts = (
                db.query(models.BulletinBoard)
                .join(models.Admin)
                .join(models.Admin.organizations)
                .filter(models.Organization.id == current_org_id)
                .order_by(models.BulletinBoard.created_at.desc())
                .limit(5)
                .all()
            )
        return templates.TemplateResponse(
            "admin_dashboard/home.html",
            {
                "request": request,
                "year": current_year,
                "bulletin_posts": latest_bulletin_posts,
                "logo_url": logo_url,
            },
        )
    elif user_role == "user":
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.organization and user.organization.logo_url:
            logo_url = user.organization.logo_url
        
        latest_bulletin_posts = []
        if current_org_id:
            latest_bulletin_posts = (
                db.query(models.BulletinBoard)
                .join(models.Admin)
                .join(models.Admin.organizations)
                .filter(models.Organization.id == current_org_id)
                .order_by(models.BulletinBoard.created_at.desc())
                .limit(5)
                .all()
            )
        temporary_faqs = [
            {
                "question": "What is the schedule for student orientation?",
                "answer": "The student orientation will be held on August 20, 2025, from 9:00 AM to 12:00 PM in the main auditorium.",
            },
            {
                "question": "How do I access the online learning platform?",
                "answer": "You can access the online learning platform by visiting our website and clicking on the 'Student Portal' link. Use your student ID and password to log in.",
            },
            {
                "question": "Who should I contact for academic advising?",
                "answer": "For academic advising, please contact the Dean's office of your respective faculty. You can find their contact information on the university website under the 'Academics' section.",
            },
        ]
        return templates.TemplateResponse(
            "student_dashboard/home.html",
            {
                "request": request,
                "year": current_year,
                "bulletin_posts": latest_bulletin_posts,
                "faqs": temporary_faqs,
                "logo_url": logo_url,
            },
        )
    else:
        raise HTTPException(status_code=403, detail="Invalid user role")

# Bulletin Board Page Route (for users)
@app.get("/BulletinBoard", response_class=HTMLResponse, name="bulletin_board")
async def bulletin_board(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    if not user_id: # Ensure user is authenticated
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    user_org_id = None
    try:
        user_org_id = await get_user_organization_id(request, db)
    except HTTPException:
        # If user is not associated with an organization, they won't see any posts
        pass 

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user and user.organization and user.organization.logo_url:
        logo_url = user.organization.logo_url

    posts = []
    if user_org_id:
        posts = db.query(models.BulletinBoard).join(models.Admin).join(models.Admin.organizations).filter(
            models.Organization.id == user_org_id
        ).order_by(models.BulletinBoard.created_at.desc()).all()

    hearted_posts = [] # This needs to be populated based on user's hearted posts if implemented
    return templates.TemplateResponse(
        "student_dashboard/bulletin_board.html",
        {"request": request, "year": "2025", "posts": posts, "hearted_posts": hearted_posts, "logo_url": logo_url}
    )

# Events Page Route (for users)
@app.get("/Events", response_class=HTMLResponse, name="events")
async def events(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url
    if user_role == "user":
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.organization and user.organization.logo_url:
            logo_url = user.organization.logo_url

    user_org_id = None
    try:
        user_org_id = await get_user_organization_id(request, db)
    except HTTPException:
        pass # If no organization found, events will be empty

    events = []
    if user_org_id:
        events = db.query(models.Event).join(models.Admin).join(models.Admin.organizations).filter(
            models.Organization.id == user_org_id
        ).order_by(models.Event.created_at.desc()).all()

    return templates.TemplateResponse(
        "student_dashboard/events.html", {"request": request, "year": "2025", "events": events, "logo_url": logo_url}
    )

# Payments Page Route (for users)
@app.get("/Payments", response_class=HTMLResponse, name="payments")
async def payments(request: Request, db: Session = Depends(get_db)):
    """
    Displays payment items for the authenticated user, categorized into past due and unpaid upcoming.
    """
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if user_role == "user":
        user_for_logo = db.query(models.User).filter(models.User.id == user_id).first()
        if user_for_logo and user_for_logo.organization and user_for_logo.organization.logo_url:
            logo_url = user_for_logo.organization.logo_url

    user_identifier = request.session.get("user_id") or request.session.get("admin_id")

    current_user = None

    if not user_identifier:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    current_user = db.query(models.User).filter(models.User.id == user_identifier).first()
    if not current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        payment_items = (
            db.query(models.PaymentItem)
            .filter(models.PaymentItem.user_id == user_identifier)
            .filter(models.PaymentItem.is_not_responsible == False)
            .order_by(models.PaymentItem.academic_year)
            .all()
        )

        past_due_items = []
        unpaid_upcoming_items = []

        for item in payment_items:
            if not item.is_paid:
                if item.is_past_due:
                    past_due_items.append(item)
                else:
                    unpaid_upcoming_items.append(item)

        return templates.TemplateResponse(
            "student_dashboard/payments.html",
            {
                "request": request,
                "past_due_items": past_due_items,
                "unpaid_upcoming_items": unpaid_upcoming_items,
                "current_user": current_user,
                "logo_url": logo_url,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payment information.",
        )

# Financial Statement Page Route (for users)
@app.get("/FinancialStatement", response_class=HTMLResponse, name="financial_statement")
async def financial_statement(request: Request, db: Session = Depends(get_db)):
    user_id: int | None = request.session.get("user_id")
    user_role: str | None = request.session.get("user_role")

    if not user_id:
        return RedirectResponse(url="/login", status_code=302)

    user_obj: models.User | None = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_obj:
        request.session.pop("user_id", None)
        request.session.pop("user_role", None)
        return RedirectResponse(url="/login", status_code=302)

    default_logo_url: str = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url: str = default_logo_url
    if user_obj.organization and user_obj.organization.logo_url:
        logo_url = user_obj.organization.logo_url

    today: date = date.today()
    current_year: int = today.year

    all_user_payment_items = db.query(models.PaymentItem).filter(models.PaymentItem.user_id == user_id).all()
    paid_user_payment_items = [item for item in all_user_payment_items if item.is_paid]
    unpaid_user_payment_items = [item for item in all_user_payment_items if not item.is_paid]

    total_revenue: float = sum(item.fee for item in paid_user_payment_items)
    total_outstanding_fees: float = sum(item.fee for item in unpaid_user_payment_items)
    total_past_due_fees: float = sum(item.fee for item in unpaid_user_payment_items if item.due_date and item.due_date < today)

    collected_fees_by_category: defaultdict[str, float] = defaultdict(float)
    for item in paid_user_payment_items:
        category_name = "Miscellaneous Fees"
        if item.academic_year and item.semester:
            category_name = f"AY {item.academic_year} - {item.semester} Fees"
        elif item.academic_year:
            category_name = f"AY {item.academic_year} Fees"
        elif item.semester:
            category_name = f"{item.semester} Semester Fees"
        collected_fees_by_category[category_name] += item.fee
    collected_fees_list = [{"category": k, "amount": v} for k, v in collected_fees_by_category.items()]

    outstanding_fees_by_category: defaultdict[str, float] = defaultdict(float)
    for item in unpaid_user_payment_items:
        category_name = "Miscellaneous Fees"
        if item.academic_year and item.semester:
            category_name = f"AY {item.academic_year} - {item.semester} Fees"
        elif item.academic_year:
            category_name = f"AY {item.academic_year} Fees"
        elif item.semester:
            category_name = f"{item.semester} Semester Fees"
        outstanding_fees_by_category[category_name] += item.fee
    outstanding_fees_list = [{"category": k, "amount": v} for k, v in outstanding_fees_by_category.items()]

    total_expenses: float = 0.00
    expenses_by_category: list = []

    current_balance: float = total_revenue - total_expenses
    net_income: float = total_revenue - total_expenses

    financial_summary_items: list[dict[str, float | str]] = []
    for item in collected_fees_list:
        financial_summary_items.append({
            "event_item": item["category"],
            "inflows": item["amount"],
            "outflows": 0.00
        })

    monthly_data: dict[str, dict[str, float]] = {}
    months_full = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    user_payments_by_month_current_year: defaultdict[str, float] = defaultdict(float)
    for item in paid_user_payment_items:
        if item.created_at and item.created_at.year == current_year:
            month_index = item.created_at.month - 1
            user_payments_by_month_current_year[months_full[month_index].lower()] += item.fee

    for month_name_lower in [m.lower() for m in months_full]:
        inflows_this_month = user_payments_by_month_current_year.get(month_name_lower, 0.00)
        monthly_data[month_name_lower] = {
            "starting_balance": 0.00,
            "inflows": inflows_this_month,
            "outflows": 0.00,
            "ending_balance": inflows_this_month
        }

    current_date_str: str = today.strftime("%B %d, %Y")

    financial_data: dict = {
        "total_revenue": total_revenue,
        "total_outstanding_fees": total_outstanding_fees,
        "total_past_due_fees": total_past_due_fees,
        "total_expenses": total_expenses,
        "current_balance": current_balance,
        "net_income": net_income,
        "collected_fees_by_category": collected_fees_list,
        "outstanding_fees_by_category": outstanding_fees_list,
        "expenses_by_category": expenses_by_category,
        "financial_summary_items": financial_summary_items,
        "monthly_data": monthly_data,
        "current_date": current_date_str
    }

    return templates.TemplateResponse(
        "student_dashboard/financial_statement.html",
        {
            "request": request,
            "year": current_year,
            "logo_url": logo_url,
            "financial_data": financial_data
        }
    )


# It receives month and year as query parameters.
@app.get("/student_dashboard/detailed_monthly_report_page", response_class=HTMLResponse)
async def detailed_monthly_report_page(
    request: Request,
    month: str = Query(...),
    year: int = Query(...),
    db: Session = Depends(get_db)
):
    user_id: int | None = request.session.get("user_id")
    user_role: str | None = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if user_role == "user" and user_id:
        user_for_logo = db.query(models.User).filter(models.User.id == user_id).first()
        if user_for_logo and user_for_logo.organization and user_for_logo.organization.logo_url:
            logo_url = user_for_logo.organization.logo_url

    return templates.TemplateResponse(
        "student_dashboard/detailed_monthly_report.html",
        {"request": request, "month": month, "year": year, "logo_url": logo_url}
    )


@app.get("/api/detailed_monthly_report", response_class=JSONResponse)
async def get_detailed_monthly_report_json(
    request: Request,
    month: str = Query(...),
    year: int = Query(...),
    db: Session = Depends(get_db)
):
    user_id: int | None = request.session.get("user_id")
    user_role: str | None = request.session.get("user_role")

    if not user_id or user_role != "user":
        raise HTTPException(status_code=403, detail="Not authenticated or authorized to view this data.")

    user_obj: models.User | None = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found.")

    month_name_lower: str = month.lower()
    month_map: dict[str, int] = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    month_number: int | None = month_map.get(month_name_lower)

    if month_number is None:
        raise HTTPException(status_code=400, detail="Invalid month specified.")

    report_year: int = year
    start_date: date = date(report_year, month_number, 1)
    end_of_month_day: int = calendar.monthrange(report_year, month_number)[1]
    end_date: date = date(report_year, month_number, end_of_month_day)

    all_payment_items: list[models.PaymentItem] = db.query(models.PaymentItem).filter(
        models.PaymentItem.user_id == user_id,
        models.PaymentItem.created_at <= (end_date + timedelta(days=1))
    ).order_by(models.PaymentItem.created_at).all()

    transactions_for_report_month: list[dict] = []
    total_inflows_month: float = 0.00
    total_outflows_month: float = 0.00
    total_outstanding_month: float = 0.00
    total_past_due_month: float = 0.00
    
    current_running_balance: float = 0.00 

    for item in all_payment_items:
        amount_inflow: float = 0.00
        amount_outflow: float = 0.00
        status: str = ""
        description: str = "Fee Payment"

        if item.academic_year and item.semester:
            description = f"AY {item.academic_year} - {item.semester} Fee"
        elif item.academic_year:
            description = f"AY {item.academic_year} Fee"
        elif item.semester:
            description = f"{item.semester} Semester Fee"

        if item.is_paid:
            amount_inflow = item.fee
            status = "Paid"
        else:
            status = "Unpaid"
            if item.due_date and item.due_date < date.today():
                status = "Past Due"
                
        current_running_balance += amount_inflow 
        current_running_balance -= amount_outflow 

        if start_date <= item.created_at <= end_date:
            total_inflows_month += amount_inflow
            total_outflows_month += amount_outflow
            if not item.is_paid:
                total_outstanding_month += item.fee
                if item.due_date and item.due_date < date.today():
                    total_past_due_month += item.fee

            transaction_data = {
                "date": item.created_at.strftime("%Y-%m-%d") if item.created_at else "N/A",
                "description": description,
                "inflow": amount_inflow,
                "outflow": amount_outflow,
                "status": status,
                "original_fee": item.fee,
                "running_balance": current_running_balance 
            }
            transactions_for_report_month.append(transaction_data)
    
    transactions_for_report_month.sort(key=lambda x: x['date'])

    ending_balance_month_footer_sum: float = total_inflows_month - total_outflows_month

    response_content = {
        "month_name": month.capitalize(),
        "year": report_year,
        "current_date": date.today().strftime("%B %d, %Y"),
        "starting_balance": 0.00,
        "total_inflows": total_inflows_month,
        "total_outflows": total_outflows_month,
        "total_outstanding": total_outstanding_month,
        "total_past_due": total_past_due_month,
        "ending_balance": ending_balance_month_footer_sum, 
        "transactions": transactions_for_report_month,
        "user_name": f"{user_obj.first_name} {user_obj.last_name}" if user_obj else "N/A",
        "total_all_original_fees": sum(item.fee for item in all_payment_items)
    }

    return JSONResponse(content=response_content)


# Settings Page Route (for users)
@app.get("/Settings", response_class=HTMLResponse, name="settings")
async def settings(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if user_role == "user":
        # Ensure that the organization relationship is eager-loaded or handled if needed for logo
        user_for_logo = db.query(models.User).filter(models.User.id == user_id).first()
        if user_for_logo and user_for_logo.organization and user_for_logo.organization.logo_url:
            logo_url = user_for_logo.organization.logo_url
            
    current_user_id = request.session.get("user_id")
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    # Ensure user is loaded to get is_verified status
    user = db.query(models.User).filter(models.User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # --- DEBUGGING STEP: Print the value of user.is_verified here ---
    print(f"DEBUG: In /Settings route, user.is_verified for user {user.id} is: {user.is_verified}")
    # --- END DEBUGGING STEP ---

    formatted_birthdate = ""
    if user.birthdate:
        try:
            birthdate_object = datetime.strptime(user.birthdate, "%Y-%m-%d %H:%M:%S")
            formatted_birthdate = birthdate_object.strftime("%Y-%m-%d")
        except ValueError:
            try:
                birthdate_object = datetime.strptime(user.birthdate, "%Y-%m-%d")
                formatted_birthdate = birthdate_object.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    birthdate_object = datetime.strptime(user.birthdate, "%m/%d/%Y")
                    formatted_birthdate = birthdate_object.strftime("%Y-%m-%d")
                except ValueError:
                    formatted_birthdate = user.birthdate # Fallback if no known format matches

    # Set the verification_status for the template
    user.verification_status = "Verified" if user.is_verified else "Not Verified"

    return templates.TemplateResponse(
        "student_dashboard/settings.html",
        {"request": request, "year": "2025", "user": user, "formatted_birthdate": formatted_birthdate, "logo_url": logo_url},
    )


# Get Organizations API Route
@app.get("/api/organizations/", response_model=List[schemas.Organization])
async def get_organizations(db: Session = Depends(get_db)):
    """
    Retrieves a list of all organizations from the database.
    """
    organizations = db.query(models.Organization).all()
    return organizations

# User Signup API Route
@app.post("/api/signup/")
async def signup(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    request: Request = None,
):
    db_user = crud.get_user(db, identifier=user.student_number)
    if db_user:
        raise HTTPException(status_code=400, detail="Student number already registered")

    db_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_name_combination = db.query(models.User).filter(
        models.User.first_name == user.first_name,
        models.User.last_name == user.last_name,
    ).first()
    if db_name_combination:
        raise HTTPException(status_code=400, detail="First and last name combination already registered")

    new_user = crud.create_user(db=db, user=user)

    current_year = date.today().year
    semester = "1st"
    payment_items = []
    start_date = date(current_year, 2, 28) # Arbitrary start date for payment item generation
    for i in range(8): # Generate 8 payment items (4 years, 2 semesters each)
        academic_year = f"{current_year}-{current_year + 1}"
        due_date = start_date + timedelta(days=i * 6 * 30) # Roughly every 6 months
        year_level_applicable = (i // 2) + 1
        payment_items.append(
            {
                "user_id": new_user.id,
                "academic_year": academic_year,
                "semester": semester,
                "fee": 100.00, # Default fee
                "description": f"Payment Item {i+1}",
                "due_date": due_date,
                "year_level_applicable": year_level_applicable,
            }
        )
        if semester == "1st":
            semester = "2nd"
        else:
            semester = "1st"
            current_year += 1
            start_date = date(current_year, 2, 28) # Reset start date for new academic year

    for payment_data in payment_items:
        crud.add_payment_item(
            db=db,
            user_id=payment_data["user_id"],
            academic_year=payment_data["academic_year"],
            semester=payment_data["semester"],
            fee=payment_data["fee"],
            due_date=payment_data["due_date"],
            year_level_applicable=payment_data["year_level_applicable"],
        )

    return {"message": "User created successfully", "user_id": new_user.id}

@app.get("/api/user/{user_id}", response_model=schemas.User)
async def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, identifier=str(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/get_user_data", response_model=schemas.UserDataResponse)
async def get_user_data(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")

    current_user_obj = None
    organization_data = None
    first_name = None
    profile_picture = None
    is_verified_status = None # Initialize for user's verification status

    if user_id:
        current_user_obj = db.query(models.User).filter(models.User.id == user_id).first()
        if current_user_obj:
            first_name = current_user_obj.first_name
            profile_picture = current_user_obj.profile_picture
            is_verified_status = current_user_obj.is_verified # Get user's is_verified status
            logger.info(f"User ID {user_id} verification status: {is_verified_status}")
            if current_user_obj.organization:
                organization_data = schemas.Organization(
                    id=current_user_obj.organization.id,
                    name=current_user_obj.organization.name,
                    theme_color=current_user_obj.organization.theme_color,
                    custom_palette=current_user_obj.organization.custom_palette,
                    logo_url=current_user_obj.organization.logo_url
                )

    elif admin_id:
        current_user_obj = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
        if current_user_obj:
            first_name = current_user_obj.name 
            profile_picture = None # Admins might not have profile pictures
            # Admins don't have is_verified, so this remains None for them
            
            if current_user_obj.organizations:
                first_org = current_user_obj.organizations[0]
                organization_data = schemas.Organization(
                    id=first_org.id,
                    name=first_org.name,
                    theme_color=first_org.theme_color,
                    custom_palette=first_org.custom_palette,
                    logo_url=first_org.logo_url
                )

    if not current_user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user/admin not found in database for provided session ID."
        )
    
    if not user_id and not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authenticated user or admin ID found in session."
        )

    return schemas.UserDataResponse(
        first_name=first_name,
        profile_picture=profile_picture,
        organization=organization_data,
        is_verified=is_verified_status # Pass the is_verified status in the response
    )

@app.post("/api/login/")
async def login(request: Request, form_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Login endpoint that handles both user and admin login.
    Admins log in using their email, and users with their student number.
    """
    user = crud.authenticate_user(db, form_data.identifier, form_data.password)

    if user:
        request.session["user_id"] = user.id
        request.session["user_role"] = getattr(user, 'role', 'user') # Default to 'user' if role not explicitly set
        return {
            "message": "User login successful",
            "user_id": user.id,
            "user_role": request.session["user_role"],
        }
    else:
        admin = crud.authenticate_admin_by_email(db, form_data.identifier, form_data.password)
        if admin:
            request.session["admin_id"] = admin.admin_id
            request.session["user_role"] = admin.role
            return {
                "message": "Admin login successful",
                "admin_id": admin.admin_id,
                "user_role": admin.role,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

# Helper function to get user's organization ID
async def get_user_organization_id(request: Request, db: Session) -> int:
    """
    Retrieves the organization ID of the currently authenticated user or admin.
    Raises HTTPException if not authenticated or not associated with an organization.
    """
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")
    organization_id = None

    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.organization_id:
            organization_id = user.organization_id
    elif admin_id:
        admin = db.query(models.Admin).options(joinedload(models.Admin.organizations)).filter(models.Admin.admin_id == admin_id).first()
        if admin and admin.organizations:
            organization_id = admin.organizations[0].id

    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User/Admin not associated with an organization or not authenticated."
        )
    return organization_id

# Helper function to get entity's organization ID (e.g., from an admin who created a post/event)
def get_entity_organization_id(db: Session, admin_id: int) -> int:
    """
    Retrieves the organization ID associated with a given admin ID.
    Raises HTTPException if admin not found or not associated with an organization.
    """
    admin = db.query(models.Admin).options(joinedload(models.Admin.organizations)).filter(models.Admin.admin_id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin for this entity not found.")
    if not admin.organizations:
        raise HTTPException(status_code=500, detail="Admin is not associated with any organization.")
    return admin.organizations[0].id

# Heart Post API Route
@app.post("/bulletin/heart/{post_id}")
async def heart_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    action: str = Form(...)
):
    user_org_id = await get_user_organization_id(request, db)

    post = db.query(models.BulletinBoard).options(joinedload(models.BulletinBoard.admin)).filter(models.BulletinBoard.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post_org_id = get_entity_organization_id(db, post.admin_id)

    if post_org_id != user_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only interact with posts from your own organization."
        )

    if action == 'heart':
        post.heart_count += 1
    elif action == 'unheart' and post.heart_count > 0:
        post.heart_count -= 1
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'heart' or 'unheart'.")

    db.commit()
    db.refresh(post)
    return {"heart_count": post.heart_count}


@app.post("/Events/join/{event_id}")
async def join_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    user_org_id = await get_user_organization_id(request, db)

    event = db.query(models.Event).options(
        joinedload(models.Event.participants),
        joinedload(models.Event.admin)
    ).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event_org_id = get_entity_organization_id(db, event.admin_id)

    if event_org_id != user_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only join events from your own organization."
        )

    current_user_id = request.session.get("user_id")
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated."
        )
    user = db.query(models.User).filter(models.User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user in event.participants:
        raise HTTPException(status_code=400, detail="You are already joined in this event.")

    if event.joined_count() >= event.max_participants:
        raise HTTPException(status_code=400, detail="This event is full.")

    event.participants.append(user)
    db.commit()
    return RedirectResponse(url="/Events", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/Events/leave/{event_id}")
async def leave_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    user_org_id = await get_user_organization_id(request, db)

    event = db.query(models.Event).options(
        joinedload(models.Event.participants),
        joinedload(models.Event.admin)
    ).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event_org_id = get_entity_organization_id(db, event.admin_id)

    if event_org_id != user_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only leave events from your own organization."
        )

    current_user_id = request.session.get("user_id")
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated."
        )
    user = db.query(models.User).filter(models.User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user not in event.participants:
        raise HTTPException(status_code=400, detail="You are not joined in this event.")

    event.participants.remove(user)
    db.commit()
    return RedirectResponse(url="/Events", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/api/events/upcoming_summary")
async def get_upcoming_events_summary(request: Request, db: Session = Depends(get_db)):
    user_org_id = await get_user_organization_id(request, db)

    now = datetime.now()
    
    upcoming_events_with_admins = db.query(models.Event).options(
        joinedload(models.Event.admin).joinedload(models.Admin.organizations)
    ).filter(models.Event.date >= now).order_by(models.Event.date).all()

    filtered_events = []
    for event in upcoming_events_with_admins:
        if event.admin and event.admin.organizations:
            admin_org_ids = [org.id for org in event.admin.organizations]
            if user_org_id in admin_org_ids:
                filtered_events.append(event)
    
    limited_events = filtered_events[:5] # Limit to 5 upcoming events

    return [{"title": event.title, "date": event.date.isoformat(), "location": event.location,
             "classification": event.classification} for event in limited_events]

# Helper function to generate email
def generate_email(first_name: str, last_name: str) -> str:
    """Generates the email address based on the provided format."""
    if first_name and last_name:
        return f"ic.{first_name.lower()}.{last_name.lower()}@cvsu.edu.ph"
    return None

# Update Profile API Route
@app.post("/api/profile/update/")
async def update_profile(
    request: Request,
    student_number: Optional[str] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    birthdate: Optional[datetime] = Form(None),
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
    """
    Updates the user's profile information, including handling the registration form file upload
    and extracting data from it. It also updates the user's payment items, setting the academic year
    and due date dynamically based on the user's year level.
    """
    current_user_id = request.session.get("user_id")
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        user = (
            db.query(models.User)
            .filter(models.User.id == current_user_id)
            .options(selectinload(models.User.payment_items))
            .first()
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while retrieving user",
        )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Helper function to delete old files
    def delete_file(file_path: Optional[str]):
        if file_path:
            full_path = os.path.join(
                "..", "frontend", file_path.lstrip("/")
            )
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    # Log the error but don't raise an HTTPException, as it's not critical for the main update
                    print(f"Error deleting old file {full_path}: {e}")
            else:
                print(f"File not found for deletion: {full_path}")

    # Update user fields if provided in the form
    if student_number is not None:
        user.student_number = student_number
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if email is not None:
        user.email = email
    if name is not None:
        user.name = name
    if address is not None:
        user.address = address
    if birthdate is not None:
        user.birthdate = birthdate
    if sex is not None:
        user.sex = sex
    if contact is not None:
        user.contact = contact
    if course is not None:
        user.course = course
    if semester is not None:
        user.semester = semester
    if campus is not None:
        user.campus = campus
    if school_year is not None:
        user.school_year = school_year
    if year_level is not None:
        user.year_level = year_level
    if section is not None:
        user.section = section
    if guardian_name is not None:
        user.guardian_name = guardian_name
    if guardian_contact is not None:
        user.guardian_contact = guardian_contact
    if is_verified is not None:
        user.is_verified = is_verified

    # Handle registration form upload (PDF)
    if registration_form:
        if registration_form.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type for registration form. Only PDF is allowed.",
            )

        try:
            # Delete old registration form if exists
            delete_file(user.registration_form)

            pdf_content = await registration_form.read()
            filename = generate_secure_filename(registration_form.filename)
            pdf_file_path = os.path.join(
                "..",
                "frontend",
                "static",
                "documents",
                "registration_forms",
                filename,
            )
            os.makedirs(os.path.dirname(pdf_file_path), exist_ok=True)
            with open(pdf_file_path, "wb") as f:
                f.write(pdf_content)
            user.registration_form = (
                f"/static/documents/registration_forms/{filename}"
            )

            # Extract info from PDF and update user fields if not already provided by form
            extracted_text = extract_text_from_pdf(pdf_file_path)
            student_info = extract_student_info(extracted_text)

            if name is None and "name" in student_info and student_info["name"]:
                user.name = student_info["name"]
            if course is None and "course" in student_info and student_info["course"]:
                user.course = student_info["course"]
            if (
                year_level is None
                and "year_level" in student_info
                and student_info["year_level"]
            ):
                user.year_level = student_info["year_level"]
            if section is None and "section" in student_info and student_info["section"]:
                user.section = student_info["section"]
            if campus is None and "campus" in student_info and student_info["campus"]:
                user.campus = student_info["campus"]
            if (
                semester is None
                and "semester" in student_info
                and student_info["semester"]
            ):
                user.semester = student_info["semester"]
            if (
                school_year is None
                and "school_year" in student_info
                and student_info["school_year"]
            ):
                user.school_year = student_info["school_year"]
            if address is None and "address" in student_info and student_info["address"]:
                user.address = student_info["address"]
            if (
                student_number is None
                and "student_number" in student_info
                and student_info["student_number"]
            ):
                user.student_number = student_info["student_number"]

            # Further process name to extract first and last name for email generation
            if "name" in student_info and student_info["name"]:
                name_str = student_info["name"].strip()
                # Remove middle initials like "A." or "B."
                name_str = re.sub(r"\s+[a-zA-Z]\.\s+", " ", name_str)
                name_str = re.sub(r"\s+[a-zA-Z]\.$", "", name_str)
                name_str = re.sub(r"\s+[a-zA-Z]\.(?=\s)", "", name_str)
                name_str = re.sub(r"\s+", " ", name_str).strip() # Normalize spaces
                name_parts = name_str.split()
                if len(name_parts) >= 2:
                    user.first_name = " ".join(name_parts[:-1]).title()
                    user.last_name = name_parts[-1].title()
                elif len(name_parts) == 1:
                    user.first_name = name_parts[0].title()
                    user.last_name = "" # No last name if only one part

            # Generate email if first and last name are available
            if user.first_name and user.last_name:
                user.email = generate_email(
                    user.first_name.replace(" ", ""), user.last_name
                )
            
            # Set is_verified to True after successful registration form processing
            user.is_verified = True

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process registration form: {e}",
            )

    # Handle profile picture upload
    if profilePicture:
        try:
            # Delete old profile picture if exists
            delete_file(user.profile_picture)

            image_content = await profilePicture.read()
            max_image_size_bytes = 2 * 1024 * 1024 # 2 MB limit
            if len(image_content) > max_image_size_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Image size too large. Maximum allowed size is {max_image_size_bytes} bytes.",
                )
            # Verify image content
            img = Image.open(BytesIO(image_content))
            img.verify()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image file: {e}",
            )

        filename = generate_secure_filename(profilePicture.filename)
        file_path = os.path.join(
            "..",
            "frontend",
            "static",
            "images",
            "profile_pictures",
            filename,
        )
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(image_content)
            user.profile_picture = (
                f"/static/images/profile_pictures/{filename}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save image: {e}",
            )

    # Regenerate email if first name and last name are updated and email was not explicitly provided
    if first_name and last_name and not email:
        email = generate_email(first_name, last_name)
        user.email = email

    # Update payment items with revised logic based on current date and user's year level
    current_date = datetime.now()

    # Map year level string to integer for calculation
    year_level_str = str(user.year_level).lower().strip()
    year_level_mapping = {
        "1st": 1,
        "first": 1,
        "1": 1,
        "2nd": 2,
        "second": 2,
        "2": 2,
        "3rd": 3,
        "third": 3,
        "3": 3,
        "4th": 4,
        "fourth": 4,
        "4": 4,
    }

    student_year = year_level_mapping.get(year_level_str, 1) # Default to 1st year if not found

    # Calculate the starting academic year for the student based on their current year level
    first_academic_year_start = current_date.year - (student_year - 1)
    if current_date.month < 6: # If current month is before June, the academic year started last year
        first_academic_year_start -= 1

    # This variable is not directly used in the loop, but kept for context if needed
    first_academic_year = f"{first_academic_year_start}-{first_academic_year_start + 1}"

    payment_items = user.payment_items # Get existing payment items for the user

    # Iterate through payment items to update academic year and due dates
    for i, item in enumerate(payment_items):
        semester_offset = i // 2 # 0 for 1st/2nd semester of year 1, 1 for year 2, etc.
        item_academic_year_start = first_academic_year_start + semester_offset
        item.academic_year = f"{item_academic_year_start}-{item_academic_year_start + 1}"

        # Determine due date based on semester (even index for 2nd semester, odd for 1st semester of next year)
        due_date_year = int(item.academic_year.split("-")[1]) # Use the end year of the academic year
        if (i % 2) == 0: # First payment item of the academic year (e.g., 2nd semester of current academic year)
            due_date = datetime(due_date_year, 2, 1) + timedelta( # February 1st
                days=7 - datetime(due_date_year, 2, 1).weekday() # Adjust to next Monday
            )
        else: # Second payment item of the academic year (e.g., 1st semester of next academic year)
            due_date = datetime(due_date_year, 7, 1) + timedelta( # July 1st
                days=7 - datetime(due_date_year, 7, 1).weekday() # Adjust to next Monday
            )
        item.due_date = due_date.date() # Store only the date part

        # Set is_past_due flag
        if item.due_date and item.due_date < current_date.date() and not item.is_paid:
            item.is_past_due = True
        else:
            item.is_past_due = False

        db.add(item) # Add the modified item to the session
        db.flush() # Flush to ensure changes are tracked before commit

    try:
        db.commit() # Commit all changes to the database
        db.refresh(user) # Refresh the user object to get the latest data

        # Add the verification_status attribute to the user object for frontend consumption
        user.verification_status = "Verified" if user.is_verified else "Not Verified"

        return {"message": "Profile updated successfully", "user": user}
    except Exception as e:
        db.rollback() # Rollback in case of any error during commit
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile in database: {e}",
        )
