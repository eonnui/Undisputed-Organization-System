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
from typing import List, Optional, Dict
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
import random
from dateutil.relativedelta import relativedelta

from starlette.middleware.sessions import SessionMiddleware

from .text import extract_text_from_pdf, extract_student_info
import logging

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

BASE_DIR = Path(__file__).resolve().parent.parent.parent

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "frontend" / "static"),
    name="static"
)

router = APIRouter()

templates = Jinja2Templates(directory=BASE_DIR / "frontend" / "templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_secure_filename(original_filename: str) -> str:
    _, file_extension = os.path.splitext(original_filename)
    random_prefix = secrets.token_hex(16)
    return f"{random_prefix}{file_extension}"

UPLOAD_BASE_DIRECTORY = Path(__file__).parent.parent.parent / "frontend" / "static" / "images"
UPLOAD_BASE_DIRECTORY.mkdir(parents=True, exist_ok=True)

@router.get("/get_user_notifications", response_class=JSONResponse)
async def get_notifications_route(
    request: Request,
    db: Session = Depends(get_db),
    organization_id: Optional[int] = Query(None, description="Optional organization ID to filter notifications.")
) -> JSONResponse:
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")

    print(f"DEBUG: User ID from session: {user_id}")
    print(f"DEBUG: Admin ID from session: {admin_id}")
    print(f"DEBUG: Organization ID from query: {organization_id}")

    raw_notifications = []

    if user_id:
        print(f"DEBUG: Attempting to fetch notifications for user_id: {user_id}")
        raw_notifications = crud.get_notifications(db, user_id=user_id)
    elif admin_id:
        print(f"DEBUG: Attempting to fetch notifications for admin_id: {admin_id}")
        raw_notifications = crud.get_notifications(db, admin_id=admin_id)
    elif organization_id:
        print(f"DEBUG: Attempting to fetch notifications for organization_id: {organization_id}")
        raw_notifications = crud.get_notifications(db, organization_id=organization_id)
    else:
        print("DEBUG: No user_id, admin_id, or organization_id found.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated or no organization ID provided."
        )
    
    print(f"DEBUG: Raw notifications fetched: {len(raw_notifications)}")

    # Fetch notification configurations
    config_map = crud.get_all_notification_configs_as_map(db)

    # Process and format notifications using the new CRUD function
    final_notifications_data = crud.process_and_format_notifications(db, raw_notifications, config_map)
    
    print(f"DEBUG: Final notifications after processing: {len(final_notifications_data)}")

    return JSONResponse(content={"notifications": final_notifications_data})

# Handles admin bulletin board post creation.
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
        
        admin_org_id = None
        if admin.organizations:
            admin_org_id = admin.organizations[0].id

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

        # Notify all users in the organization about the new bulletin post
        if admin_org_id:
            users_in_org = db.query(models.User).filter(models.User.organization_id == admin_org_id).all()
            for user in users_in_org:
                crud.create_notification(
                    db,
                    message=f"New bulletin post: '{title}'",
                    organization_id=admin_org_id,
                    user_id=user.id,
                    notification_type="bulletin_post",
                    entity_id=db_post.post_id,
                    url=f"/BulletinBoard#{db_post.post_id}" # Link to the bulletin board, anchor to post
                )

        return RedirectResponse(url="/admin/bulletin_board",
                                    status_code=status.HTTP_303_SEE_OTHER)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during post creation",
        )

# Displays the admin settings page.
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

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    organization_id = None
    current_theme_color = "#6B00B9"
    logo_url = default_logo_url

    if admin_id:
        admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
        if admin and admin.organizations:
            first_org = admin.organizations[0]
            organization_id = first_org.id
            
            if first_org.logo_url:
                logo_url = first_org.logo_url
            
            if first_org.theme_color:
                current_theme_color = first_org.theme_color

    return templates.TemplateResponse(
        "admin_dashboard/admin_settings.html",
        {
            "request": request,
            "year": "2025",
            "organization_id": organization_id,
            "current_theme_color": current_theme_color,
            "logo_url": logo_url
        },
    )

# Handles admin event creation.
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
        event_date = datetime.strptime(date, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date and time format. Please use Year-MM-DDTHH:MM (e.g., 2025-05-27T14:30).",
        )

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
        date=event_date,
        location=location,
        max_participants=max_participants,
        admin_id=admin_id,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Notify all users in the organization about the new event
    users_in_org = db.query(models.User).filter(models.User.organization_id == admin_org_id).all()
    for user in users_in_org:
        crud.create_notification(
            db,
            message=f"New event: '{title}' on {event_date.strftime('%Y-%m-%d at %H:%M')}",
            organization_id=admin_org_id,
            user_id=user.id,
            notification_type="event",
            entity_id=db_event.event_id,
            url=f"/Events#{db_event.event_id}" # Link to the events page, anchor to event
        )

    return RedirectResponse(url="/admin/events", status_code=status.HTTP_303_SEE_OTHER)

# Handles admin event deletion.
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

# Handles admin bulletin post deletion.
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

# Displays the admin payments page.
@router.get("/Admin/payments", response_class=HTMLResponse, name="admin_payments")
async def admin_payments(
    request: Request,
    db: Session = Depends(get_db),
    student_number: Optional[str] = None,
):
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
            admin_org_id = first_org.id

    query = db.query(models.PaymentItem).join(models.User)

    if admin_org_id:
        query = query.filter(models.User.organization_id == admin_org_id)

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

# This route allows an admin to view the payment history for all members in their organization.
@router.get("/admin/Payments/History", response_class=JSONResponse, name="admin_payment_history")
async def admin_payment_history(request: Request, db: Session = Depends(get_db)):
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

    current_admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()

    if not current_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found.")

    admin_organizations = current_admin.organizations
    if not admin_organizations:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin is not associated with an organization.")

    organization = admin_organizations[0]

    try:
        organization_members = db.query(models.User).filter(
            models.User.organization_id == organization.id
        ).all()

        member_ids = [member.id for member in organization_members]

        payments = (
            db.query(models.Payment)
            .options(joinedload(models.Payment.payment_item), joinedload(models.Payment.user))
            .filter(models.Payment.user_id.in_(member_ids))
            .order_by(models.Payment.created_at.desc(), models.Payment.id.desc())
            .all()
        )

        payment_history_data = []
        for payment in payments:
            payment_item = payment.payment_item
            user = payment.user

            academic_year = payment_item.academic_year if payment_item else None
            semester = payment_item.semester if payment_item else None
            fee = payment_item.fee if payment_item else None
            due_date = payment_item.due_date if payment_item else None
            is_not_responsible = payment_item.is_not_responsible if payment_item else False

            amount_paid = payment.amount
            status_raw = payment.status
            payment_created_at = payment.created_at
            payment_updated_at = payment.updated_at

            user_first_name = user.first_name if user else None
            user_last_name = user.last_name if user else None
            student_number = user.student_number if user else None

            if (academic_year is None or str(academic_year).lower() == "n/a" or
                semester is None or str(semester).lower() == "n/a" or
                fee is None or str(fee).lower() == "n/a" or
                amount_paid is None or str(amount_paid).lower() == "n/a" or
                status_raw is None or str(status_raw).lower() == "n/a" or
                due_date is None or str(due_date).lower() == "n/a" or
                payment_created_at is None or str(payment_created_at).lower() == "n/a" or
                user_first_name is None or str(user_first_name).lower() == "n/a" or
                user_last_name is None or str(user_last_name).lower() == "n/a" or
                student_number is None or str(student_number).lower() == "n/a"):
                continue

            status_text = status_raw
            if status_text == "pending":
                status_text = "Pending"
            elif status_text == "success":
                status_text = "Paid"                
            elif status_text == "failed":
                status_text = "Failed"
            elif status_text == "cancelled":
                status_text = "Cancelled"

            due_date_str = due_date.strftime('%Y-%m-%d') if due_date else 'Not Set'
            created_at_str = payment_created_at.strftime('%Y-%m-%d %H:%M:%S') if payment_created_at else None
            updated_at_str = payment_updated_at.strftime('%Y-%m-%d %H:%M:%S') if payment_updated_at else None

            payment_history_data.append({
                "item": {
                    "id": payment.id,
                    "amount": amount_paid,
                    "paymaya_payment_id": payment.paymaya_payment_id,
                    "status": payment.status,
                    "created_at": created_at_str,
                    "updated_at": updated_at_str,
                    "payment_item": {
                        "academic_year": academic_year,
                        "semester": semester,
                        "fee": fee,
                        "due_date": due_date_str,
                        "is_not_responsible": is_not_responsible
                    } if payment_item else None
                },
                "status": status_text,
                "user_name": f"{user_first_name} {user_last_name}" if user_first_name and user_last_name else "N/A",
                "student_number": student_number,
                "payment_date": created_at_str  
            })

        return JSONResponse(content={"payment_history": payment_history_data})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve organization payment history: {e}",
        )

# Updates the status of a specific payment item.
@router.post("/admin/payment/{payment_item_id}/update_status")
async def update_payment_status(
    request: Request,
    payment_item_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
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
                new_payment = models.Payment(
                    user_id=payment_item.user_id,
                    amount=payment_item.fee,
                    payment_item_id=payment_item_id,
                    status="success"
                )
                db.add(new_payment)
            db.commit()
        elif status == "NOT RESPONSIBLE":
            payment_item.is_not_responsible = True
            payment_item.is_paid = False
            payment_item.is_past_due = False
            payment_item.fee = 0.0

            existing_payment = db.query(models.Payment).filter(models.Payment.payment_item_id == payment_item_id).first()
            if existing_payment:
                db.delete(existing_payment)
            
            db.commit()
            return {"message": f"Payment item {payment_item_id} marked as NOT RESPONSIBLE, fee set to 0, and associated payment (if any) deleted."}

        db.commit()
        db.refresh(payment_item)
        return {"message": f"Payment item {payment_item_id} status updated to {status}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update payment item status: {e}",
        )

# Retrieves membership data for administrators.
@router.get("/admin/membership/")
async def admin_membership(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: Optional[str] = None,
    semester: Optional[str] = None,
) -> List[Dict]:
    try:
        admin_id = request.session.get("admin_id")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as admin")

        admin_org_id = get_entity_organization_id(db, admin_id)

        query = db.query(models.User).options(
            joinedload(models.User.payment_items).options(joinedload(models.PaymentItem.payments))
        ).filter(models.User.organization_id == admin_org_id)
        
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

# Retrieves individual membership data for administrators.
@router.get("/admin/individual_members/")
async def admin_individual_members(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: Optional[str] = None,
    semester: Optional[str] = None,
) -> List[Dict]:
    try:
        admin_id = request.session.get("admin_id")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated as admin")

        admin_org_id = get_entity_organization_id(db, admin_id)

        query = db.query(models.User).options(
            joinedload(models.User.payment_items).options(joinedload(models.PaymentItem.payments))
        ).filter(models.User.organization_id == admin_org_id)

        filters = []
        if academic_year:
            filters.append(models.PaymentItem.academic_year == academic_year)
        if semester:
            filters.append(models.PaymentItem.semester == semester)

        if filters:
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

# Returns monthly trends of total successful membership fees collected.
@router.get("/financial_trends")
async def get_financial_trends(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated as admin. Please log in.",
        )

    admin_org_id = get_entity_organization_id(db, admin_id)

    if not admin_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin organization not found or not assigned.",
        )

    num_months_to_display = 12
    today = date.today()

    all_months_data = OrderedDict()

    for i in range(num_months_to_display - 1, -1, -1):
        target_date = today - relativedelta(months=i)
        year_month_key = (target_date.year, target_date.month)
        all_months_data[year_month_key] = 0.0

    earliest_year, earliest_month = next(iter(all_months_data.keys()))
    earliest_date_for_filter = datetime(earliest_year, earliest_month, 1)

    financial_data_raw = (
        db.query(
            func.extract('year', models.Payment.created_at).label('year'),
            func.extract('month', models.Payment.created_at).label('month'),
            func.sum(models.Payment.amount).label('total'),
        )
        .join(models.Payment.user)
        .filter(
            models.Payment.status == "success",
            models.User.organization_id == admin_org_id,
            models.Payment.created_at >= earliest_date_for_filter,
            models.Payment.created_at <= today
        )
        .group_by(
            func.extract('year', models.Payment.created_at),
            func.extract('month', models.Payment.created_at),
        )
        .all()
    )

    for row in financial_data_raw:
        key = (int(row.year), int(row.month))
        if key in all_months_data:
            all_months_data[key] = float(row.total)

    labels = []
    data = []
    for (year, month), total in all_months_data.items():
        labels.append(f"{year}-{month:02d}")
        data.append(total)

    return {"labels": labels, "data": data}

# Returns total fees per academic year from PaymentItem.
@router.get("/expenses_by_category")
async def get_expenses_by_category(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated as admin. Please log in.",
        )

    admin_org_id = get_entity_organization_id(db, admin_id)

    if not admin_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin organization not found or not assigned.",
        )

    expenses_data = (
        db.query(
            models.Expense.category,
            func.sum(models.Expense.amount),
        )
        .filter(
            models.Expense.organization_id == admin_org_id
        )
        .group_by(
            models.Expense.category
        )
        .all()
    )

    labels = [
        category if category else "Uncategorized" for category, total in expenses_data
    ]
    data = [float(total) for category, total in expenses_data]

    return {"labels": labels, "data": data}

# Distributes collected successful funds based on the academic year.
@router.get("/fund_distribution")
async def get_fund_distribution(request: Request, db: Session = Depends(get_db)):
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
        models.PaymentItem.user
    ).filter(
        models.Payment.status == "success",
        models.User.organization_id == admin_org_id
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

# Retrieves the total outstanding dues amount.
@router.get("/admin/outstanding_dues/")
async def admin_outstanding_dues(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: Optional[str] = None,
) -> List[Dict]:
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

        query = db.query(models.PaymentItem).join(
            models.User, models.PaymentItem.user_id == models.User.id
        ).filter(
            and_(
                func.lower(models.PaymentItem.academic_year) == resolved_academic_year.lower(),
                models.PaymentItem.semester == current_semester,
                models.User.organization_id == admin_org_id,
                models.PaymentItem.is_not_responsible == False
            )
        )
        
        relevant_payment_items = query.all()
        
        total_outstanding_amount = 0.0
        # No notification creation here, so no URL needed

        for item in relevant_payment_items:
            if not item.is_paid:
                total_outstanding_amount += item.fee

        return [{"total_outstanding_amount": total_outstanding_amount}]

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch outstanding dues data")

# Displays total members for administrators.
@router.get("/admin/payments/total_members", response_class=HTMLResponse, name="payments_total_members")
async def payments_total_members(
    request: Request,
    db: Session = Depends(get_db),
    section: Optional[str] = None,
    year_level: Optional[str] = None,
    student_number: Optional[str] = None
):
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

    query = db.query(models.User).filter(models.User.organization_id == admin_org_id)

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

# Displays the admin bulletin board page.
@router.get('/admin/bulletin_board', response_class=HTMLResponse)
async def admin_bulletin_board(request: Request, db: Session = Depends(get_db)):
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

# Displays the admin events page.
@router.get('/admin/events', response_class=HTMLResponse)
async def admin_events(request: Request, db: Session = Depends(get_db)):
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

# Displays the admin financial statement page.
@router.get("/admin/financial_statement", response_class=HTMLResponse, name="admin_financial_statement")
async def admin_financial_statement_page(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")

    if not admin_id:
        return templates.TemplateResponse(
            "admin_dashboard/unauthorized.html",
            {"request": request, "message": "You must be logged in as an admin to view this page."}
        )

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
        },
    )

# This router provides endpoints for creating and retrieving organizational expenses.
@router.get("/expenses/", response_model=List[schemas.Expense], status_code=status.HTTP_200_OK)
async def get_expenses(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated as admin. Only admins can view expenses."
        )

    organization_id = get_entity_organization_id(db, admin_id)
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin is not associated with an organization. Cannot view expenses."
        )
    
    expenses = db.query(models.Expense).filter(
        models.Expense.organization_id == organization_id
    ).order_by(models.Expense.incurred_at.desc()).all()

    for expense in expenses:
        if expense.admin and expense.admin.position is None:
            expense.admin.position = ""

    return expenses

# This router handles expense-related endpoints for admins.
@router.post("/expenses/", response_model=schemas.Expense, status_code=status.HTTP_201_CREATED)
async def create_expense(request: Request, expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated as admin. Only admins can create expenses."
        )

    organization_id = get_entity_organization_id(db, admin_id)
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin is not associated with an organization. Cannot create expense."
        )
    
    total_revenue_query = db.query(func.sum(models.PaymentItem.fee)).join(
        models.User, models.PaymentItem.user_id == models.User.id
    ).filter(
        models.User.organization_id == organization_id,
        models.PaymentItem.is_paid.is_(True)
    )
    total_revenue = total_revenue_query.scalar() or 0.0

    total_expenses_query = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.organization_id == organization_id
    )
    total_expenses = total_expenses_query.scalar() or 0.0

    if (total_expenses + expense.amount) > total_revenue:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expense amount (₱{expense.amount:.2f}) exceeds the available revenue. "
                   f"Current total revenue: ₱{total_revenue:.2f}, "
                   f"Current total expenses: ₱{total_expenses:.2f}. "
                   f"Remaining budget: ₱{total_revenue - total_expenses:.2f}"
        )

    db_expense = models.Expense(
        description=expense.description,
        amount=expense.amount,
        category=expense.category,
        incurred_at=expense.incurred_at if expense.incurred_at else date.today(),
        admin_id=admin_id,
        organization_id=organization_id
    )

    db.add(db_expense)
    db.commit()
    
    db.refresh(db_expense, attribute_names=["admin"])     
    
    if db_expense.admin and db_expense.admin.position is None:
        db_expense.admin.position = ""

    return db_expense

# Retrieves financial data for administrators.
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
                extract('year', models.PaymentItem.updated_at) == current_year,
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
    total_funds_available = net_income_ytd 

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
            extract('year', models.PaymentItem.updated_at) == current_year,
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
        if top_revenue_source_query.academic_year and top_revenue_source_query.semester:
            source_name = f"AY {top_revenue_source_query.academic_year} - {top_revenue_source_query.semester} Fees"
        elif top_revenue_source_query.academic_year:
            source_name = f"AY {top_revenue_source_query.academic_year} Fees"
        elif top_revenue_source_query.semester:
            source_name = f"{top_revenue_source_query.semester} Semester Fees"
        else:
            source_name = "Miscellaneous Fees"
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
        largest_expense_category = largest_expense_query.category if largest_expense_query.category else "Uncategorized"
        largest_expense_amount = round(float(largest_expense_query.total_amount), 2)

    profit_margin_ytd = round((net_income_ytd / total_revenue_ytd) * 100, 2) if total_revenue_ytd != 0 else 0.0

    revenues_breakdown_query = db.query(
        models.PaymentItem.academic_year,
        models.PaymentItem.semester,
        func.sum(models.PaymentItem.fee).label('total_fee')
    ).join(models.User).\
    filter(
        and_(
            extract('year', models.PaymentItem.updated_at) == current_year,
            models.PaymentItem.is_paid == True,
            models.User.organization_id == organization_id
        )
    ).group_by(
        models.PaymentItem.academic_year,
        models.PaymentItem.semester
    ).all()

    revenues_breakdown = []
    for item in revenues_breakdown_query:
        if item.academic_year and item.semester:
            source_name = f"AY {item.academic_year} - {item.semester} Fees"
        elif item.academic_year:
            source_name = f"AY {item.academic_year} Fees"
        elif item.semester:
            source_name = f"{item.semester} Semester Fees"
        else:
            source_name = "Miscellaneous Fees"
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
            "category": item.category if item.category else "Uncategorized",
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

    for i in range(1, 13):
        target_month_num = i
        
        dummy_date = date(current_year, target_month_num, 1)
        month_name_full = dummy_date.strftime('%B')
        month_name_abbr = dummy_date.strftime('%b')
        chart_net_income_trend_labels.append(month_name_abbr)

        monthly_revenue_query = db.query(func.sum(models.PaymentItem.fee)).\
            join(models.User).\
            filter(
                and_(
                    extract('year', models.PaymentItem.updated_at) == current_year,
                    extract('month', models.PaymentItem.updated_at) == target_month_num,
                    models.PaymentItem.is_paid == True,
                    models.User.organization_id == organization_id
                )
            ).scalar()
        monthly_revenue = float(monthly_revenue_query) if monthly_revenue_query else 0.0

        monthly_expenses_query = db.query(func.sum(models.Expense.amount)).\
            filter(
                and_(
                    extract('year', models.Expense.incurred_at) == current_year,
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
                extract('year', models.PaymentItem.updated_at) == current_year,
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
        "total_current_balance": total_current_balance,
        "total_revenue_ytd": total_revenue_ytd,
        "total_expenses_ytd": total_expenses_ytd,
        "net_income_ytd": net_income_ytd,
        "balance_turnover": balance_turnover,
        "total_funds_available": total_funds_available,
        "reporting_date": reporting_date,
        "top_revenue_source_name": top_revenue_source["name"],
        "top_revenue_source_amount": top_revenue_source['amount'],
        "largest_expense_category": largest_expense_category,
        "largest_expense_amount": largest_expense_amount,
        "profit_margin_ytd": profit_margin_ytd,
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

# Creates a new organization.
@router.post("/admin/organizations/", response_model=schemas.Organization, status_code=status.HTTP_201_CREATED)
async def create_organization_route(
    request: Request,
    organization: schemas.OrganizationCreate,
    db: Session = Depends(get_db)
):
    existing_organization = db.query(models.Organization).filter(
        models.Organization.name == organization.name
    ).first()
    if existing_organization:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with name '{organization.name}' already exists."
        )

    existing_course_org = db.query(models.Organization).filter(
        models.Organization.primary_course_code == organization.primary_course_code
    ).first()
    if existing_course_org:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with primary course code '{organization.primary_course_code}' already exists."
        )

    try:
        custom_palette = crud.generate_custom_palette(organization.theme_color)

        suggested_filename = f"{organization.name.lower().replace(' ', '_')}_logo.png"
        logo_upload_path = f"/static/images/{suggested_filename}"

        new_org = models.Organization(
            name=organization.name,
            theme_color=organization.theme_color,
            primary_course_code=organization.primary_course_code,
            custom_palette=custom_palette,
            logo_url=logo_upload_path
        )
        db.add(new_org)
        db.commit()
        db.refresh(new_org)

        print(f"\n**Action Required:** Please upload the organization logo to your web server at the path: **{new_org.logo_url}**")
        print(f"The suggested filename for the image file is: **{suggested_filename}**")

        return new_org
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating organization: {e}"
        )
    
# Creates a new admin user.
@router.post("/admin/admins/", response_model=schemas.Admin, status_code=status.HTTP_201_CREATED)
async def create_admin_user_route(
    request: Request,
    admin_data: schemas.AdminCreate,
    db: Session = Depends(get_db)
):
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
            role="Admin",
            position=admin_data.position
        )
        db.add(new_admin)
        db.flush()

        if admin_data.organization_id:
            organization = db.get(models.Organization, admin_data.organization_id)
            if organization:
                new_admin.organizations.append(organization)
            else:
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

# Updates the theme color of an existing organization.
@router.put("/admin/organizations/{org_id}/theme", response_model=Dict[str, str])
async def update_organization_theme_color_route(
    request: Request,
    org_id: int,
    theme_update: schemas.OrganizationThemeUpdate,
    db: Session = Depends(get_db)
):
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
        organization.custom_palette = crud.generate_custom_palette(theme_update.new_theme_color)
        db.add(organization)
        db.commit()
        db.refresh(organization)
        return {"message": f"Organization '{organization.name}' (ID: {org_id}) theme color updated to {theme_update.new_theme_color} and palette regenerated successfully."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating organization theme color: {e}"
        )

# Uploads and updates the logo for an existing organization.
@router.put("/admin/organizations/{org_id}/logo", response_model=Dict[str, str])
async def update_organization_logo_route(
    request: Request,
    org_id: int,
    logo_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
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

    organization_name_slug = organization.name.lower().replace(' ', '_')
    organization_name_slug = ''.join(e for e in organization_name_slug if e.isalnum() or e == '_')

    file_extension = Path(logo_file.filename).suffix.lower()
    
    allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg']
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only {', '.join(allowed_extensions)} are allowed."
        )

    suggested_filename = f"{organization_name_slug}_logo{file_extension}"
    
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

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating organization logo: {e}"
        )

# Creates a PayMaya payment request.
@router.post("/payments/paymaya/create", response_class=JSONResponse, name="paymaya_create_payment")
async def paymaya_create_payment(
    request: Request,
    payment_item_id: int = Form(...),
    db: Session = Depends(get_db),
):
    public_api_key = "pk-Z0OSzLvIcOI2UIvDhdTGVVfRSSeiGStnceqwUE7n0Ah"
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
    
    db_payment = crud.create_payment(db, amount=payment_amount, user_id=user_id, payment_item_id=payment_item_id)

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

# Handles the payment success callback from PayMaya.
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

        # --- Notification Logic for Admin ---
        if user and user.organization:
            organization_admins = user.organization.admins
            for admin in organization_admins:
                message = f"Payment Successful: {user.first_name} {user.last_name} has successfully paid {payment.amount} for {payment_item.academic_year} {payment_item.semester} fees."
                crud.create_notification(
                    db,
                    message=message,
                    admin_id=admin.admin_id,
                    organization_id=user.organization_id,
                    notification_type="payment_success",
                    entity_id=payment.id,  # Link to the payment for context
                    url=f"/admin/Payments/History" # Link to admin payment history
                )
        # --- End Notification Logic ---

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

# Handles the payment failure callback from PayMaya.
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

# Handles the payment cancellation callback from PayMaya.
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

# Helper function to get related PaymentItem.
async def _get_related_payment_item(db: Session, payment_item_id: int | None) -> models.PaymentItem | None:
    if payment_item_id:
        return crud.get_payment_item_by_id(db, payment_item_id=payment_item_id)
    return None

app.include_router(router)

# Handles user logout.
@app.get("/logout", response_class=RedirectResponse, name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# Displays the root index page.
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Displays the home dashboard for both admin and regular users.
@app.get("/home", response_class=HTMLResponse, name="home")
async def home(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")
    user_role = request.session.get("user_role")

    current_year = "2025"
    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if not (user_id or admin_id) or not user_role:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Please log in to access this page."})

    current_org_id = None
    try:
        current_org_id = await get_user_organization_id(request, db)
    except HTTPException:
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

            past_due_users = db.query(models.User).join(models.PaymentItem).filter(
                models.User.organization_id == current_org_id,
                models.PaymentItem.is_past_due == True,
                models.PaymentItem.is_paid == False
            ).distinct(models.User.id).all()

            for past_due_user in past_due_users:
                message = f"Past Due Payments: {past_due_user.first_name} {past_due_user.last_name} has past due payment items."
                crud.create_notification(
                    db,
                    message=message,
                    admin_id=admin.admin_id,
                    organization_id=current_org_id,
                    notification_type="past_due_payments",
                    entity_id=past_due_user.id,
                    url=f"/admin/payments/total_members?student_number={past_due_user.student_number}"
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
        
        user_past_due_items = db.query(models.PaymentItem).filter(
            models.PaymentItem.user_id == user_id,
            models.PaymentItem.is_past_due == True,
            models.PaymentItem.is_paid == False
        ).all()

        if user_past_due_items:
            message = "You have past due payment items. Please check your payments page."
            crud.create_notification(
                db,
                message=message,
                user_id=user_id,
                organization_id=current_org_id,
                notification_type="user_past_due",
                url="/Payments"
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

# Displays the bulletin board page for users.
@app.get("/BulletinBoard", response_class=HTMLResponse, name="bulletin_board")
async def bulletin_board(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    if not user_id:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    user_org_id = None
    try:
        user_org_id = await get_user_organization_id(request, db)
    except HTTPException:
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

    hearted_posts = []
    return templates.TemplateResponse(
        "student_dashboard/bulletin_board.html",
        {"request": request, "year": "2025", "posts": posts, "hearted_posts": hearted_posts, "logo_url": logo_url}
    )

# Displays the events page for users.
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
        pass

    events = []
    if user_org_id:
        events = db.query(models.Event).options(joinedload(models.Event.participants)).join(models.Admin).join(models.Admin.organizations).filter(
            models.Organization.id == user_org_id
        ).order_by(models.Event.created_at.desc()).all()

    return templates.TemplateResponse(
        "student_dashboard/events.html", {
            "request": request,
            "year": "2025",
            "events": events,
            "logo_url": logo_url,
            "current_user_id": user_id
        }
    )

# Displays payment items for the authenticated user.
@app.get("/Payments", response_class=HTMLResponse, name="payments")
async def payments(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if user_role == "user":
        user_for_logo = db.query(models.User).filter(models.User.id == user_id).first()
        if user_for_logo and user_for_logo.organization and user_for_logo.organization.logo_url:
            logo_url = user_for_logo.organization.logo_url

    user_identifier = request.session.get("user_id")

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

# Displays the Payment History for users.
@app.get("/Payments/History", response_class=HTMLResponse, name="payment_history")
async def payment_history(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    user_role = request.session.get("user_role")

    default_logo_url = request.url_for('static', path='images/patrick_logo.jpg')
    logo_url = default_logo_url

    if user_role == "user":
        user_for_logo = db.query(models.User).filter(models.User.id == user_id).first()
        if user_for_logo and user_for_logo.organization and user_for_logo.organization.logo_url:
            logo_url = user_for_logo.organization.logo_url

    user_identifier = request.session.get("user_id")

    if not user_identifier:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    current_user = db.query(models.User).filter(models.User.id == user_identifier).first()
    if not current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        payments = (
            db.query(models.Payment)
            .options(joinedload(models.Payment.payment_item))
            .filter(models.Payment.user_id == user_identifier)
            .order_by(models.Payment.created_at.desc(), models.Payment.id.desc())
            .all()
        )

        payment_history_data = []
        for payment in payments:
            payment_item = payment.payment_item

            academic_year = payment_item.academic_year if payment_item else None
            semester = payment_item.semester if payment_item else None
            fee = payment_item.fee if payment_item else None
            due_date = payment_item.due_date if payment_item else None

            amount_paid = payment.amount
            status_raw = payment.status
            payment_date = payment.created_at

            if (academic_year is None or str(academic_year).lower() == "n/a" or
                semester is None or str(semester).lower() == "n/a" or
                fee is None or str(fee).lower() == "n/a" or
                amount_paid is None or str(amount_paid).lower() == "n/a" or
                status_raw is None or str(status_raw).lower() == "n/a" or
                due_date is None or str(due_date).lower() == "n/a" or
                payment_date is None or str(payment_date).lower() == "n/a"):
                continue

            status_text = status_raw
            if status_text == "pending":
                status_text = "Pending"
            elif status_text == "success":
                status_text = "Paid"
            elif status_text == "failed":
                status_text = "Failed"
            elif status_text == "cancelled":
                status_text = "Cancelled"

            payment_history_data.append({
                "item": payment,
                "status": status_text,
            })

        return templates.TemplateResponse(
            "student_dashboard/payment_history.html",
            {
                "request": request,
                "payment_history": payment_history_data,
                "current_user": current_user,
                "logo_url": logo_url,
                "year": "2025",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment history: {e}",
        )

# Displays the financial statement page for users.
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
    
    paid_user_payment_items = []
    unpaid_user_payment_items = []
    total_revenue = 0.0
    total_outstanding_fees = 0.0
    total_past_due_fees = 0.0

    collected_fees_by_category: defaultdict[str, float] = defaultdict(float)
    outstanding_fees_by_category: defaultdict[str, float] = defaultdict(float)

    for item in all_user_payment_items:
        # Inlined logic for category_name
        category_name: str
        if item.academic_year and item.semester:
            category_name = f"AY {item.academic_year} - {item.semester} Fees"
        elif item.academic_year:
            category_name = f"AY {item.academic_year} Fees"
        elif item.semester:
            category_name = f"{item.semester} Semester Fees"
        else:
            category_name = "Miscellaneous Fees"

        if item.is_paid:
            paid_user_payment_items.append(item)
            total_revenue += item.fee
            collected_fees_by_category[category_name] += item.fee
        else:
            unpaid_user_payment_items.append(item)
            total_outstanding_fees += item.fee
            outstanding_fees_by_category[category_name] += item.fee
            if item.due_date and item.due_date < today:
                total_past_due_fees += item.fee

    collected_fees_list = [{"category": k, "amount": v} for k, v in collected_fees_by_category.items()]
    outstanding_fees_list = [{"category": k, "amount": v} for k, v in outstanding_fees_by_category.items()]

    expense_query = db.query(models.Expense)
    if user_obj.organization_id:
        all_expenses = expense_query.filter(models.Expense.organization_id == user_obj.organization_id).all()
    else:
        all_expenses = expense_query.filter(models.Expense.organization_id.is_(None)).all()

    total_expenses: float = sum(expense.amount for expense in all_expenses)

    expenses_by_category: defaultdict[str, float] = defaultdict(float)
    for expense in all_expenses:
        category_name = expense.category if expense.category else "Uncategorized"
        expenses_by_category[category_name] += expense.amount
    expenses_by_category_list = [{"category": k, "amount": v} for k, v in expenses_by_category.items()]

    net_income: float = total_revenue - total_expenses 

    financial_summary_items: list[dict[str, float | str | date]] = []
    for item in paid_user_payment_items:
        relevant_date = item.updated_at if item.updated_at else item.created_at
        if relevant_date:
            # Inlined logic for category_name
            category_name_summary: str
            if item.academic_year and item.semester:
                category_name_summary = f"AY {item.academic_year} - {item.semester} Fees"
            elif item.academic_year:
                category_name_summary = f"AY {item.academic_year} Fees"
            elif item.semester:
                category_name_summary = f"{item.semester} Semester Fees"
            else:
                category_name_summary = "Miscellaneous Fees"

            financial_summary_items.append({
                "date": relevant_date,
                "event_item": category_name_summary,
                "inflows": item.fee,
                "outflows": 0.00
            })
    
    for expense in all_expenses:
        if expense.incurred_at:
            financial_summary_items.append({
                "date": expense.incurred_at,
                "event_item": f"Expenses - {expense.category if expense.category else 'Uncategorized'}",
                "inflows": 0.00,
                "outflows": expense.amount
            })
    
    financial_summary_items.sort(key=lambda x: x['date'])
    for item in financial_summary_items:
        item['date'] = item['date'].strftime("%Y-%m-%d")


    months_full = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    user_payments_by_month_current_year: defaultdict[str, float] = defaultdict(float)
    for item in paid_user_payment_items:
        relevant_date = item.updated_at if item.updated_at and item.updated_at.year == current_year else \
                        (item.created_at if item.created_at and item.created_at.year == current_year else None)
        if relevant_date:
            month_index = relevant_date.month - 1
            user_payments_by_month_current_year[months_full[month_index].lower()] += item.fee

    expenses_by_month_current_year: defaultdict[str, float] = defaultdict(float)
    for expense in all_expenses:
        if expense.incurred_at and expense.incurred_at.year == current_year:
            month_index = expense.incurred_at.month - 1
            expenses_by_month_current_year[months_full[month_index].lower()] += expense.amount

    running_balance_org_level = 0.00
    monthly_data: dict[str, dict[str, float]] = {}

    for i, month_name in enumerate(months_full):
        month_name_lower = month_name.lower()
        inflows_this_month = user_payments_by_month_current_year.get(month_name_lower, 0.00)
        outflows_this_month = expenses_by_month_current_year.get(month_name_lower, 0.00)
        
        starting_balance = running_balance_org_level
        ending_balance = starting_balance + inflows_this_month - outflows_this_month
        running_balance_org_level = ending_balance
        
        monthly_data[month_name_lower] = {
            "starting_balance": starting_balance,
            "inflows": inflows_this_month,
            "outflows": outflows_this_month,
            "ending_balance": ending_balance
        }

    current_date_str: str = today.strftime("%B %d, %Y")

    financial_data: dict = {
        "total_revenue": total_revenue,
        "total_outstanding_fees": total_outstanding_fees,
        "total_past_due_fees": total_past_due_fees,
        "total_expenses": total_expenses,
        "net_income": net_income,
        "collected_fees_by_category": collected_fees_list,
        "outstanding_fees_by_category": outstanding_fees_list,
        "expenses_by_category": expenses_by_category_list,
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

# Displays the detailed monthly report page for users.
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

# Retrieves detailed monthly report data for users.
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
    start_date_of_month: date = date(report_year, month_number, 1)
    end_of_month_day: int = calendar.monthrange(report_year, month_number)[1]
    end_date_of_month: date = date(report_year, month_number, end_of_month_day)

    all_user_payment_items_unsorted: list[models.PaymentItem] = db.query(models.PaymentItem).filter(
        models.PaymentItem.user_id == user_id
    ).all()

    expense_query = db.query(models.Expense)
    if user_obj.organization_id:
        all_expenses_unsorted: list[models.Expense] = expense_query.filter(models.Expense.organization_id == user_obj.organization_id).all()
    else:
        all_expenses_unsorted: list[models.Expense] = expense_query.filter(models.Expense.organization_id.is_(None)).all()

    all_financial_events: list[tuple[date, str, float, float, str, float]] = []

    for item in all_user_payment_items_unsorted:
        relevant_date = item.updated_at if item.updated_at else item.created_at
        if relevant_date:
            category_name: str
            if item.academic_year and item.semester:
                category_name = f"AY {item.academic_year} - {item.semester} Fee"
            elif item.academic_year:
                category_name = f"AY {item.academic_year} Fee"
            elif item.semester:
                category_name = f"{item.semester} Semester Fee"
            else:
                category_name = "Miscellaneous Fee"
            
            inflow_amount = item.fee if item.is_paid else 0.00
            outflow_amount = 0.00

            status_str = ""
            if item.is_paid:
                status_str = "Paid"
            else:
                status_str = "Unpaid"
                if item.due_date and item.due_date < date.today():
                    status_str = "Past Due"
            
            all_financial_events.append((relevant_date, category_name, inflow_amount, outflow_amount, status_str, item.fee))

    for expense in all_expenses_unsorted:
        if expense.incurred_at:
            description = f"Expense - {expense.category if expense.category else 'Uncategorized'}"
            all_financial_events.append((expense.incurred_at, description, 0.00, expense.amount, "Recorded", expense.amount))

    all_financial_events.sort(key=lambda x: x[0])

    transactions_for_report_month: list[dict] = []
    total_inflows_month: float = 0.00
    total_outflows_month: float = 0.00
    total_outstanding_month: float = 0.00
    total_past_due_month: float = 0.00
    
    current_running_balance: float = 0.00 
    starting_balance_month: float = 0.00

    for event_date, _, inflow, outflow, _, _ in all_financial_events:
        if event_date < start_date_of_month:
            current_running_balance += inflow - outflow
        else:
            starting_balance_month = current_running_balance
            break

    for event_date, description, inflow, outflow, status, original_value in all_financial_events:
        if start_date_of_month <= event_date <= end_date_of_month:
            total_inflows_month += inflow
            total_outflows_month += outflow
            
            current_running_balance += inflow - outflow

            transactions_for_report_month.append({
                "date": event_date.strftime("%Y-%m-%d"),
                "description": description,
                "inflow": inflow,
                "outflow": outflow,
                "status": status,
                "original_value": original_value,
                "running_balance": current_running_balance
            })
            
            if "Fee" in description and status != "Paid":
                matching_payment_item = next((pi for pi in all_user_payment_items_unsorted if (pi.updated_at == event_date or pi.created_at == event_date) and pi.fee == original_value), None)
                if matching_payment_item and not matching_payment_item.is_paid:
                    total_outstanding_month += matching_payment_item.fee
                    if matching_payment_item.due_date and matching_payment_item.due_date < date.today():
                        total_past_due_month += matching_payment_item.fee

    ending_balance_month_footer_sum: float = starting_balance_month + total_inflows_month - total_outflows_month

    response_content = {
        "month_name": month.capitalize(),
        "year": report_year,
        "current_date": date.today().strftime("%B %d, %Y"),
        "starting_balance": starting_balance_month,
        "total_inflows": total_inflows_month,
        "total_outflows": total_outflows_month,
        "total_outstanding": total_outstanding_month,
        "total_past_due": total_past_due_month,
        "ending_balance": ending_balance_month_footer_sum,
        "transactions": transactions_for_report_month,
        "user_name": f"{user_obj.first_name} {user_obj.last_name}" if user_obj else "N/A",
        "total_all_original_fees": sum(item.fee for item in all_user_payment_items_unsorted)
    }

    return JSONResponse(content=response_content)

# Displays the settings page for users.
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
                    formatted_birthdate = user.birthdate

    user.verification_status = "Verified" if user.is_verified else "Not Verified"

    return templates.TemplateResponse(
        "student_dashboard/settings.html",
        {"request": request, "year": "2025", "user": user, "formatted_birthdate": formatted_birthdate, "logo_url": logo_url},
    )

# Retrieves a list of all organizations.
@app.get("/api/organizations/", response_model=List[schemas.Organization])
async def get_organizations(db: Session = Depends(get_db)):
    organizations = db.query(models.Organization).all()
    return organizations

# Handles user signup.
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
    start_date = date(current_year, 2, 28)
    for i in range(8):
        academic_year = f"{current_year}-{current_year + 1}"
        due_date = start_date + timedelta(days=i * 6 * 30)
        year_level_applicable = (i // 2) + 1
        payment_items.append(
            {
                "user_id": new_user.id,
                "academic_year": academic_year,
                "semester": semester,
                "fee": 100.00,
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
            start_date = date(current_year, 2, 28)

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

# Retrieves a user by ID.
@app.get("/api/user/{user_id}", response_model=schemas.User)
async def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, identifier=str(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Retrieves user data including organization and verification status.
@app.get("/get_user_data", response_model=schemas.UserDataResponse)
async def get_user_data(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")

    current_user_obj = None
    organization_data = None
    first_name = None
    profile_picture = None
    is_verified_status = None

    if user_id:
        current_user_obj = db.query(models.User).filter(models.User.id == user_id).first()
        if current_user_obj:
            first_name = current_user_obj.first_name
            profile_picture = current_user_obj.profile_picture
            is_verified_status = current_user_obj.is_verified
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
            profile_picture = None
            
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
        is_verified=is_verified_status
    )

# Handles user and admin login.
@app.post("/api/login/")
async def login(request: Request, form_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.identifier, form_data.password)

    if user:
        request.session["user_id"] = user.id
        request.session["user_role"] = getattr(user, 'role', 'user')
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

# Retrieves the organization ID of the currently authenticated user or admin.
async def get_user_organization_id(request: Request, db: Session) -> int:
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

# Retrieves the organization ID associated with a given admin ID.
def get_entity_organization_id(db: Session, admin_id: int) -> int:
    admin = db.query(models.Admin).options(joinedload(models.Admin.organizations)).filter(models.Admin.admin_id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin for this entity not found.")
    if not admin.organizations:
        raise HTTPException(status_code=500, detail="Admin is not associated with any organization.")
    return admin.organizations[0].id

# Handles hearting/unhearting of bulletin posts.
@app.post("/bulletin/heart/{post_id}")
async def heart_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    action: str = Form(...)
):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated.")

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
        # Notify admin about the like
        if post.admin_id:
            liking_user = db.query(models.User).filter(models.User.id == user_id).first()
            if liking_user:
                message = f"{liking_user.first_name} {liking_user.last_name} liked your bulletin post: '{post.title}'"
                crud.create_notification(
                    db,
                    message,
                    organization_id=post_org_id,
                    admin_id=post.admin_id,
                    notification_type="bulletin_like",
                    entity_id=post_id,
                    url=f"/admin/bulletin_board#{post_id}" # Link to the specific bulletin post for admin
                )
    elif action == 'unheart' and post.heart_count > 0:
        post.heart_count -= 1
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'heart' or 'unheart'.")

    db.commit()
    db.refresh(post)
    return {"heart_count": post.heart_count}

# Handles a user joining an event.
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

    # Notify admin about the event join
    if event.admin_id:
        message = f"{user.first_name} {user.last_name} joined your event: '{event.title}'"
        crud.create_notification(
            db,
            message,
            organization_id=event_org_id,
            admin_id=event.admin_id,
            notification_type="event_join",
            entity_id=event_id,
            url=f"/admin/events#{event_id}" # Link to the specific event for admin
        )

    return RedirectResponse(url="/Events", status_code=status.HTTP_303_SEE_OTHER)

# Handles a user leaving an event.
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

# Retrieves a summary of upcoming events.
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
    
    limited_events = filtered_events[:5]

    return [{"title": event.title, "date": event.date.isoformat(), "location": event.location,
             "classification": event.classification} for event in limited_events]

# Generates an email address based on first and last name.
def generate_email(first_name: str, last_name: str) -> str:
    if first_name and last_name:
        return f"ic.{first_name.lower()}.{last_name.lower()}@cvsu.edu.ph"
    return None

# Updates the user's profile information.
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
    
    original_is_verified_status = user.is_verified

    def delete_file(file_path: Optional[str]):
        if file_path:
            full_path = os.path.join(
                "..", "frontend", file_path.lstrip("/")
            )
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    print(f"Error deleting old file {full_path}: {e}")
            else:
                print(f"File not found for deletion: {full_path}")

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

    if registration_form:
        if registration_form.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type for registration form. Only PDF is allowed.",
            )

        try:
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

            if "name" in student_info and student_info["name"]:
                name_str = student_info["name"].strip()
                name_str = re.sub(r"\s+[a-zA-Z]\.\s+", " ", name_str)
                name_str = re.sub(r"\s+[a-zA-Z]\.$", "", name_str)
                name_str = re.sub(r"\s+[a-zA-Z]\.(?=\s)", "", name_str)
                name_str = re.sub(r"\s+", " ", name_str).strip()
                name_parts = name_str.split()
                if len(name_parts) >= 2:
                    user.first_name = " ".join(name_parts[:-1]).title()
                    user.last_name = name_parts[-1].title()
                elif len(name_parts) == 1:
                    user.first_name = name_parts[0].title()
                    user.last_name = ""

            if user.first_name and user.last_name:
                user.email = generate_email(
                    user.first_name.replace(" ", ""), user.last_name
                )
            
            user.is_verified = True

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process registration form: {e}",
            )

    if profilePicture:
        try:
            delete_file(user.profile_picture)

            image_content = await profilePicture.read()
            max_image_size_bytes = 2 * 1024 * 1024
            if len(image_content) > max_image_size_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Image size too large. Maximum allowed size is {max_image_size_bytes} bytes.",
                )
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

    if first_name and last_name and not email:
        email = generate_email(first_name, last_name)
        user.email = email

    current_date = datetime.now()

    year_level_str = str(user.year_level).lower().strip()
    year_level_mapping = {
        "1st": 1, "first": 1, "1": 1,
        "2nd": 2, "second": 2, "2": 2,
        "3rd": 3, "third": 3, "3": 3,
        "4th": 4, "fourth": 4, "4": 4,
    }

    student_year = year_level_mapping.get(year_level_str, 1)

    first_academic_year_start = current_date.year - (student_year - 1)
    if current_date.month < 9:
        first_academic_year_start -= 1

    first_academic_year = f"{first_academic_year_start}-{first_academic_year_start + 1}"

    payment_items = user.payment_items

    for i, item in enumerate(payment_items):
        semester_offset = i // 2
        item_academic_year_start = first_academic_year_start + semester_offset
        item.academic_year = f"{item_academic_year_start}-{item_academic_year_start + 1}"

        academic_year_end_year = int(item.academic_year.split("-")[1])

        if (i % 2) == 0:
            jan_1st = datetime(academic_year_end_year, 1, 1)
            first_sunday_of_jan = jan_1st + timedelta(days=(6 - jan_1st.weekday()) % 7)
            due_date = first_sunday_of_jan
        else:
            june_1st = datetime(academic_year_end_year, 6, 1)
            first_sunday_of_june = june_1st + timedelta(days=(6 - june_1st.weekday()) % 7)
            third_sunday = first_sunday_of_june + timedelta(days=14)
            due_date = third_sunday

        item.due_date = due_date.date()

        if item.due_date and item.due_date < current_date.date() and not item.is_paid:
            item.is_past_due = True
        else:
            item.is_past_due = False

        db.add(item)
        db.flush()

    try:
        if not original_is_verified_status and user.is_verified:
            if user.organization_id:
                organization_admins = db.query(models.Admin).join(
                    models.organization_admins
                ).filter(
                    models.organization_admins.c.organization_id == user.organization_id
                ).all()

                for admin in organization_admins:
                    message = f"Member {user.first_name} {user.last_name} has been verified."
                    crud.create_notification(
                        db=db,
                        message=message,
                        organization_id=user.organization_id,
                        admin_id=admin.admin_id,
                        notification_type="member_verification",
                        entity_id=user.id,
                        url=f"/admin/payments/total_members?student_number={user.student_number}" # Link to admin individual members filtered by student
                    )

        db.commit()
        db.refresh(user)

        user.verification_status = "Verified" if user.is_verified else "Not Verified"

        return {"message": "Profile updated successfully", "user": user}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile in database: {e}",
        )
