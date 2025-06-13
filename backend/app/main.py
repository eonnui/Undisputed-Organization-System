from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Form, APIRouter, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, extract, desc
from . import models, schemas, crud
from .database import SessionLocal, engine
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict, OrderedDict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string
import os
import re
import requests
import base64
import bcrypt
import shutil
import calendar
from dateutil.relativedelta import relativedelta
import logging
import json

# Configure logger
logger = logging.getLogger("uvicorn.error")

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

# Define the subdirectory relative to STATIC_DIR for wiki images
WIKI_IMAGES_SUBDIRECTORY = "images/wiki_images"
# Define the full path where wiki images will be saved
FULL_WIKI_UPLOAD_PATH = STATIC_DIR / WIKI_IMAGES_SUBDIRECTORY
# Ensure the directory exists
FULL_WIKI_UPLOAD_PATH.mkdir(parents=True, exist_ok=True)

# Define the subdirectory for event classification images
EVENT_CLASSIFICATION_IMAGES_SUBDIRECTORY = "images/event_classifications"
# Ensure the directory exists for event classification images
(STATIC_DIR / EVENT_CLASSIFICATION_IMAGES_SUBDIRECTORY).mkdir(parents=True, exist_ok=True)

# Define subdirectory for shirt campaign images
CAMPAIGN_IMAGES_SUBDIRECTORY = "images/campaigns"
(STATIC_DIR / CAMPAIGN_IMAGES_SUBDIRECTORY).mkdir(parents=True, exist_ok=True)

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
        full_path = STATIC_DIR / file_path.lstrip("/static/")
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                logger.info(f"Successfully deleted old file: {full_path}")
            except Exception as e:
                logger.error(f"Error deleting old file {full_path}: {e}")

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
        logger.error(f"Failed to save file to {save_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}",
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
            organization = user.organization
            organization_id = organization.id
            if organization.logo_url:
                logo_url = organization.logo_url

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
    request: Request, db: Session = Depends(get_db),
    organization_id: Optional[int] = Query(None),
    include_read: bool = Query(False)
) -> JSONResponse:
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")
    raw_notifications = []
    if user_id:
        raw_notifications = crud.get_notifications(db, user_id=user_id, include_read=include_read)
    elif admin_id:
        raw_notifications = crud.get_notifications(db, admin_id=admin_id, include_read=include_read)
    elif organization_id:
        raw_notifications = crud.get_notifications(db, organization_id=organization_id, include_read=include_read)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated or no organization ID provided.")
    config_map = crud.get_all_notification_configs_as_map(db)
    final_notifications_data = crud.process_and_format_notifications(db, raw_notifications, config_map)
    return JSONResponse(content={"notifications": final_notifications_data})

@router.post("/{notification_id}/read", response_model=schemas.Notification)
async def mark_single_notification_as_read_endpoint(
    request: Request,
    notification_id: int,
    db: Session = Depends(get_db)
):  
    notif = crud.mark_notification_as_read(db, notification_id)
    if not notif:       
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")    
    db.commit()
    db.refresh(notif)  
    return notif

@router.post("/mark_notifications_as_read_bulk")
async def mark_notifications_as_read_bulk(
    notification_ids: List[int], db: Session = Depends(get_db)
):   
    try:       
        notifications_to_update = db.query(models.Notification).filter(
            models.Notification.id.in_(notification_ids)           
        ).all()
        if not notifications_to_update:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notifications not found or not accessible.")
        for notification in notifications_to_update:
            notification.is_read = True        
        db.commit()         
        return {"message": "Notifications marked as read successfully."}
    except Exception as e:
        db.rollback() 
        logger.error(f"Error marking notifications {notification_ids} as read: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to mark notifications as read: {e}")

@router.delete("/notifications/clear_all", status_code=status.HTTP_200_OK)
async def clear_all_notifications_route(
    request: Request,
    db: Session = Depends(get_db)
) -> JSONResponse:  
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")
    organization_id = request.session.get("organization_id")

    dismissed_count = 0
    if user_id:
        dismissed_count = crud.mark_all_notifications_as_dismissed_by_owner(db, user_id=user_id)
    elif admin_id:
        dismissed_count = crud.mark_all_notifications_as_dismissed_by_owner(db, admin_id=admin_id)
    elif organization_id:
        dismissed_count = crud.mark_all_notifications_as_dismissed_by_owner(db, organization_id=organization_id)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated to clear notifications.")
    
    return JSONResponse(content={"message": f"Successfully cleared {dismissed_count} notifications."})

@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_single_notification_route(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db)
) -> Response:
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")
    organization_id = request.session.get("organization_id") 

    dismissed_notification = None
    if user_id:
        dismissed_notification = crud.mark_notification_as_dismissed_by_owner(db, notification_id, user_id=user_id)
    elif admin_id:     
        dismissed_notification = crud.mark_notification_as_dismissed_by_owner(db, notification_id, admin_id=admin_id)
    elif organization_id:       
        dismissed_notification = crud.mark_notification_as_dismissed_by_owner(db, notification_id, organization_id=organization_id)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated to clear notifications.")

    if not dismissed_notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found or unauthorized to dismiss.")
      
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Fetching Organization Admin Postition
@router.get("/api/admin/org_chart_data", response_model=List[Dict[str, str]])
async def get_organizational_chart_data(
    request: Request,
    db: Session = Depends(get_db)
):  
    authenticated_entity = None
    organization = None

    try:
        authenticated_entity, organization = get_current_admin_with_org(request, db)
    except HTTPException as e:

        if e.status_code == status.HTTP_401_UNAUTHORIZED or e.status_code == status.HTTP_403_FORBIDDEN:
            try:
                authenticated_entity, organization = get_current_user_with_org(request, db)
            except HTTPException:
                
                raise e
        else:

            raise

    if not organization:

        return []

    admins = db.query(models.Admin).join(models.organization_admins).filter(
        models.organization_admins.c.organization_id == organization.id
    ).all()

    org_chart_data = []
    for admin in admins:
        admin_data = {
            "first_name": admin.first_name if admin.first_name else "",
            "last_name": admin.last_name if admin.last_name else "",
            "email": admin.email if admin.email else "",
            "position": admin.position if admin.position else "", 
            "organization_name": organization.name if organization and organization.name else "N/A",
        }
        org_chart_data.append(admin_data)

    return org_chart_data

@router.get("/api/admin/organizations/{organization_id}/taken_positions", response_model=List[str])
async def get_taken_positions(organization_id: int, db: Session = Depends(get_db)):
    taken_positions_query = db.query(models.Admin.position).join(models.Admin.organizations).filter(
        models.Organization.id == organization_id
    ).distinct().all()

    taken_positions = [position[0] for position in taken_positions_query if position[0]]

    return taken_positions

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
        if user.organization_id == admin_org.id:
            crud.create_notification(
            db,
            message=f"New bulletin post: '{title}'",
            organization_id=admin_org.id,
            user_id=user.id,
            notification_type="bulletin_post",
            bulletin_post_id=db_post.post_id, 
            url=f"/BulletinBoard#{db_post.post_id}",
            event_identifier=f"bulletin_post_user_{user.id}_post_{db_post.post_id}"
            )

    # Log the action
    description = f"Admin '{admin.first_name} {admin.last_name}' created bulletin board post: '{db_post.title}'."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Bulletin Post Created",
        description=description,
        request=request,
        target_entity_type="BulletinBoard",
        target_entity_id=db_post.post_id
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
    classification_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)

    # --- Server-side Validation ---

    # Validate Date and Time
    try:
        event_date = datetime.strptime(date, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date and time format. Please use YYYY-MM-DDTHH:MM (e.g., 2025-05-27T14:30)."
        )

    # Ensure the event date is not in the past
    current_datetime = datetime.now()
    # For accurate comparison, clear seconds and microseconds if the client-side also clears them.
    # However, it's generally safer to compare with a slight buffer or compare to the minute.
    # Here, we'll just compare directly, which is strict.
    if event_date < current_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event date and time cannot be in the past. Please select a future date and time."
        )

    # Validate Max Participants
    if max_participants < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Max participants cannot be less than 0. Please enter a valid non-negative number."
        )

    # --- End Server-side Validation ---

    classification_image_url = None
    if classification_image and classification_image.filename:
        classification_image_url = await handle_file_upload(
            classification_image,
            EVENT_CLASSIFICATION_IMAGES_SUBDIRECTORY,
            ["image/jpeg", "image/png", "image/gif", "image/svg+xml"],
            max_size_bytes=5 * 1024 * 1024
        )

    db_event = models.Event(
        title=title,
        classification=classification,
        description=description,
        date=event_date,
        location=location,
        max_participants=max_participants,
        admin_id=admin.admin_id,
        classification_image_url=classification_image_url,
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
            event_id=db_event.event_id,
            url=f"/Events#{db_event.event_id}",
            event_identifier=f"new_event_user_{user.id}_event_{db_event.event_id}"
        )

    # Log the action
    description = f"Admin '{admin.first_name} {admin.last_name}' created event: '{db_event.title}'."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Event Created",
        description=description,
        request=request,
        target_entity_type="Event",
        target_entity_id=db_event.event_id
    )

    db.commit()
    return RedirectResponse(url="/admin/events", status_code=status.HTTP_303_SEE_OTHER)

# Admin Event Deletion 
@router.post("/admin/events/delete/{event_id}", response_class=HTMLResponse, name="admin_delete_event")
async def admin_delete_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    admin, admin_org = get_current_admin_with_org(request, db)
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")    
   
    if event.classification_image_url:
        delete_file_from_path(event.classification_image_url)

    db.query(models.Notification).filter(
        models.Notification.event_id == event_id 
    ).delete(synchronize_session=False)

    db.delete(event)
    db.commit()

    # Log the action
    description = f"Admin '{admin.first_name} {admin.last_name}' deleted event: '{event.title}' (ID: {event.event_id})."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Event Deleted",
        description=description,
        request=request,
        target_entity_type="Event",
        target_entity_id=event.event_id
    )

    return RedirectResponse(url="/admin/events", status_code=status.HTTP_303_SEE_OTHER)

# Admin Bulletin Post Deletion
@router.post("/admin/bulletin_board/delete/{post_id}", response_class=HTMLResponse, name="admin_delete_bulletin_post")
async def admin_delete_bulletin_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    admin, admin_org = get_current_admin_with_org(request, db)
    post = db.query(models.BulletinBoard).filter(models.BulletinBoard.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    if post.image_path:
        delete_file_from_path(post.image_path)

    db.query(models.Notification).filter(
        models.Notification.bulletin_post_id == post_id 
    ).delete(synchronize_session=False)

    db.query(models.UserLike).filter(models.UserLike.post_id == post_id).delete(synchronize_session=False)

    db.delete(post)
    db.commit()

    # Log the action
    description = f"Admin '{admin.first_name} {admin.last_name}' deleted bulletin board post: '{post.title}' (ID: {post.post_id})."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Bulletin Post Deleted",
        description=description,
        request=request,
        target_entity_type="BulletinBoard",
        target_entity_id=post.post_id
    )

    return RedirectResponse(url="/admin/bulletin_board", status_code=status.HTTP_303_SEE_OTHER)

# Shirt Campaigns
@router.post("/campaigns/", response_model=schemas.ShirtCampaign)
async def create_shirt_campaign_api(
    request: Request,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    prices_by_size: str = Form(..., description="JSON string of prices by size, e.g., '{\"S\": 15.0, \"M\": 16.0}'"), # New field
    pre_order_deadline: datetime = Form(...),
    available_stock: int = Form(...),
    is_active: bool = Form(True),
    size_chart_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)
    organization_id = admin_org.id if admin_org else None

    # Parse prices_by_size JSON string
    try:
        parsed_prices_by_size = json.loads(prices_by_size)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format for 'prices_by_size'. It must be a dictionary like {'size': price}."
        )

    size_chart_image_path = None
    if size_chart_image and size_chart_image.filename:
        size_chart_image_path = await handle_file_upload(
            size_chart_image,
            CAMPAIGN_IMAGES_SUBDIRECTORY,
            ["image/jpeg", "image/png", "image/gif", "image/svg+xml"],
            max_size_bytes=5 * 1024 * 1024
        )

    # REMOVE organization_id from here as it's not part of ShirtCampaignCreate schema
    campaign_data = schemas.ShirtCampaignCreate(
        title=title,
        description=description,
        prices_by_size=parsed_prices_by_size,
        pre_order_deadline=pre_order_deadline,
        available_stock=available_stock,
        is_active=is_active,
        size_chart_image_path=size_chart_image_path
    )

    # Pass organization_id directly to the crud function
    db_campaign = crud.create_shirt_campaign(
        db=db,
        campaign=campaign_data,
        admin_id=admin.admin_id,
        organization_id=organization_id, # <--- ADD THIS LINE
    )

    description_log = f"Admin '{admin.first_name} {admin.last_name}' created shirt campaign: '{db_campaign.title}'."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Shirt Campaign Created",
        description=description_log,
        request=request,
        target_entity_type="ShirtCampaign",
        target_entity_id=db_campaign.id
    )

    return db_campaign

@router.get("/campaigns/{campaign_id}", response_model=schemas.ShirtCampaign)
async def get_shirt_campaign_api(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        current_entity, organization = get_current_admin_with_org(request, db)
    except HTTPException:
        try:
            current_entity, organization = get_current_user_with_org(request, db)
        except HTTPException as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated to view campaigns.")

    campaign = crud.get_shirt_campaign_by_id(db, campaign_id=campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shirt Campaign not found")
    if organization and campaign.organization_id != organization.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Campaign not accessible to this organization.")
    return campaign

@router.get("/campaigns/", response_model=List[schemas.ShirtCampaign])
async def get_all_shirt_campaigns_api(
    request: Request,
    db: Session = Depends(get_db),
    admin_info_tuple: Tuple[models.Admin, models.Organization] = Depends(get_current_admin_with_org),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),
    is_active: Optional[bool] = Query(None, description="Filter by campaign active status"),
    search: Optional[str] = Query(None, description="Search keyword in campaign name or description"),
    start_date: Optional[date] = Query(None, description="Filter campaigns starting from this date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter campaigns ending by this date (YYYY-MM-DD)")
):
    current_admin, current_organization = admin_info_tuple
    organization_id = current_organization.id if current_organization else None

    campaigns = crud.get_all_shirt_campaigns(
        db=db,
        organization_id=organization_id,
        skip=skip,
        limit=limit,
        is_active=is_active,
        search=search,
        start_date=start_date,
        end_date=end_date
    )

    return campaigns

@router.put("/campaigns/{campaign_id}", response_model=schemas.ShirtCampaign)
async def update_shirt_campaign_api(
    campaign_id: int,
    request: Request,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    # price_per_shirt: Optional[float] = Form(None), # Removed: prices_by_size takes precedence
    prices_by_size: Optional[str] = Form(None, description="Optional JSON string of prices by size for update"), # New field
    pre_order_deadline: Optional[datetime] = Form(None),
    available_stock: Optional[int] = Form(None),
    is_active: Optional[bool] = Form(None),
    size_chart_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)

    campaign = crud.get_shirt_campaign_by_id(db, campaign_id=campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shirt Campaign not found")
    if campaign.organization_id != admin_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this campaign.")

    # Prepare update data dynamically
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description

    if prices_by_size is not None:
        try:
            update_data["prices_by_size"] = json.loads(prices_by_size)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format for 'prices_by_size'. It must be a dictionary like {'size': price}."
            )
    # if price_per_shirt is not None: # No longer accepting price_per_shirt directly for update
    #     update_data["price_per_shirt"] = price_per_shirt

    if pre_order_deadline is not None:
        update_data["pre_order_deadline"] = pre_order_deadline
    if available_stock is not None:
        update_data["available_stock"] = available_stock
    if is_active is not None:
        update_data["is_active"] = is_active

    final_size_chart_image_path = campaign.size_chart_image_path
    if size_chart_image is not None:
        if size_chart_image.filename:
            final_size_chart_image_path = await handle_file_upload(
                size_chart_image,
                CAMPAIGN_IMAGES_SUBDIRECTORY,
                ["image/jpeg", "image/png", "image/gif", "image/svg+xml"],
                max_size_bytes=5 * 1024 * 1024,
                old_file_path=campaign.size_chart_image_path
            )
        else:
            delete_file_from_path(campaign.size_chart_image_path)
            final_size_chart_image_path = None
    update_data["size_chart_image_path"] = final_size_chart_image_path # Always include even if None

    campaign_update = schemas.ShirtCampaignUpdate(**update_data)

    updated_campaign = crud.update_shirt_campaign(
        db=db,
        campaign_id=campaign_id,
        campaign_update=campaign_update
    )

    if not updated_campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shirt Campaign not found after update attempt.")

    description_log = f"Admin '{admin.first_name} {admin.last_name}' updated shirt campaign: '{updated_campaign.title}'."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Shirt Campaign Updated",
        description=description_log,
        request=request,
        target_entity_type="ShirtCampaign",
        target_entity_id=updated_campaign.id
    )

    return updated_campaign

@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shirt_campaign_api(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)

    campaign = crud.get_shirt_campaign_by_id(db, campaign_id=campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shirt Campaign not found")
    if campaign.organization_id != admin_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this campaign.")

    if campaign.size_chart_image_path:
        delete_file_from_path(campaign.size_chart_image_path)

    crud.delete_shirt_campaign(db, campaign_id=campaign_id)

    description_log = f"Admin '{admin.first_name} {admin.last_name}' deleted shirt campaign: '{campaign.title}' (ID: {campaign.id})."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Shirt Campaign Deleted",
        description=description_log,
        request=request,
        target_entity_type="ShirtCampaign",
        target_entity_id=campaign.id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Shirt Orders
@router.post("/orders/", response_model=schemas.StudentShirtOrder)
async def create_student_shirt_order_api(
    request: Request,
    campaign_id: int = Form(...),
    student_name: str = Form(...),
    student_year_section: str = Form(...),
    shirt_size: str = Form(...),
    quantity: int = Form(...),
    # order_total_amount: float = Form(...), # REMOVED: This is now calculated by CRUD
    student_email: Optional[str] = Form(None),
    student_phone: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    current_student, _ = get_current_user_with_org(request, db)
    student_id = current_student.id
    order_data = schemas.StudentShirtOrderCreate(
        campaign_id=campaign_id,
        student_id=student_id,
        student_name=student_name,
        student_year_section=student_year_section,
        student_email=student_email,
        student_phone=student_phone,
        shirt_size=shirt_size,
        quantity=quantity,
        # order_total_amount=order_total_amount, # REMOVED: Do not pass this, CRUD calculates it
    )

    db_order = crud.create_student_shirt_order(
        db=db,
        order=order_data,
    )

    return db_order

@router.get("/orders/{order_id}", response_model=schemas.StudentShirtOrder)
async def get_student_shirt_order_api(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    current_entity = None
    organization = None
    is_admin = False

    try:
        current_entity, organization = get_current_admin_with_org(request, db)
        is_admin = True
    except HTTPException:
        try:
            current_entity, organization = get_current_user_with_org(request, db)
        except HTTPException as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated to view orders.")

    order = crud.get_student_shirt_order_by_id(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student Shirt Order not found")


    if order.campaign and organization and order.campaign.organization_id != organization.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this order.")

    if not is_admin and order.student_id != current_entity.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this order.")

    return order

@router.get("/orders/campaign/{campaign_id}", response_model=List[schemas.StudentShirtOrder])
async def get_student_shirt_orders_by_campaign_api(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),

):
    admin, admin_org = get_current_admin_with_org(request, db)
    campaign = crud.get_shirt_campaign_by_id(db, campaign_id=campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    if campaign.organization_id != admin_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view orders for this campaign.")

    orders = crud.get_student_shirt_orders_for_campaign(
        db,
        campaign_id=campaign_id,

        skip=skip,
        limit=limit
    )
    return orders

@router.get("/orders/student/{student_id}", response_model=List[schemas.StudentShirtOrder])
async def get_student_shirt_orders_by_student_api(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),

):
    current_entity = None
    organization = None
    is_admin = False

    try:
        current_entity, organization = get_current_admin_with_org(request, db)
        is_admin = True
    except HTTPException:
        try:
            current_entity, organization = get_current_user_with_org(request, db)
        except HTTPException as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated to view orders.")

    if not is_admin and student_id != current_entity.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view orders for another student.")

    orders = crud.get_student_shirt_orders_by_student_id(
        db,
        student_id=student_id,
        skip=skip,
        limit=limit
    )
    return orders

@router.put("/orders/{order_id}", response_model=schemas.StudentShirtOrder)
async def update_student_shirt_order_api(
    order_id: int,
    request: Request,
    order_update_data: schemas.StudentShirtOrderUpdate = Body(...), # Expect update data in request body
    db: Session = Depends(get_db)
):
    # Authenticate the current user (student)
    current_user, user_org = get_current_user_with_org(request, db)

    # Fetch the order by its ID
    order = crud.get_student_shirt_order_by_id(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student Shirt Order not found.")

    # Authorization: Ensure the order belongs to the current student
    if order.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this order. You can only update your own orders.")

    # Authorization: Also ensure the order's campaign belongs to the student's organization
    # This prevents students from updating orders in other organizations
    if order.campaign and order.campaign.organization_id != user_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this order. Order belongs to a different organization.")

    updated_order = crud.update_student_shirt_order(
        db=db,
        order_id=order_id,
        order_update=order_update_data, # Use the actual update data from the request body
    )

    if not updated_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found after update attempt.")

    # Removed admin log. If you want to log user actions, you'll need a separate user log system.
    return updated_order

@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student_shirt_order_api(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    # Authenticate the current user (student)
    current_user, user_org = get_current_user_with_org(request, db)

    # Fetch the order by its ID
    order = crud.get_student_shirt_order_by_id(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student Shirt Order not found.")

    # Authorization: Ensure the order belongs to the current student
    if order.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this order. You can only delete your own orders.")

    # Authorization: Also ensure the order's campaign belongs to the student's organization
    if order.campaign and order.campaign.organization_id != user_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this order. Order belongs to a different organization.")

    crud.delete_student_shirt_order(db, order_id=order_id)

    # Removed admin log. If you want to log user actions, you'll need a separate user log system.
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/orders/", response_model=List[schemas.StudentShirtOrder]) # <-- ADD THIS ROUTE
async def get_all_organization_orders_for_admin(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),
):
    # This dependency will ensure only authenticated admins can access
    # and will give you the admin object and their organization
    admin, organization = get_current_admin_with_org(request, db)

    # Use a CRUD function to fetch all orders for that organization
    # You'll need to ensure crud.get_all_student_shirt_orders_by_organization
    # exists and correctly filters by organization_id
    orders = crud.get_all_student_shirt_orders_by_organization(
        db,
        organization_id=organization.id,
        skip=skip,
        limit=limit
    )
    return orders

@router.get("/student/shirt-management", response_class=HTMLResponse, name="student_shirt_management")
async def get_student_shirt_management_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user_and_org: tuple = Depends(get_current_user_with_org)
):
    logger.info("--- Entering /student/shirt-management route ---")

    current_user = current_user_and_org[0]
    logger.info(f"Current User ID: {current_user.id if current_user else 'None'}")
    logger.info(f"Current User Name: {current_user.name if current_user else 'None'}")

    organization_obj: Optional[models.Organization] = current_user_and_org[1]
    logger.info(f"Organization Object: {organization_obj}")

    organization_id: Optional[int] = organization_obj.id if organization_obj else None
    logger.info(f"Organization ID (extracted): {organization_id}")

    # --- THIS IS THE CRITICAL FIX ---
    # Change min_pre_order_deadline to start_date
    shirt_campaigns = crud.get_all_shirt_campaigns(
        db,
        organization_id=organization_id,
        is_active=True,
        start_date=date.today() # Renamed to match crud function's 'start_date' parameter
    )
    logger.info(f"Fetched Shirt Campaigns: {len(shirt_campaigns)} campaigns.")
    for campaign in shirt_campaigns:
        logger.info(f"   - Campaign ID: {campaign.id}, Name: {campaign.title}, Org ID: {campaign.organization_id}, Deadline: {campaign.pre_order_deadline}")
        # Note: 'status' is not an attribute of 'campaign' in your schemas.
        # If 'status' is important, it needs to be part of the campaign model/schema or derived.

    student_shirt_orders = crud.get_student_shirt_orders_by_student_id(db, current_user.id)
    logger.info(f"Fetched Student Shirt Orders: {len(student_shirt_orders)} orders for student {current_user.id}.")
    for order in student_shirt_orders:
        logger.info(f"   - Order ID: {order.id}, Campaign ID: {order.campaign_id}, Payment Status: {order.payment.status if order.payment else 'No Payment Record'}")
        # Assuming order.payment is now correctly loaded and has a .status attribute

    env = templates.env
    logger.info(f"Jinja2 Environment acquired: {env}")

    if 'now' not in env.globals:
        env.globals['now'] = datetime.now
        logger.info("Added 'now' to Jinja2 globals.")
    else:
        logger.info("'now' already exists in Jinja2 globals.")


    order_detail = None # This remains None unless a specific order is passed
    logger.info(f"Order Detail set to: {order_detail}")

    context = await get_base_template_context(request, db)
    logger.info(f"Base Template Context Keys: {list(context.keys())}")

    context.update({
        "shirt_campaigns": shirt_campaigns,
        "student_shirt_orders": student_shirt_orders,
        "current_user": current_user,
        "order_detail": order_detail # This will always be None unless you modify the route to accept an order_id
    })
    logger.info(f"Final Template Context Keys: {list(context.keys())}")


    logger.info("--- Exiting /student/shirt-management route (rendering template) ---")
    return templates.TemplateResponse(
        "student_dashboard/student_shirt_management.html", # Double-check this path if you have issues
        context
    )

@router.get("/student/shirt-management/order/{order_id}", response_class=HTMLResponse)
async def get_student_shirt_order_detail_page(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user_and_org: tuple = Depends(get_current_user_with_org)
):
    logger.info(f"--- Entering /student/shirt-management/order/{order_id} route ---")

    current_user = current_user_and_org[0]
    logger.info(f"Current User ID: {current_user.id if current_user else 'None'}")

    found_order = crud.get_student_shirt_order_by_id(db, order_id)
    logger.info(f"Attempting to fetch order ID: {order_id}. Found: {found_order.id if found_order else 'None'}")

    if not found_order or found_order.student_id != current_user.id:
        logger.warning(f"Order {order_id} not found or user {current_user.id} does not own it.")
        raise HTTPException(status_code=404, detail="Order not found or not accessible.")

    organization_obj: Optional[models.Organization] = current_user_and_org[1]
    logger.info(f"Organization Object: {organization_obj}")

    organization_id: Optional[int] = organization_obj.id if organization_obj else None
    logger.info(f"Organization ID (extracted): {organization_id}")
    shirt_campaigns = crud.get_all_shirt_campaigns(
        db,
        organization_id=organization_id,
        is_active=True,
        start_date=date.today() # Changed min_pre_order_deadline to start_date
    )
    logger.info(f"Fetched Shirt Campaigns: {len(shirt_campaigns)} campaigns for order detail page.")
    for campaign in shirt_campaigns:
        logger.info(f"   - Campaign ID: {campaign.id}, Name: {campaign.title}, Org ID: {campaign.organization_id}, Deadline: {campaign.pre_order_deadline}")

    student_shirt_orders = crud.get_student_shirt_orders_by_student_id(db, current_user.id)
    logger.info(f"Fetched Student Shirt Orders: {len(student_shirt_orders)} orders for student {current_user.id} on order detail page.")
    env = templates.env
    logger.info(f"Jinja2 Environment acquired: {env}")
    if 'now' not in env.globals:
        env.globals['now'] = datetime.now
        logger.info("Added 'now' to Jinja2 globals.")
    else:
        logger.info("'now' already exists in Jinja2 globals.")

    context = await get_base_template_context(request, db)
    logger.info(f"Base Template Context Keys: {list(context.keys())}")
    context.update({
        "shirt_campaigns": shirt_campaigns,
        "student_shirt_orders": student_shirt_orders,
        "current_user": current_user,
        "order_detail": found_order
    })
    logger.info(f"Final Template Context Keys: {list(context.keys())}")
    logger.info(f"--- Exiting /student/shirt-management/order/{order_id} route (rendering template) ---")
    return templates.TemplateResponse(
        "student_dashboard/student_shirt_management.html",
        context
    )

@router.get("/admin/shirt_management", response_class=HTMLResponse, name="admin_shirt_management")
async def admin_shirt_management(request: Request, db: Session = Depends(get_db)):
    admin, organization = get_current_admin_with_org(request, db)
    context = await get_base_template_context(request, db)
    context.update({
        "admin_id": admin.admin_id,
        "organization_id": organization.id,
    })
    return templates.TemplateResponse("admin_dashboard/admin_shirt_management.html", context)

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
async def admin_payment_history(
    request: Request,
    db: Session = Depends(get_db),
    student_number: Optional[str] = None
):
    admin, organization = get_current_admin_with_org(request, db)

    query = db.query(models.Payment).options(
        joinedload(models.Payment.payment_item),
        joinedload(models.Payment.user)
    ).join(models.User).filter(
        models.User.organization_id == organization.id
    )

    if student_number:
        query = query.filter(models.User.student_number == student_number)

    payments = query.order_by(
        models.Payment.created_at.desc(),
        models.Payment.id.desc()
    ).all()

    payment_history_data = []
    for payment in payments:
        payment_item = payment.payment_item
        user = payment.user

        # --- CORRECTED LOGIC STARTS HERE ---
        # First, check if essential related objects (payment_item, user) are not None.
        # Then, check their specific attributes.
        # This prevents AttributeError if payment_item or user is None.
        if (
            payment_item is not None and
            user is not None and
            payment_item.academic_year is not None and
            payment_item.semester is not None and
            payment_item.fee is not None and
            payment_item.due_date is not None and
            payment.amount is not None and
            payment.status is not None and
            payment.created_at is not None and
            user.first_name is not None and
            user.last_name is not None and
            user.student_number is not None
        ):
            status_text = payment.status
            if status_text == "pending": status_text = "Pending"
            elif status_text == "success": status_text = "Paid"
            elif status_text == "failed": status_text = "Failed"
            elif status_text == "cancelled": status_text = "Cancelled"
            elif status_text == "past_due": status_text = "Past Due"
            elif status_text == "unpaid": status_text = "Unpaid"

            # Safely build the payment_item dictionary, assuming payment_item is not None here
            payment_item_data = {
                "academic_year": payment_item.academic_year,
                "semester": payment_item.semester,
                "fee": float(payment_item.fee),
                "due_date": payment_item.due_date.strftime('%Y-%m-%d'),
                "is_not_responsible": payment_item.is_not_responsible
            }

            payment_history_data.append({
                "item": {
                    "id": payment.id,
                    "amount": float(payment.amount),
                    "paymaya_payment_id": payment.paymaya_payment_id,
                    "status": payment.status,
                    "created_at": payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "updated_at": payment.updated_at.strftime('%Y-%m-%d %H:%M:%S') if payment.updated_at else None,
                    "payment_item": payment_item_data # Use the safely built dictionary
                },
                "status": status_text,
                "user_name": f"{user.first_name} {user.last_name}",
                "student_number": user.student_number,
                "payment_date": payment.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            # If any required data is missing, print a warning and skip this entry
            print(f"Skipping payment {payment.id} due to missing related data.")
            continue
        # --- CORRECTED LOGIC ENDS HERE ---

    return JSONResponse(content={"payment_history": payment_history_data})

# Update Payment Status
@router.post("/admin/payment/{payment_item_id}/update_status")
async def update_payment_status(
    request: Request,
    payment_item_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    admin, admin_org = get_current_admin_with_org(request, db) 

    allowed_statuses = ["Unpaid", "Paid", "NOT RESPONSIBLE"]
    if status not in allowed_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {status}. Allowed statuses are: {allowed_statuses}")

    payment_item = db.query(models.PaymentItem).get(payment_item_id)
    if not payment_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment item {payment_item_id} not found")

    old_status_text = "Unpaid" 
    if payment_item.is_not_responsible:
        old_status_text = "NOT RESPONSIBLE"
    elif payment_item.is_paid:
        old_status_text = "Paid"
    elif payment_item.is_past_due:
        old_status_text = "Past Due"

    user_affected = db.query(models.User).filter(models.User.id == payment_item.user_id).first()
    user_name_affected = f"{user_affected.first_name} {user_affected.last_name}" if user_affected else "Unknown User"

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

    # Log the action
    description = f"Admin '{admin.first_name} {admin.last_name}' updated payment status for '{user_name_affected}' (Item ID: {payment_item_id}) from '{old_status_text}' to '{status}'."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Payment Status Update",
        description=description,
        request=request,
        target_entity_type="PaymentItem",
        target_entity_id=payment_item_id
    )

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

    posts = db.query(models.BulletinBoard).options(
        joinedload(models.BulletinBoard.admin)
    ).join(models.Admin).join(models.Admin.organizations).filter(
        models.Organization.id == admin_org.id
    ).order_by(models.BulletinBoard.created_at.desc()).all()

    wiki_posts = db.query(models.RuleWikiEntry).filter(
        models.RuleWikiEntry.organization_id == admin_org.id
    ).order_by(models.RuleWikiEntry.updated_at.desc()).all()

    context = await get_base_template_context(request, db)
    context.update({
        "posts": posts,
        "wiki_posts": wiki_posts 
    })
    return templates.TemplateResponse("admin_dashboard/admin_bulletin_board.html", context)

# --- Rules & Wiki specific: New Route for creating Rule/Wiki entries ---
@router.post('/admin/rules_wiki', response_class=RedirectResponse, name='admin_post_rule_wiki')
async def admin_post_rule_wiki(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    content: str = Form(...),
    image: Optional[UploadFile] = File(None), 
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)

    image_path = None
    if image and image.filename: 
        image_path = await handle_file_upload(
            image,
            WIKI_IMAGES_SUBDIRECTORY, 
            ["image/jpeg", "image/png", "image/gif", "image/svg+xml"],
            max_size_bytes=5 * 1024 * 1024 
        )

    db_rule_wiki = models.RuleWikiEntry(
        title=title,
        category=category,
        content=content,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        image_path=image_path 
    )
    db.add(db_rule_wiki)
    db.commit()
    db.refresh(db_rule_wiki)

    # Log the action
    description = f"Admin '{admin.first_name} {admin.last_name}' created Rule/Wiki entry: '{db_rule_wiki.title}'."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Rule/Wiki Entry Created",
        description=description,
        request=request,
        target_entity_type="RuleWikiEntry",
        target_entity_id=db_rule_wiki.id
    )

    return RedirectResponse(url=request.url_for('admin_bulletin_board'), status_code=status.HTTP_303_SEE_OTHER)


# --- Rules & Wiki specific: Route for displaying edit form ---
@router.get('/admin/rules_wiki/edit/{post_id}', name='admin_edit_rule_wiki')
async def admin_edit_rule_wiki(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)

    rule_wiki_entry = db.query(models.RuleWikiEntry).filter(
        models.RuleWikiEntry.id == post_id,
        models.RuleWikiEntry.organization_id == admin_org.id 
    ).first()

    if not rule_wiki_entry:
        raise HTTPException(status_code=404, detail="Rule/Wiki entry not found or you don't have permission.")
       
    redirect_url = request.url_for('admin_bulletin_board') + f"?edit_wiki_post_id={post_id}"
    return RedirectResponse(url=redirect_url, status_code=302)

@router.post('/admin/rules_wiki/update/{post_id}', name='admin_update_rule_wiki')
async def admin_update_rule_wiki(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)

    rule_wiki_entry = db.query(models.RuleWikiEntry).filter(
        models.RuleWikiEntry.id == post_id,
        models.RuleWikiEntry.organization_id == admin_org.id
    ).first()

    if not rule_wiki_entry:
        raise HTTPException(status_code=404, detail="Rule/Wiki entry not found.")

    form = await request.form()
    rule_wiki_entry.title = form.get('title')
    rule_wiki_entry.category = form.get('category')
    rule_wiki_entry.content = form.get('content')
    uploaded_image = form.get('image')
    if uploaded_image and uploaded_image.filename:
        pass 

    db.add(rule_wiki_entry)
    db.commit()
    db.refresh(rule_wiki_entry)

    return RedirectResponse(url=request.url_for('admin_bulletin_board'), status_code=302)


# --- Rules & Wiki specific: Route for updating Rule/Wiki entries ---
@router.post('/admin/rules_wiki/edit/{post_id}', response_class=RedirectResponse, name='admin_update_rule_wiki')
async def admin_update_rule_wiki(
    request: Request,
    post_id: int,
    title: str = Form(...),
    category: str = Form(...),
    content: str = Form(...),
    image: Optional[UploadFile] = File(None), 
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)

    rule_wiki_entry = db.query(models.RuleWikiEntry).filter(
        models.RuleWikiEntry.id == post_id,
        models.RuleWikiEntry.organization_id == admin_org.id
    ).first()

    if not rule_wiki_entry:
        raise HTTPException(status_code=404, detail="Rule/Wiki entry not found or you don't have permission.")

    old_title = rule_wiki_entry.title
    old_category = rule_wiki_entry.category
    old_content_snippet = rule_wiki_entry.content[:50]

    if image and image.filename:
        new_image_path = await handle_file_upload(
            image,
            WIKI_IMAGES_SUBDIRECTORY, 
            ["image/jpeg", "image/png", "image/gif", "image/svg+xml"],
            max_size_bytes=5 * 1024 * 1024, 
            old_file_path=rule_wiki_entry.image_path 
        )
        rule_wiki_entry.image_path = new_image_path


    rule_wiki_entry.title = title
    rule_wiki_entry.category = category
    rule_wiki_entry.content = content

    db.add(rule_wiki_entry)
    db.commit()
    db.refresh(rule_wiki_entry)

    # Log the action
    description = (
        f"Admin '{admin.first_name} {admin.last_name}' updated Rule/Wiki entry '{old_title}' (ID: {post_id}). "
        f"Title changed from '{old_title}' to '{title}'. "
        f"Category changed from '{old_category}' to '{category}'. "
        f"Content updated (snippet: '{old_content_snippet}...' to '{content[:50]}...')."
    )
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Rule/Wiki Entry Updated",
        description=description,
        request=request,
        target_entity_type="RuleWikiEntry",
        target_entity_id=post_id
    )

    return RedirectResponse(url=request.url_for('admin_bulletin_board'), status_code=status.HTTP_303_SEE_OTHER)


# --- Rules & Wiki specific: Route for deleting Rule/Wiki entries ---
@router.post('/admin/rules_wiki/delete/{post_id}', response_class=RedirectResponse, name='admin_delete_rule_wiki')
async def admin_delete_rule_wiki(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)

    rule_wiki_entry = db.query(models.RuleWikiEntry).filter(
        models.RuleWikiEntry.id == post_id,
        models.RuleWikiEntry.organization_id == admin_org.id
    ).first()

    if not rule_wiki_entry:
        raise HTTPException(status_code=404, detail="Rule/Wiki entry not found or you don't have permission.")

    title_deleted = rule_wiki_entry.title
    
    if rule_wiki_entry.image_path:
        delete_file_from_path(rule_wiki_entry.image_path)

    db.delete(rule_wiki_entry)
    db.commit()

    # Log the action
    description = f"Admin '{admin.first_name} {admin.last_name}' deleted Rule/Wiki entry: '{title_deleted}' (ID: {post_id})."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=admin_org.id,
        action_type="Rule/Wiki Entry Deleted",
        description=description,
        request=request,
        target_entity_type="RuleWikiEntry",
        target_entity_id=post_id
    )

    return RedirectResponse(url=request.url_for('admin_bulletin_board'), status_code=status.HTTP_303_SEE_OTHER)



@app.get("/api/events/{event_id}/participants", response_model=List[schemas.ParticipantResponse])
async def get_event_participants_api(event_id: int, db: Session = Depends(get_db)):
    """
    Fetches the list of participants for a given event ID.
    Returns a list of dictionaries, each with a 'name' key.
    """
    event = db.query(models.Event).options(joinedload(models.Event.participants)).filter(
        models.Event.event_id == event_id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Use the existing participants_list_json property from the Event model
    # FastAPI's JSONResponse will automatically serialize this list of dicts
    # according to the response_model.
    return event.participants_list_json

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

    # Log the action
    description = f"Admin '{admin.first_name} {admin.last_name}' created expense: '{db_expense.description}' for {db_expense.amount:.2f} in category '{db_expense.category or 'Uncategorized'}'."
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=organization.id,
        action_type="Expense Created",
        description=description,
        request=request,
        target_entity_type="Expense",
        target_entity_id=db_expense.id
    )

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
    organization_data: schemas.OrganizationCreate,
    db: Session = Depends(get_db)
):
    
    if db.query(models.Organization).filter(models.Organization.name == organization_data.name).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Organization with name '{organization_data.name}' already exists.")
    if db.query(models.Organization).filter(models.Organization.primary_course_code == organization_data.primary_course_code).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Organization with primary course code '{organization_data.primary_course_code}' already exists.")

    custom_palette = crud.generate_custom_palette(organization_data.theme_color)
    suggested_filename = f"{organization_data.name.lower().replace(' ', '_')}_logo.png"
    logo_upload_path = f"/static/images/{suggested_filename}"

    new_org = models.Organization(
        name=organization_data.name, theme_color=organization_data.theme_color,
        primary_course_code=organization_data.primary_course_code,
        custom_palette=custom_palette, logo_url=logo_upload_path
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    logging.info(f"Action Required: Please upload the organization logo to your web server at the path: {new_org.logo_url}. Suggested filename: {suggested_filename}")
    
    # Log the action
    admin_id_for_log = request.session.get("admin_id") or 0 
    description = f"Organization '{new_org.name}' created with primary course code '{new_org.primary_course_code}'."
    await crud.create_admin_log(
        db=db,
        admin_id=admin_id_for_log, 
        organization_id=new_org.id,
        action_type="Organization Created",
        description=description,
        request=request,
        target_entity_type="Organization",
        target_entity_id=new_org.id
    )

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
    new_admin = models.Admin(first_name=admin_data.first_name, last_name=admin_data.last_name, email=admin_data.email, password=hashed_password, role="Admin", position=getattr(admin_data, "position", None))
    db.add(new_admin)
    db.flush()

    if admin_data.organization_id:
        organization = db.get(models.Organization, admin_data.organization_id)
        if organization: new_admin.organizations.append(organization)
        else: logging.warning(f"Organization with ID {admin_data.organization_id} not found. Admin created without organization link.")
    
    db.commit()
    db.refresh(new_admin)

    # Log the action
    admin_performing_action = request.session.get("admin_id") 
    admin_org_id = admin_data.organization_id 

    description = f"Admin '{admin_performing_action or 'System'}' created new admin user: '{new_admin.first_name} {new_admin.last_name}' with email '{new_admin.email}' and role '{new_admin.role}'."
    await crud.create_admin_log(
        db=db,
        admin_id=admin_performing_action or 0, 
        organization_id=admin_org_id,
        action_type="Admin User Created",
        description=description,
        request=request,
        target_entity_type="Admin",
        target_entity_id=new_admin.admin_id
    )

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
    
    old_theme_color = organization.theme_color 
    old_custom_palette = organization.custom_palette 

    organization.theme_color = theme_update.new_theme_color
    organization.custom_palette = crud.generate_custom_palette(theme_update.new_theme_color)
    db.add(organization)
    db.commit()
    db.refresh(organization)

    # Log the action
    description = (
        f"Admin '{admin.first_name} {admin.last_name}' updated organization '{organization.name}' (ID: {org_id}) "
        f"theme color from '{old_theme_color}' to '{organization.theme_color}' and regenerated palette."
    )
    await crud.create_admin_log(
        db=db,
        admin_id=admin.admin_id,
        organization_id=organization.id,
        action_type="Organization Theme Updated",
        description=description,
        request=request,
        target_entity_type="Organization",
        target_entity_id=organization.id
    )

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
    
    old_logo_url = organization.logo_url 
    
    if organization.logo_url and organization.logo_url != request.url_for('static', path='images/patrick_logo.jpg'):
        delete_file_from_path(organization.logo_url)

    file_path = STATIC_DIR / "images" / suggested_filename 
    file_path.parent.mkdir(parents=True, exist_ok=True) 

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(logo_file.file, buffer)
        logo_url = f"/static/images/{suggested_filename}" 
        organization.logo_url = logo_url
        db.add(organization)
        db.commit()
        db.refresh(organization)

        # Log the action
        description = (
            f"Admin '{admin.first_name} {admin.last_name}' updated organization '{organization.name}' (ID: {org_id}) "
            f"logo from '{old_logo_url or 'None'}' to '{logo_url}'."
        )
        await crud.create_admin_log(
            db=db,
            admin_id=admin.admin_id,
            organization_id=organization.id,
            action_type="Organization Logo Updated",
            description=description,
            request=request,
            target_entity_type="Organization",
            target_entity_id=organization.id
        )

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

    # --- PayMaya API setup (no change) ---
    public_api_key = "pk-Z0OSzLvIcOI2UIvDhdTGVVfRSSeiGStnceqwUE7n0Ah"
    encoded_key = base64.b64encode(f"{public_api_key}:".encode()).decode()
    url = "https://pg-sandbox.paymaya.com/checkout/v1/checkouts"
    headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Basic {encoded_key}"}

    # --- Retrieve PaymentItem ---
    payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if not payment_item:
        logging.error(f"Payment item not found for payment_item_id={payment_item_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment item not found")
    
    # --- CRITICAL NEW CHECK: Prevent payment if item is already paid ---
    # This check needs your PaymentItem model to have an 'is_paid' boolean attribute.
    # If not, you might need to check if there's an associated successful payment instead.
    if hasattr(payment_item, 'is_paid') and payment_item.is_paid: 
        logging.warning(f"Attempted to create payment for already paid PaymentItem ID: {payment_item_id}. User ID: {user.id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This item has already been paid for.")

    # --- REVISED LOGIC: Check for existing reusable payment (to prevent duplicates) ---
    # We are looking for any payment record linked to this payment_item and user
    # that is NOT yet 'success' and NOT explicitly 'failed'.
    # We prioritize those that haven't yet received a paymaya_payment_id.
    
    existing_reusable_payment = db.query(models.Payment).filter(
        models.Payment.payment_item_id == payment_item_id,
        models.Payment.user_id == user.id,
        models.Payment.status.notin_(['success', 'failed']) # This captures 'pending', 'null', etc.
    ).order_by(
        models.Payment.paymaya_payment_id.is_(None).desc() # Prefer payments that haven't initiated PayMaya yet
    ).first()

    db_payment = None
    if existing_reusable_payment:
        db_payment = existing_reusable_payment
        db.refresh(db_payment)
        # Ensure its status is 'pending' if it wasn't already (e.g., if it was NULL)
        if db_payment.status != "pending":
            db_payment.status = "pending"
            db.add(db_payment)
            # No db.flush() needed here, the final db.commit() in the try block handles it for this update
        logging.info(f"Reusing existing payment (ID: {db_payment.id}, Current Status: {db_payment.status}) for payment_item_id: {payment_item_id}. PayMaya ID: {db_payment.paymaya_payment_id}")
    else:
        # --- Create a NEW initial Payment record ONLY if no reusable one exists ---
        db_payment = crud.create_payment(db, amount=payment_item.fee, user_id=user.id, payment_item_id=payment_item_id)
        db.add(db_payment)
        db.flush() # Essential to get the ID for db_payment immediately and make it visible

        # Explicitly set status to 'pending' for a brand new payment
        db_payment.status = "pending" 
        db.add(db_payment) # Mark as dirty for update
        
        logging.info(f"Created new payment (ID: {db_payment.id}) and set status to 'pending' for payment_item_id: {payment_item_id}.")

    # --- Link payment to StudentShirtOrder if applicable (no change) ---
    if payment_item.student_shirt_order_id:
        shirt_order = db.query(models.StudentShirtOrder).filter(
            models.StudentShirtOrder.id == payment_item.student_shirt_order_id
        ).first()

        if shirt_order:
            if shirt_order.payment_id != db_payment.id: 
                shirt_order.payment_id = db_payment.id
                db.add(shirt_order) 
                db.commit() # Commit the update to the shirt_order now to ensure link is saved
                db.refresh(shirt_order) 

            logging.info(
                f"Linked PayMaya payment to StudentShirtOrder: payment_id={db_payment.id}, "
                f"shirt_order_id={shirt_order.id}"
            )
        else:
            logging.warning(
                f"PaymentItem {payment_item.id} has student_shirt_order_id "
                f"{payment_item.student_shirt_order_id} but no matching StudentShirtOrder found."
            )
    
    # --- PayMaya Payload (fixed typo and added UTC for request reference) ---
    payload = {
        "totalAmount": {"currency": "PHP", "value": payment_item.fee},
        "requestReferenceNumber": f"shirt-order-{payment_item_id}-{db_payment.id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}", # <-- Using UTC now
        "redirectUrl": {
            "success": f"http://127.0.0.1:8000/Success?paymentId={db_payment.id}&paymentItemId={payment_item_id}",
            "failure": f"http://127.0.0.1:8000/Failure?paymentId={db_payment.id}&paymentItemId={payment_item_id}",
            "cancel": f"http://127.0.0.1:8000/Cancel?paymentId={db_payment.id}&paymentItemId={payment_item_id}" 
        },
        "metadata": {
            "pf": {"smi": "CVSU", "smn": "Undisputed", "mci": "Imus City", "mpc": "608", "mco": "PHL", "postalCode": "1554", "contactNo": "0211111111", "addressLine1": "Palico"}
            , "subMerchantRequestReferenceNumber": f"shirt-order-subref-{payment_item_id}" 
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        payment_data = response.json()
        paymaya_payment_id = payment_data.get("checkoutId")
        
        # Update the PayMaya specific ID on the (newly created or reused) db_payment
        crud.update_payment(db, payment_id=db_payment.id, paymaya_payment_id=paymaya_payment_id)
        db.commit() # Commit all changes
        
        logging.info(f"PayMaya checkout session created successfully: payment_id={db_payment.id}, paymaya_payment_id={paymaya_payment_id}")
        return payment_data
    except requests.exceptions.RequestException as e:
        db.rollback() 
        crud.update_payment(db, payment_id=db_payment.id, status="failed") 
        db.commit() 
        logging.error(f"PayMaya API error during checkout creation for payment_id={db_payment.id}: {e.response.text if hasattr(e.response, 'text') else str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"PayMaya API error: {e.response.text if hasattr(e.response, 'text') else str(e)}")

@router.post("/payments/paymaya/create", response_class=JSONResponse, name="paymaya_create_payment")
async def paymaya_create_payment(
    request: Request,
    payment_item_id: int = Form(...),
    db: Session = Depends(get_db),
):
    user, _ = get_current_user_with_org(request, db)

    # --- PayMaya API setup (no change) ---
    public_api_key = "pk-Z0OSzLvIcOI2UIvDhdTGVVfRSSeiGStnceqwUE7n0Ah"
    encoded_key = base64.b64encode(f"{public_api_key}:".encode()).decode()
    url = "https://pg-sandbox.paymaya.com/checkout/v1/checkouts"
    headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Basic {encoded_key}"}

    # --- Retrieve PaymentItem ---
    payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if not payment_item:
        logging.error(f"Payment item not found for payment_item_id={payment_item_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment item not found")
    
    # --- CRITICAL NEW CHECK: Prevent payment if item is already paid ---
    if payment_item.is_paid: # Assuming PaymentItem has an 'is_paid' boolean flag
        logging.warning(f"Attempted to create payment for already paid PaymentItem ID: {payment_item_id}. User ID: {user.id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This item has already been paid for.")

    # --- Re-confirm reusable payment logic ---
    # We are looking for any payment record linked to this payment_item and user
    # that is NOT yet 'success' and NOT explicitly 'failed'.
    # We prioritize those that haven't yet received a paymaya_payment_id.
    
    existing_reusable_payment = db.query(models.Payment).filter(
        models.Payment.payment_item_id == payment_item_id,
        models.Payment.user_id == user.id,
        models.Payment.status.notin_(['success', 'failed']) # This captures 'pending', 'null', etc.
    ).order_by(
        models.Payment.paymaya_payment_id.is_(None).desc() # Prefer payments that haven't initiated PayMaya yet
    ).first()

    db_payment = None
    if existing_reusable_payment:
        db_payment = existing_reusable_payment
        db.refresh(db_payment)
        # Ensure its status is 'pending' if it wasn't already (e.g., if it was NULL)
        if db_payment.status != "pending":
            db_payment.status = "pending"
            db.add(db_payment)
            # No db.flush() needed here, the final db.commit() in the try block handles it for this update
        logging.info(f"Reusing existing payment (ID: {db_payment.id}, Current Status: {db_payment.status}) for payment_item_id: {payment_item_id}. PayMaya ID: {db_payment.paymaya_payment_id}")
    else:
        # --- Create a NEW initial Payment record ONLY if no reusable one exists ---
        db_payment = crud.create_payment(db, amount=payment_item.fee, user_id=user.id, payment_item_id=payment_item_id)
        db.add(db_payment)
        db.flush() # Essential to get the ID for db_payment immediately and make it visible

        # Explicitly set status to 'pending' for a brand new payment
        db_payment.status = "pending" 
        db.add(db_payment) # Mark as dirty for update
        
        logging.info(f"Created new payment (ID: {db_payment.id}) and set status to 'pending' for payment_item_id: {payment_item_id}.")

    # --- Link payment to StudentShirtOrder if applicable (no change) ---
    if payment_item.student_shirt_order_id:
        shirt_order = db.query(models.StudentShirtOrder).filter(
            models.StudentShirtOrder.id == payment_item.student_shirt_order_id
        ).first()

        if shirt_order:
            if shirt_order.payment_id != db_payment.id: 
                shirt_order.payment_id = db_payment.id
                db.add(shirt_order) 
                db.commit() # Commit the update to the shirt_order now to ensure link is saved
                db.refresh(shirt_order) 

            logging.info(
                f"Linked PayMaya payment to StudentShirtOrder: payment_id={db_payment.id}, "
                f"shirt_order_id={shirt_order.id}"
            )
        else:
            logging.warning(
                f"PaymentItem {payment_item.id} has student_shirt_order_id "
                f"{payment_item.student_shirt_order_id} but no matching StudentShirtOrder found."
            )
    
    # --- PayMaya Payload (fixed typo) ---
    payload = {
        "totalAmount": {"currency": "PHP", "value": payment_item.fee},
        "requestReferenceNumber": f"shirt-order-{payment_item_id}-{db_payment.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "redirectUrl": {
            "success": f"http://127.0.0.1:8000/Success?paymentId={db_payment.id}&paymentItemId={payment_item_id}",
            "failure": f"http://127.0.0.1:8000/Failure?paymentId={db_payment.id}&paymentItemId={payment_item_id}",
            "cancel": f"http://127.0.0.1:8000/Cancel?paymentId={db_payment.id}&paymentItemId={payment_item_id}" 
        },
        "metadata": {
            "pf": {"smi": "CVSU", "smn": "Undisputed", "mci": "Imus City", "mpc": "608", "mco": "PHL", "postalCode": "1554", "contactNo": "0211111111", "addressLine1": "Palico"}
            , "subMerchantRequestReferenceNumber": f"shirt-order-subref-{payment_item_id}" 
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        payment_data = response.json()
        paymaya_payment_id = payment_data.get("checkoutId")
        
        # Update the PayMaya specific ID on the (newly created or reused) db_payment
        crud.update_payment(db, payment_id=db_payment.id, paymaya_payment_id=paymaya_payment_id)
        db.commit() # Commit all changes
        
        logging.info(f"PayMaya checkout session created successfully: payment_id={db_payment.id}, paymaya_payment_id={paymaya_payment_id}")
        return payment_data
    except requests.exceptions.RequestException as e:
        db.rollback() 
        crud.update_payment(db, payment_id=db_payment.id, status="failed") 
        db.commit() 
        logging.error(f"PayMaya API error during checkout creation for payment_id={db_payment.id}: {e.response.text if hasattr(e.response, 'text') else str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"PayMaya API error: {e.response.text if hasattr(e.response, 'text') else str(e)}")

# Success Callback
@router.get("/Success", response_class=HTMLResponse, name="payment_success")
async def payment_success(
    request: Request,
    paymentId: int = Query(...),
    paymentItemId: int = Query(...),
    db: Session = Depends(get_db),
):
    # Log incoming request details
    logging.info(f"Payment success callback received: paymentId={paymentId}, paymentItemId={paymentItemId}")

    # 1. Retrieve the existing Payment record that needs to be updated
    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if not payment:
        logging.error(f"Payment record not found for paymentId={paymentId}. This might indicate an invalid callback or a race condition.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

    # Refresh the payment object to ensure it has the latest state from the DB
    db.refresh(payment) 
    logging.info(f"Retrieved payment (ID: {payment.id}, Current Status: {payment.status}, User ID: {payment.user_id}) for update.")

    # Prevent re-processing already successful payments for the same paymentId
    if payment.status == "success":
        logging.warning(f"Payment ID {paymentId} is already marked as success. Skipping further updates to prevent duplicate processing.")
        # Although it's already successful, we still want to show the success page.
        payment_item = crud.get_payment_item_by_id(db, payment_item_id=paymentItemId)
        if payment_item:
            logging.info(f"Associated Payment Item {payment_item.id} already processed or found.")
        
        context = await get_base_template_context(request, db)
        context.update({
            "payment_id": payment.paymaya_payment_id if payment.paymaya_payment_id else payment.id, 
            "payment_item_id": paymentItemId, 
            "payment": payment, 
            "payment_item": payment_item
        })
        return templates.TemplateResponse("student_dashboard/payment_success.html", context)


    # 2. Update the general payment status to "success"
    try:
        updated_payment = crud.update_payment(db, payment_id=payment.id, status="success")
        if not updated_payment:
            logging.error(f"Failed to update payment status for paymentId={paymentId} to 'success'. CRUD operation returned None.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update payment status.")
        logging.info(f"Payment ID {payment.id} status successfully updated to 'success'.")
    except Exception as e:
        logging.exception(f"Exception while updating payment status for paymentId={payment.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating payment status.")


    # 3. Retrieve and mark the PaymentItem linked to this successful payment
    payment_item = crud.get_payment_item_by_id(db, payment_item_id=paymentItemId)
    if not payment_item:
        logging.error(f"Associated Payment Item not found for paymentItemId={paymentItemId}. This is critical for Payment ID {payment.id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated Payment Item not found.")

    if not payment_item.is_paid: # Only mark as paid if not already
        try:
            crud.mark_payment_item_as_paid(db, payment_item_id=paymentItemId)
            logging.info(f"Payment Item ID {paymentItemId} marked as paid successfully.")
        except Exception as e:
            logging.exception(f"Exception while marking Payment Item {paymentItemId} as paid: {e}")
            # Decide if this should halt the process or just log and continue
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error marking payment item as paid.")
    else:
        logging.info(f"Payment Item ID {paymentItemId} was already marked as paid. No action needed.")

    # 4. Check if this PaymentItem is for a StudentShirtOrder
    if payment_item.student_shirt_order_id:
        logging.info(f"Payment Item {paymentItemId} is linked to Student Shirt Order ID: {payment_item.student_shirt_order_id}.")
        shirt_order = crud.get_student_shirt_order_by_id(db, order_id=payment_item.student_shirt_order_id)
        if shirt_order:
            if shirt_order.status != "paid": # Only update if not already paid
                logging.info(f"Student Shirt Order {shirt_order.id} status is '{shirt_order.status}', attempting to set to 'paid'.")
                order_update_data = schemas.StudentShirtOrderUpdate(status="paid") 
                try:
                    updated_shirt_order = crud.update_student_shirt_order(
                        db=db,
                        order_id=shirt_order.id,
                        order_update=order_update_data 
                    )
                    if updated_shirt_order:
                        logging.info(f"Student Shirt Order {updated_shirt_order.id} status successfully updated to 'paid' via PaymentItem {payment_item.id}.")
                        
                        # Optional: Create a notification for admins/organization about the shirt order payment
                        if updated_shirt_order.campaign and updated_shirt_order.campaign.organization_id:
                            organization = db.query(models.Organization).filter(models.Organization.id == updated_shirt_order.campaign.organization_id).first()
                            if organization:
                                for admin in organization.admins:
                                    message = f"Shirt Order Payment: Student {updated_shirt_order.student_name} has paid for Shirt Order ID: {updated_shirt_order.id} (Campaign: {updated_shirt_order.campaign.title})."
                                    crud.create_notification(db, message, 
                                                            admin_id=admin.admin_id, # <--- FIXED: use admin.admin_id
                                                            organization_id=organization.id, 
                                                            notification_type="shirt_order_payment",
                                                            payment_id=payment.id, 
                                                            url=f"/admin/orders/{updated_shirt_order.id}", 
                                                            event_identifier=f"shirt_order_payment_admin_{admin.admin_id}_order_{updated_shirt_order.id}") # <--- FIXED: use admin.admin_id
                                    logging.info(f"Notification created for admin {admin.admin_id} for shirt order payment {updated_shirt_order.id}.")
                            else:
                                logging.warning(f"Organization not found for campaign {updated_shirt_order.campaign.id} linked to shirt order {updated_shirt_order.id}.")
                        else:
                            logging.info(f"No campaign or organization found for shirt order {updated_shirt_order.id} for notification.")
                    else:
                        logging.warning(f"Failed to update status for Student Shirt Order {shirt_order.id} linked to PaymentItem {payment_item.id}. CRUD operation returned None.")
                except Exception as e:
                    logging.exception(f"Exception while updating Student Shirt Order {shirt_order.id} status: {e}")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating shirt order status.")
            else:
                logging.info(f"Student Shirt Order {shirt_order.id} was already marked as paid. No status update needed.")
        else:
            logging.warning(f"PaymentItem {payment_item.id} linked to non-existent shirt_order_id {payment_item.student_shirt_order_id}. Data inconsistency detected.")
    else:
        # This block contains your existing logic for general fees payment items
        logging.info(f"Payment Item {paymentItemId} is for general fees.")
        user = db.query(models.User).filter(models.User.id == payment.user_id).first()
        if user and user.organization and payment_item.academic_year and payment_item.semester: 
            logging.info(f"User {user.id} and organization {user.organization.id} found for general fee payment.")
            for admin in user.organization.admins:
                message = f"Payment Successful: {user.first_name} {user.last_name} has successfully paid {payment.amount} for {payment_item.academic_year} {payment_item.semester} fees."
                crud.create_notification(db, message, admin_id=admin.admin.id, organization_id=user.organization.id, notification_type="payment_success",
                                         payment_id=payment.id, 
                                         url=f"/admin/payments/total_members?student_number={user.student_number}",
                                         event_identifier=f"payment_success_admin_{admin.admin.id}_payment_{payment.id}")
                logging.info(f"Notification created for admin {admin.admin.id} for general fee payment {payment.id}.")
        else:
            logging.warning(f"Could not find user, organization, or academic year/semester for general fee payment {payment.id}. Notification skipped.")
    
    # Commit all changes at once (payment, payment_item, and potentially shirt_order)
    try:
        db.commit() 
        logging.info(f"Database transaction committed successfully for payment_id={payment.id}.")
    except Exception as e:
        db.rollback() # Rollback on error to prevent partial updates
        logging.exception(f"Failed to commit transaction for payment_id={payment.id}. Rolling back changes: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database transaction failed during commit.")

    logging.info(f"PayMaya payment success processing completed for payment_id={payment.id}, paymaya_payment_id={payment.paymaya_payment_id}. Redirecting to success page.")
    
    context = await get_base_template_context(request, db)
    context.update({
        "payment_id": payment.paymaya_payment_id if payment.paymaya_payment_id else payment.id, 
        "payment_item_id": paymentItemId, 
        "payment": payment, 
        "payment_item": payment_item
    })
    
    return templates.TemplateResponse("student_dashboard/payment_success.html", context)

# Payment Failure Callback
@router.get("/Failure", response_class=HTMLResponse, name="payment_failure")
async def payment_failure(request: Request, paymentId: int = Query(...), db: Session = Depends(get_db)):
    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if not payment: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")
    db.refresh(payment) 
    
    crud.update_payment(db, payment_id=payment.id, status="failed")
    payment_item = crud.get_payment_item_by_id(db, payment.payment_item_id)

    db.commit() 
    logging.info(f"PayMaya payment failure: payment_id={payment.id}, paymaya_payment_id={payment.paymaya_payment_id}")
    context = await get_base_template_context(request, db)
    context.update({"payment_id": payment.paymaya_payment_id, "payment_item": payment_item})
    return templates.TemplateResponse("student_dashboard/payment_failure.html", context)

# Payment Cancellation Callback
@router.get("/Cancel", response_class=HTMLResponse, name="payment_cancel")
async def payment_cancel(request: Request, paymentId: int = Query(...), db: Session = Depends(get_db)):
    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if not payment: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")
    db.refresh(payment) 
    
    crud.update_payment(db, payment_id=payment.id, status="cancelled")
    payment_item = crud.get_payment_item_by_id(db, payment.payment_item_id)

    db.commit() 
    logging.info(f"PayMaya payment cancelled: payment_id={payment.id}, paymaya_payment_id={payment.paymaya_payment_id}")
    context = await get_base_template_context(request, db)
    context.update({"payment_id": payment.paymaya_payment_id, "payment_item": payment_item})
    return templates.TemplateResponse("student_dashboard/payment_cancel.html", context)

# Add the new admin_logs router here
app.include_router(router)

# User Logout
@app.get("/logout", response_class=RedirectResponse, name="logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")
    
    if admin_id:
        admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
        
        if admin:
            organization_id_to_log = None
            
            admin_organizations = db.query(models.Organization)\
                .join(models.organization_admins)\
                .filter(models.organization_admins.c.admin_id == admin.admin_id)\
                .limit(1).first()

            if admin_organizations: 
                organization_id_to_log = admin_organizations.id

            description = f"Admin '{admin.first_name} {admin.last_name}' successfully logged out."
            await crud.create_admin_log(
                db=db,
                admin_id=admin.admin_id,
                organization_id=organization_id_to_log, 
                action_type="Admin Logout",
                description=description,
                request=request
            )
            db.commit() 
        else:
            print(f"Warning: Admin with ID {admin_id} not found during logout process.")

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
                                         notification_type="past_due_payments", 
                                         payment_item_id=None, 
                                         url=f"/admin/payments/total_members?student_number={past_due_user.student_number}",
                                         event_identifier=f"admin_past_due_user_{past_due_user.id}_admin_{admin.admin_id}")
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
                                         notification_type="user_past_due", 
                                         payment_item_id=None,
                                         url="/Payments",
                                         event_identifier=f"user_past_due_alert_user_{user_id}")
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
    wiki_posts = []  
    hearted_post_ids = set()

    if user_org:
        posts = db.query(models.BulletinBoard)\
                    .join(models.Admin).join(models.Admin.organizations)\
                    .filter(models.Organization.id == user_org.id)\
                    .order_by(desc(models.BulletinBoard.created_at)).all()

        wiki_posts = db.query(models.RuleWikiEntry)\
                        .filter(models.RuleWikiEntry.organization_id == user_org.id)\
                        .order_by(desc(models.RuleWikiEntry.created_at)).all()

        if user:
            user_likes = db.query(models.UserLike).filter(models.UserLike.user_id == user.id).all()
            hearted_post_ids = {like.post_id for like in user_likes}

    context = await get_base_template_context(request, db)
    context.update({"posts": posts, "hearted_posts": hearted_post_ids, "wiki_posts": wiki_posts})

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

        # --- CORRECTED LOGIC STARTS HERE ---
        # First, ensure payment_item itself is not None.
        # Then, ensure all necessary attributes are not None.
        if (
            payment_item is not None and
            payment_item.academic_year is not None and
            payment_item.semester is not None and
            payment_item.fee is not None and
            payment_item.due_date is not None and
            # Also ensure payment's own critical attributes are not None
            payment.amount is not None and
            payment.status is not None and
            payment.created_at is not None
        ):
            status_text = payment.status
            if status_text == "pending": status_text = "Pending"
            elif status_text == "success": status_text = "Paid"
            elif status_text == "failed": status_text = "Failed"
            elif status_text == "cancelled": status_text = "Cancelled"
            payment_history_data.append({"item": payment, "status": status_text})
        else:
            # If payment_item is None, or any required attribute is None,
            # this entry will be skipped, maintaining your original 'continue' behavior.
            logging.warning(f"Skipping payment ID {payment.id} due to missing PaymentItem or incomplete data.")
            continue
        # --- CORRECTED LOGIC ENDS HERE ---

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
@app.get("/student_dashboard/detailed_monthly_report_page", response_class=HTMLResponse)
async def detailed_monthly_report_page(
    request: Request, month: str = Query(...), year: int = Query(...), db: Session = Depends(get_db)
):
    user, _ = get_current_user_with_org(request, db) 
    context = await get_base_template_context(request, db)
    context.update({"month": month, "year": year})
    return templates.TemplateResponse("student_dashboard/detailed_monthly_report.html", context)

# Detailed Monthly Report Data (User)
@app.get("/api/detailed_monthly_report", response_class=JSONResponse)
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
            relevant_date = (item.updated_at or item.created_at) 
            if relevant_date and start_date_of_month <= relevant_date <= end_date_of_month: 
                category_name = f"AY {item.academic_year} - {item.semester} Fee" if item.academic_year and item.semester else "Miscellaneous Fee"
                status_str = "Paid" if item.is_paid else ("Past Due" if not item.is_paid and item.due_date and item.due_date < date.today() else "Unpaid")
                all_financial_events.append((relevant_date, f"Your Payment - {category_name}", item.fee if item.is_paid else 0.00, 0.00, status_str, item.fee, item))

    org_id_for_query = user_org.id if user_org else None
    if report_type in ['organization', 'combined', None]:
        org_inflows_query = db.query(models.PaymentItem).join(models.User).filter(models.PaymentItem.is_paid == True, models.User.organization_id == org_id_for_query)
        if report_type in ['user', 'combined', None]: org_inflows_query = org_inflows_query.filter(models.PaymentItem.user_id != user.id)
        
        org_inflows_for_month = org_inflows_query.filter(
            or_(
                and_(models.PaymentItem.updated_at >= start_date_of_month, models.PaymentItem.updated_at <= end_date_of_month),
                and_(models.PaymentItem.created_at >= start_date_of_month, models.PaymentItem.created_at <= end_date_of_month)
            )
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
    
    db.flush()

    current_academic_year_string_start = date.today().year
    if date.today().month < 6:
        current_academic_year_string_start -= 1
        
    start_calculation_date = date(2025, 2, 28)
    
    for i in range(8):
        if i % 2 == 0:
            academic_year_str = f"{current_academic_year_string_start}-{current_academic_year_string_start + 1}"
        else:
            academic_year_str = f"{current_academic_year_string_start}-{current_academic_year_string_start + 1}"
            current_academic_year_string_start += 1

        due_date = start_calculation_date + timedelta(days=i * 6 * 30)
        
        year_level_applicable = (i // 2) + 1
        semester = "1st" if (i % 2) == 0 else "2nd"

        crud.add_payment_item(
            db=db, user_id=new_user.id, academic_year=academic_year_str, semester=semester,
            fee=100.00,
            due_date=due_date,
            year_level_applicable=year_level_applicable,
        )
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
async def get_user_data(
    request: Request,
    db: Session = Depends(get_db),
    dark_mode: bool = Query(False, description="Request dark mode custom palette") 
):
    user_id = request.session.get("user_id")
    admin_id = request.session.get("admin_id")

    current_entity = None
    organization_data = None
    first_name = None
    profile_picture = None
    is_verified_status = None
    organization_theme_color = None

    if user_id:
        current_entity = db.query(models.User).filter(models.User.id == user_id).first()
        if current_entity:
            first_name = current_entity.first_name
            profile_picture = current_entity.profile_picture
            is_verified_status = current_entity.is_verified
            if current_entity.organization:
                organization_data = schemas.Organization.model_validate(current_entity.organization)
                organization_theme_color = current_entity.organization.theme_color 
    elif admin_id:
        current_entity = db.query(models.Admin).options(joinedload(models.Admin.organizations)).filter(models.Admin.admin_id == admin_id).first()
        if current_entity:
            first_name = current_entity.first_name 
            if current_entity.organizations:
                organization_data = schemas.Organization.model_validate(current_entity.organizations[0])
                organization_theme_color = current_entity.organizations[0].theme_color 

    if not current_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user/admin not found in database for provided session ID.")
    if not user_id and not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No authenticated user or admin ID found in session.")

    if organization_data and organization_theme_color:
        generated_palette_json = crud.generate_custom_palette(organization_theme_color, dark_mode)
        
        organization_data.custom_palette = generated_palette_json
    else:
       
        if organization_data:
            organization_data.custom_palette = None


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

            organization_id_to_log = None
            
            admin_organizations = db.query(models.Organization)\
                .join(models.organization_admins)\
                .filter(models.organization_admins.c.admin_id == admin.admin_id)\
                .limit(1).first()

            if admin_organizations: 
                organization_id_to_log = admin_organizations.id
            
            description = f"Admin '{admin.first_name} {admin.last_name}' successfully logged in."
            await crud.create_admin_log(
                db=db,
                admin_id=admin.admin_id,
                organization_id=organization_id_to_log, 
                action_type="Admin Login",
                description=description,
                request=request
            )
            db.commit()

            return {"message": "Admin login successful", "admin_id": admin.admin_id, "user_role": admin.role}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})

# Heart/Unheart Bulletin Posts
@app.post("/bulletin/heart/{post_id}")
async def heart_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db),
    action: str = Form(...)
):
    user, user_org = get_current_user_with_org(request, db)
    if not user: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth required.")

    post = db.query(models.BulletinBoard).options(joinedload(models.BulletinBoard.admin)).get(post_id)
    if not post: raise HTTPException(status_code=404, detail="Post not found.")
    if not post.admin or not post.admin.organizations or post.admin.organizations[0].id != user_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for organization.")

    user_like = db.query(models.UserLike).filter_by(user_id=user.id, post_id=post_id).first()
    is_hearted_by_user = (action == 'heart')

    if action == 'heart':
        if not user_like:
            db.add(models.UserLike(user_id=user.id, post_id=post_id))
            post.heart_count += 1
            crud.create_notification(db, f"{user.first_name} {user.last_name} liked your post: '{post.title}'",
                                     organization_id=user_org.id, admin_id=post.admin_id,
                                     notification_type="bulletin_like", 
                                     bulletin_post_id=post_id, 
                                     url=f"/admin/bulletin_board#{post_id}",
                                     event_identifier=f"bulletin_like_admin_{post.admin_id}_post_{post_id}_user_{user.id}")
    elif action == 'unheart':
        if user_like:
            db.delete(user_like)
            post.heart_count = max(0, post.heart_count - 1) 
    else:
        raise HTTPException(status_code=400, detail="Invalid action.")

    db.commit()
    db.refresh(post)
    return {"heart_count": post.heart_count, "is_hearted_by_user": is_hearted_by_user}

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
                             event_id=event_id, 
                             url=f"/admin/events#{event_id}",
                             event_identifier=f"event_join_admin_{event.admin_id}_event_{event_id}_user_{user.id}")
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
                        user.birthdate = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d")
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
                            user.birthdate = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d")
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

    # Capture changes for logging
    changes = []
    if is_verified is not None and is_verified != original_is_verified_status:
        changes.append(f"Verification status changed from '{original_is_verified_status}' to '{is_verified}'.")

    if not original_is_verified_status and user.is_verified and user.organization_id:
        for admin in db.query(models.Admin).join(models.organization_admins).filter(models.organization_admins.c.organization_id == user.organization_id).all():
            crud.create_notification(db=db, message=f"Member {user.first_name} {user.last_name} has been verified.",
                                     organization_id=user.organization_id, admin_id=admin.admin_id, notification_type="member_verification",
                                     verified_user_id=user.id, 
                                     url=f"/admin/payments/total_members?student_number={user.student_number}",
                                     event_identifier=f"member_verified_admin_{admin.admin_id}_user_{user.id}")
            # Log the admin action of verifying a user (if an admin is logged in)
            admin_id_for_log = request.session.get("admin_id")
            if admin_id_for_log:
                admin_performing_action = db.query(models.Admin).filter(models.Admin.admin_id == admin_id_for_log).first()
                if admin_performing_action:
                    description = f"Admin '{admin_performing_action.first_name} {admin_performing_action.last_name}' verified user: '{user.first_name} {user.last_name}' (ID: {user.id})."
                    await crud.create_admin_log(
                        db=db,
                        admin_id=admin_performing_action.admin_id,
                        organization_id=user.organization_id,
                        action_type="User Verified",
                        description=description,
                        request=request,
                        target_entity_type="User",
                        target_entity_id=user.id
                    )

    db.commit()
    db.refresh(user)
    user.verification_status = "Verified" if user.is_verified else "Not Verified"
    
    # Log general user profile update (if an admin is performing it)
    admin_id_for_log = request.session.get("admin_id")
    if admin_id_for_log and changes: 
        admin_performing_action = db.query(models.Admin).filter(models.Admin.admin_id == admin_id_for_log).first()
        if admin_performing_action:
            description = f"Admin '{admin_performing_action.first_name} {admin_performing_action.last_name}' updated profile for user: '{user.first_name} {user.last_name}' (ID: {user.id}). Changes: {'; '.join(changes)}"
            await crud.create_admin_log(
                db=db,
                admin_id=admin_performing_action.admin_id,
                organization_id=user.organization_id,
                action_type="User Profile Updated (Admin)",
                description=description,
                request=request,
                target_entity_type="User",
                target_entity_id=user.id
            )

    return {"message": "Profile updated successfully", "user": user}

@app.post("/api/auth/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(..., description="The user's current password"),
    new_password: str = Form(..., description="The new password to set"),
    confirm_password: str = Form(..., description="Confirmation of the new password"),
    db: Session = Depends(get_db),
):
    user, _ = get_current_user_with_org(request, db)
    if not crud.verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if crud.verify_password(new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as current password.",
        )
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long.",
        )
    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match.",
        )
    user.hashed_password = crud.get_password_hash(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log the action (if an admin is changing their own password)
    admin_id_for_log = request.session.get("admin_id")
    if admin_id_for_log == user.id: 
        admin_performing_action = db.query(models.Admin).filter(models.Admin.admin_id == admin_id_for_log).first()
        if admin_performing_action:
            description = f"Admin '{admin_performing_action.first_name} {admin_performing_action.last_name}' changed their own password."
            await crud.create_admin_log(
                db=db,
                admin_id=admin_performing_action.admin_id,
                action_type="Admin Password Change",
                description=description,
                request=request,
                target_entity_type="Admin",
                target_entity_id=admin_performing_action.admin_id
            )

    return {"message": "Password updated successfully!"}

@app.post("/api/forgot-password/")
async def forgot_password_endpoint(
    request_data: schemas.ForgotPasswordRequest, 
    request: Request,
    db: Session = Depends(get_db)
):
    identifier = request_data.identifier

    user = crud.get_user(db, identifier=identifier)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with the provided identifier."
        )

    alphabet = string.ascii_uppercase + string.digits
    reset_code = ''.join(secrets.choice(alphabet) for i in range(6))

    db.query(models.PasswordResetToken).filter(models.PasswordResetToken.user_id == user.id).delete()
    db.commit()

    expiration_time = datetime.now() + timedelta(minutes=10) 
    crud.create_password_reset_token(db, user_id=user.id, token=reset_code, expiration=expiration_time)

    sender_email = "ic.markaaron.mayor@cvsu.edu.ph"
    receiver_email = user.email 
    mailtrap_username = "e09c5a4e999a44" 
    mailtrap_password = "a4c986c82c92fd" 

    message = MIMEMultipart("alternative")
    message["Subject"] = "Your Password Reset Code"
    message["From"] = f"Your App Support <{sender_email}>"
    message["To"] = receiver_email

    text = f"""\
    Hi {user.first_name},

    Your password reset code is: {reset_code}

    This code is valid for 10 minutes.

    If you did not request a password reset, please ignore this email.

    Thank you,
    Your App Team
    """
    html = f"""\
    <html>
      <body>
        <p>Hi {user.first_name},</p>
        <p>Your password reset code is: <strong>{reset_code}</strong></p>
        <p>This code is valid for 10 minutes.</p>
        <p>If you did not request a password reset, please ignore this email.</p>
        <p>Thank you,</p>
        <p>Your App Team</p>
      </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    try:
        with smtplib.SMTP("sandbox.smtp.mailtrap.io", 2525) as server:
            server.starttls()
            server.login(mailtrap_username, mailtrap_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        
        # Log the action
        admin_id_for_log = request.session.get("admin_id")
        if admin_id_for_log: 
            admin_performing_action = db.query(models.Admin).filter(models.Admin.admin_id == admin_id_for_log).first()
            if admin_performing_action:
                description = f"Admin '{admin_performing_action.first_name} {admin_performing_action.last_name}' requested a password reset code."
                await crud.create_admin_log(
                    db=db,
                    admin_id=admin_performing_action.admin_id,
                    action_type="Admin Password Reset Request",
                    description=description,
                    request=request,
                    target_entity_type="Admin",
                    target_entity_id=admin_performing_action.admin_id
                )
        else: 
            description = f"User '{user.first_name} {user.last_name}' requested a password reset code."
            pass

        return {"message": "Password reset code sent to your email."}, status.HTTP_200_OK
    except Exception as e:
        print(f"Error sending email: {e}") 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reset code. Please try again later."
        )

@app.post("/api/reset-password/")
async def reset_password_endpoint(
    request_data: schemas.ResetPasswordRequest, 
    request: Request,
    db: Session = Depends(get_db)
):
    identifier = request_data.identifier
    code = request_data.code
    new_password = request_data.new_password

    user = crud.get_user(db, identifier=identifier)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    db_token = crud.get_password_reset_token_by_token(db, code)
    if not db_token or db_token.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code."
        )
    
    if db_token.expiration_time < datetime.now():
        crud.delete_password_reset_token(db, db_token.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired. Please request a new one."
        )

    crud.update_user_password(db, user.id, new_password)

    crud.delete_password_reset_token(db, db_token.id)

    # Log the action
    admin_performing_action = db.query(models.Admin).filter(models.Admin.email == identifier).first()
    if admin_performing_action and admin_performing_action.admin_id == user.id: 
        description = f"Admin '{admin_performing_action.first_name} {admin_performing_action.last_name}' successfully reset their password via reset code."
        await crud.create_admin_log(
            db=db,
            admin_id=admin_performing_action.admin_id,
            action_type="Admin Password Reset (Code)",
            description=description,
            request=request,
            target_entity_type="Admin",
            target_entity_id=admin_performing_action.admin_id
        )

    return {"message": "Password has been reset successfully."}, status.HTTP_200_OK

@app.get("/api/admin_users", response_model=List[Dict[str, Any]])
async def get_all_admin_users(db: Session = Depends(get_db)):
    """
    Retrieves a list of all administrators with their basic information.
    This is used to populate the admin filter dropdown in the activity log.
    """
    admins = db.query(models.Admin).all()
    return [
        {
            "admin_id": admin.admin_id,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "email": admin.email
        } for admin in admins
    ]

@app.get("/admin-logs", response_model=List[schemas.AdminLog])
async def get_all_admin_logs_api(
    request: Request,
    db: Session = Depends(get_db),
    admin_info_tuple: Tuple[models.Admin, models.Organization] = Depends(get_current_admin_with_org),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),
    admin_id: Optional[int] = Query(None, description="Filter by specific admin ID within the organization"),
    organization_id: Optional[int] = Query(None, include_in_schema=False), 
    action_type: Optional[str] = Query(None, description="Filter by type of action (e.g., 'Theme Change')"),
    start_date: Optional[date] = Query(None, description="Start date for logs (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for logs (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search keyword in log description")
):
    current_admin, current_organization = admin_info_tuple

    logs = crud.get_admin_logs(
        db=db,
        skip=skip,
        limit=limit,
        admin_id=admin_id,
        organization_id=current_organization.id, 
        action_type=action_type,
        start_date=start_date,
        end_date=end_date,
        search_query=search
    )
    return logs