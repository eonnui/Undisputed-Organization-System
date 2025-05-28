from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Form, APIRouter, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, and_
from . import models, schemas, crud # Assuming models, schemas, and crud are in the same package
from .database import SessionLocal, engine # Assuming database.py is in the same package
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
from io import BytesIO
from PIL import Image
import os
import secrets
import re
import requests
import base64
import logging
import bcrypt
import shutil

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
@router.get("/admin/financial_statement", response_class=HTMLResponse, name="admin_financial_statement")
async def admin_financial_statement(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url
    if admin_id:
        admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
        if admin and admin.organizations:
            first_org = admin.organizations[0]
            if first_org.logo_url:
                logo_url = first_org.logo_url

    return templates.TemplateResponse(
        "admin_dashboard/admin_financial_statement.html",
        {
            "request": request,
            "year": "2025",
            "logo_url": logo_url,
        },
    )

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
    try:
        # Generate custom_palette from theme_color
        custom_palette = crud.generate_custom_palette(organization.theme_color)
        
        # Generate a suggested filename for the logo based on the organization name
        suggested_filename = f"{organization.name.lower().replace(' ', '_')}_logo.png"
        logo_upload_path = f"/static/images/{suggested_filename}" # Keeping the path as provided by user

        new_org = models.Organization(
            name=organization.name,
            theme_color=organization.theme_color,
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
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if user_role == "user":
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.organization and user.organization.logo_url:
            logo_url = user.organization.logo_url

    return templates.TemplateResponse("student_dashboard/financial_statement.html", {"request": request, "year": "2025", "logo_url": logo_url})

# Settings Page Route (for users)
@app.get("/Settings", response_class=HTMLResponse, name="settings")
async def settings(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if user_role == "user":
        user_for_logo = db.query(models.User).filter(models.User.id == user_id).first()
        if user_for_logo and user_for_logo.organization and user_for_logo.organization.logo_url:
            logo_url = user_for_logo.organization.logo_url
            
    current_user_id = request.session.get("user_id")
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = db.query(models.User).filter(models.User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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

    if user_id:
        current_user_obj = db.query(models.User).filter(models.User.id == user_id).first()
        if current_user_obj:
            first_name = current_user_obj.first_name
            profile_picture = current_user_obj.profile_picture
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
        organization=organization_data
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
    and extracting data from it.  It also updates the user's payment items, setting the academic year
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
        return {"message": "Profile updated successfully", "user": user}
    except Exception as e:
        db.rollback() # Rollback in case of any error during commit
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile in database: {e}",
        )
