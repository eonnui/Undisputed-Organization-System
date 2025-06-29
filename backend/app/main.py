from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Form, APIRouter, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from sqlalchemy.orm import Session, joinedload, contains_eager
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
import uuid
import aiofiles

# Import IntegrityError for database exception handling 
from sqlalchemy.exc import IntegrityError

# Import run_in_threadpool for async threadpool execution
from starlette.concurrency import run_in_threadpool

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

# File Directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static" 

WIKI_IMAGES_SUBDIRECTORY = "images/wiki_images"
FULL_WIKI_UPLOAD_PATH = STATIC_DIR / WIKI_IMAGES_SUBDIRECTORY
FULL_WIKI_UPLOAD_PATH.mkdir(parents=True, exist_ok=True)

EVENT_CLASSIFICATION_IMAGES_SUBDIRECTORY = "images/event_classifications"
(STATIC_DIR / EVENT_CLASSIFICATION_IMAGES_SUBDIRECTORY).mkdir(parents=True, exist_ok=True)

CAMPAIGN_IMAGES_SUBDIRECTORY = "images/campaigns"
(STATIC_DIR / CAMPAIGN_IMAGES_SUBDIRECTORY).mkdir(parents=True, exist_ok=True)

PROFILE_PICS_SUBDIRECTORY = "images/profile_pictures"
FULL_PROFILE_UPLOAD_PATH = STATIC_DIR / PROFILE_PICS_SUBDIRECTORY
FULL_PROFILE_UPLOAD_PATH.mkdir(parents=True, exist_ok=True)

ORG_CHART_PICTURE_FOLDER_NAME = "images/org_chart_pictures"
FULL_ORG_CHART_UPLOAD_PATH = STATIC_DIR / ORG_CHART_PICTURE_FOLDER_NAME
FULL_ORG_CHART_UPLOAD_PATH.mkdir(parents=True, exist_ok=True) 

# Define your temporary upload directory relative to STATIC_DIR
TEMP_UPLOAD_DIR = STATIC_DIR / "temp_uploads"
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
    old_file_path: Optional[str] = None,
    is_video_upload: bool = False # New flag to handle videos differently
) -> str:
    """
    Handles file uploads, saving to a temporary directory for large files (like videos)
    or directly to the final subdirectory for smaller files (like images).
    Returns the *relative* path to the saved file (e.g., /static/...).
    """
    if upload_file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only {', '.join(allowed_types)} are allowed for {subdirectory}.",
        )

    # If an old file path is provided, delete it first
    if old_file_path:
        # Assuming delete_file_from_path works with relative paths like '/static/...'
        delete_file_from_path(old_file_path)

    # Determine the target directory: temporary for videos, final for others
    if is_video_upload:
        # Generate a unique filename for the temporary file
        file_extension = os.path.splitext(upload_file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        target_save_path = TEMP_UPLOAD_DIR / unique_filename
    else:
        filename = generate_secure_filename(upload_file.filename)
        target_save_path = STATIC_DIR / subdirectory / filename
        target_save_path.parent.mkdir(parents=True, exist_ok=True) # Ensure final subdirectory exists

    file_size = 0
    try:
        async with aiofiles.open(target_save_path, "wb") as out_file:
            while True:
                chunk = await upload_file.read(8192)  # Read in chunks (e.g., 8KB)
                if not chunk:
                    break
                file_size += len(chunk)
                if max_size_bytes and file_size > max_size_bytes:
                    await out_file.close() # Close file before raising
                    # Clean up partial file if it's too large
                    if target_save_path.exists():
                        os.remove(target_save_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File size too large. Maximum allowed size is {max_size_bytes / (1024 * 1024):.2f} MB.",
                    )
                await out_file.write(chunk)

        # Return the path appropriate for the caller
        if is_video_upload:
            # For videos, return the absolute temporary file path,
            # which the RQ worker will use to move it later.
            return str(target_save_path.resolve())
        else:
            # For images, return the relative path as before
            return f"/static/{subdirectory}/{filename}"

    except Exception as e:
        # Ensure partial files are cleaned up on error
        if target_save_path.exists():
            os.remove(target_save_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}"
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

# Fetching Existing Admin
@router.get("/api/admin/existing_admins", response_model=List[schemas.AdminDisplay])
async def get_existing_admins(
    request: Request,
    db: Session = Depends(get_db)
):
    authenticated_admin, organization = None, None

    try:
        authenticated_admin, organization = get_current_admin_with_org(request, db)
    except HTTPException as e:
        raise e

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found for the authenticated admin."
        )
    
    existing_admins = db.query(models.Admin).join(models.organization_admins).filter(
        models.organization_admins.c.organization_id == organization.id,
        models.Admin.first_name.isnot(None),
        models.Admin.first_name != "",        
        models.Admin.first_name.ilike('%Vacant%') == False 
    ).all()

    return existing_admins

# Update Profile Picture of Admin
@router.put("/api/admin/me/profile_picture")
async def update_profile_picture(
    profile_picture_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin_with_org) 
):
    current_admin, _ = admin_data 
    

    db_admin = db.query(models.Admin).filter(models.Admin.admin_id == current_admin.admin_id).first()
    if not db_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated admin not found in database."
        )

    allowed_types = ["image/png", "image/jpeg", "image/gif", "image/svg+xml"]
    if profile_picture_file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PNG, JPG, JPEG, GIF, SVG are allowed."
        )

    FULL_PROFILE_UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
    file_extension = profile_picture_file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = FULL_PROFILE_UPLOAD_PATH / unique_filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(profile_picture_file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not upload profile picture: {e}"
        )

    db_admin.profile_picture = f"/static/{PROFILE_PICS_SUBDIRECTORY}/{unique_filename}" 
    
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)

    return {
        "message": "Profile picture updated successfully!",
        "profile_picture_url": db_admin.profile_picture
    }

@router.get("/api/admin/me/profile", response_model=None) 
async def get_my_profile(
    db: Session = Depends(get_db),
    admin_data: tuple = Depends(get_current_admin_with_org) 
):
    current_admin, _ = admin_data 

    db_admin = db.query(models.Admin).filter(models.Admin.admin_id == current_admin.admin_id).first()
    if not db_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found.")

    return {
        "admin_id": db_admin.admin_id,
        "first_name": db_admin.first_name,
        "last_name": db_admin.last_name,
        "email": db_admin.email,
        "profile_picture": db_admin.profile_picture 
    }

# Fetching Organization Admin Postition
DEFAULT_ORG_OFFICERS = [
    {
        "first_name": "Vacant",
        "last_name": "Vacant",
        "position": "President",
        "profile_picture_url": "/static/images/your_image_name.jpg"
    },
    {
        "first_name": "Vacant",
        "last_name": "Vacant",
        "position": "Vice President-Internal",
        "profile_picture_url": "/static/images/your_image_name.jpg"
    },
    {
        "first_name": "Vacant",
        "last_name": "Vacant",
        "position": "Vice President-External",
        "profile_picture_url": "/static/images/your_image_name.jpg"
    },
    {
        "first_name": "Vacant",
        "last_name": "Vacant",
        "position": "Secretary",
        "profile_picture_url": "/static/images/your_image_name.jpg"
    },
    {
        "first_name": "Vacant",
        "last_name": "Vacant",
        "position": "Treasurer",
        "profile_picture_url": "/static/images/your_image_name.jpg"
    },
    {
        "first_name": "Vacant",
        "last_name": "Vacant",
        "position": "Auditor",
        "profile_picture_url": "/static/images/your_image_name.jpg"
    },
    {
        "first_name": "Vacant",
        "last_name": "",
        "position": "PRO",
        "profile_picture_url": "/static/images/your_image_name.jpg"
    },
    {
        "first_name": "Vacant",
        "last_name": "Vacant",
        "position": "Adviser 1",
        "profile_picture_url": "/static/images/your_image_name.jpg"
    },
    {
        "first_name": "Vacant",
        "last_name": "Vacant",
        "position": "Adviser 2",
        "profile_picture_url": "/static/images/your_image_name.jpg"
    },
]

# Routes for Organization Chart
@router.get("/api/admin/org_chart_data", response_model=List[schemas.OrgChartNodeDisplay])
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

    org_name = organization.name if organization and organization.name else "N/A"
    org_chart_data_nodes = []

    admins_in_org = db.query(models.Admin).join(models.organization_admins).filter(
        models.organization_admins.c.organization_id == organization.id
    ).all()

    org_chart_node_overrides = db.query(models.OrgChartNode).options(joinedload(models.OrgChartNode.admin)).filter(
        models.OrgChartNode.organization_id == organization.id
    ).all()

    admin_map = {admin.admin_id: admin for admin in admins_in_org}
    org_chart_node_map_by_admin_id = {node.admin_id: node for node in org_chart_node_overrides if node.admin_id is not None}
    org_chart_node_map_by_position = {node.position: node for node in org_chart_node_overrides if node.admin_id is None and node.position}

    processed_admin_ids = set()

    for i, default_officer_template in enumerate(DEFAULT_ORG_OFFICERS):
        position_name = default_officer_template["position"]
        current_node_data = {}
        source_id = None

        chart_node_override_for_position = org_chart_node_map_by_position.get(position_name)

        admin_matching_position = None
        for admin_id, admin_obj in admin_map.items():
            if admin_obj.position == position_name and admin_id not in processed_admin_ids:
                admin_matching_position = admin_obj
                break

        if chart_node_override_for_position:
            current_node_data = {
                "first_name": chart_node_override_for_position.first_name,
                "last_name": chart_node_override_for_position.last_name,
                "position": chart_node_override_for_position.position,
                "chart_picture_url": chart_node_override_for_position.chart_picture_url or "/static/images/your_image_name.jpg"
            }
            source_id = f"chart_node_{chart_node_override_for_position.id}"
            org_chart_node_map_by_position.pop(position_name, None)
            if admin_matching_position:
                processed_admin_ids.add(admin_matching_position.admin_id)
                org_chart_node_map_by_admin_id.pop(admin_matching_position.admin_id, None)

        elif admin_matching_position:
            processed_admin_ids.add(admin_matching_position.admin_id)
            chart_node_override_for_admin = org_chart_node_map_by_admin_id.get(admin_matching_position.admin_id)

            if chart_node_override_for_admin:
                current_node_data = {
                    "first_name": chart_node_override_for_admin.first_name or admin_matching_position.first_name,
                    "last_name": chart_node_override_for_admin.last_name or admin_matching_position.last_name,
                    "position": chart_node_override_for_admin.position or admin_matching_position.position,
                    "chart_picture_url": chart_node_override_for_admin.chart_picture_url or admin_matching_position.profile_picture or "/static/images/your_image_name.jpg"
                }
                org_chart_node_map_by_admin_id.pop(admin_matching_position.admin_id, None)
            else:
                current_node_data = {
                    "first_name": admin_matching_position.first_name,
                    "last_name": admin_matching_position.last_name,
                    "position": admin_matching_position.position,
                    "chart_picture_url": admin_matching_position.profile_picture or "/static/images/your_image_name.jpg"
                }
            source_id = str(admin_matching_position.admin_id)

        else:
            current_node_data = {
                "first_name": default_officer_template.get("first_name", ""),
                "last_name": default_officer_template.get("last_name", ""),
                "position": default_officer_template["position"],
                "chart_picture_url": default_officer_template.get("chart_picture_url", "/static/images/your_image_name.jpg")
            }
            source_id = f"new_placeholder_{position_name.lower().replace(' ', '_')}_{i}"

        chart_node_entry = schemas.OrgChartNodeDisplay(
            id=source_id,
            first_name=current_node_data.get("first_name", ""),
            last_name=current_node_data.get("last_name", ""),
            position=current_node_data.get("position", ""),
            chart_picture_url=current_node_data.get("chart_picture_url", "/static/images/your_image_name.jpg"),
            organization_name=org_name
        )
        org_chart_data_nodes.append(chart_node_entry)

    for chart_node_override in org_chart_node_overrides:
        if chart_node_override.admin_id is None and chart_node_override.position in org_chart_node_map_by_position:
            org_chart_data_nodes.append(schemas.OrgChartNodeDisplay(
                id=f"chart_node_{chart_node_override.id}",
                first_name=chart_node_override.first_name,
                last_name=chart_node_override.last_name,
                position=chart_node_override.position,
                chart_picture_url=chart_node_override.chart_picture_url or "/static/images/your_image_name.jpg",
                organization_name=org_name
            ))
            org_chart_node_map_by_position.pop(chart_node_override.position, None)

        elif chart_node_override.admin_id is not None and chart_node_override.admin_id in org_chart_node_map_by_admin_id:
            admin_obj = chart_node_override.admin
            node_display_data = {
                "first_name": chart_node_override.first_name,
                "last_name": chart_node_override.last_name,
                "position": chart_node_override.position,
                "chart_picture_url": chart_node_override.chart_picture_url
            }
            if admin_obj:
                node_display_data["first_name"] = node_display_data["first_name"] or admin_obj.first_name
                node_display_data["last_name"] = node_display_data["last_name"] or admin_obj.last_name
                node_display_data["position"] = node_display_data["position"] or admin_obj.position
                node_display_data["chart_picture_url"] = node_display_data["chart_picture_url"] or admin_obj.profile_picture

            org_chart_data_nodes.append(schemas.OrgChartNodeDisplay(
                id=str(chart_node_override.admin_id),
                first_name=node_display_data["first_name"],
                last_name=node_display_data["last_name"],
                position=node_display_data["position"],
                chart_picture_url=node_display_data["chart_picture_url"] or "/static/images/your_image_name.jpg",
                organization_name=org_name
            ))
            processed_admin_ids.add(chart_node_override.admin_id)
            org_chart_node_map_by_admin_id.pop(chart_node_override.admin_id, None)

    for admin_id, admin_obj in admin_map.items():
        if admin_id not in processed_admin_ids:
            org_chart_data_nodes.append(schemas.OrgChartNodeDisplay(
                id=str(admin_obj.admin_id),
                first_name=admin_obj.first_name,
                last_name=admin_obj.last_name,
                position=admin_obj.position,
                chart_picture_url=admin_obj.profile_picture or "/static/images/your_image_name.jpg",
                organization_name=org_name
            ))

    return org_chart_data_nodes

@router.put("/api/admin/org_chart_node/{node_id}", response_model=schemas.OrgChartNodeUpdateResponse)
async def update_org_chart_node(
    node_id: str,
    request: Request,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    chart_picture: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    admin_org_data: Tuple[models.Admin, models.Organization] = Depends(get_current_admin_with_org)
):
    authenticated_entity, organization = admin_org_data

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this organization."
        )

    chart_node_to_update = None
    admin_id_for_node = None
    is_newly_created_chart_node = False

    if node_id.startswith("chart_node_"):
        try:
            chart_node_db_id = int(node_id.split("_")[2])
            chart_node_to_update = db.query(models.OrgChartNode).filter(
                models.OrgChartNode.id == chart_node_db_id,
                models.OrgChartNode.organization_id == organization.id
            ).first()
            if not chart_node_to_update:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart node not found or not in your organization.")
        except (ValueError, IndexError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart node ID format.")

    elif node_id.startswith("new_placeholder_"):
        is_newly_created_chart_node = True
        
        chart_node_to_update = models.OrgChartNode(organization_id=organization.id, admin_id=None, chart_picture_url="/static/images/your_image_name.jpg") 
        if not position: 
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Position is required for new chart node creation.")
        chart_node_to_update.position = position 

    else: 
        try:
            admin_id_for_node = int(node_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid node ID format. Must be an integer admin ID or a chart node string.")

        is_org_admin_check = db.query(models.organization_admins).filter(
            models.organization_admins.c.organization_id == organization.id,
            models.organization_admins.c.admin_id == admin_id_for_node
        ).first()
        if not is_org_admin_check:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin does not belong to your organization or you are not authorized.")

        chart_node_to_update = db.query(models.OrgChartNode).filter(
            models.OrgChartNode.organization_id == organization.id,
            models.OrgChartNode.admin_id == admin_id_for_node
        ).first()

        if not chart_node_to_update:
            is_newly_created_chart_node = True
            admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id_for_node).first()
            if not admin:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found to create chart node for.")

            chart_node_to_update = models.OrgChartNode(
                organization_id=organization.id,
                admin_id=admin_id_for_node,
                first_name=admin.first_name,
                last_name=admin.last_name,
                position=admin.position,
                chart_picture_url=admin.profile_picture 
            )
            db.add(chart_node_to_update)
            db.flush() 

    if not chart_node_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organizational chart node to update not found.")

    original_chart_picture_url = chart_node_to_update.chart_picture_url 
    
    sever_link = False
    original_admin_id = chart_node_to_update.admin_id 
    linked_admin_original = None
    original_admin_name = "Unknown Admin"

    if original_admin_id is not None:
        linked_admin_original = db.query(models.Admin).filter(models.Admin.admin_id == original_admin_id).first()
        if linked_admin_original:
            original_admin_name = f"{linked_admin_original.first_name} {linked_admin_original.last_name}"
        else: 
            sever_link = True 

    if chart_picture and chart_picture.size > 0:
        file_extension = Path(chart_picture.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = FULL_ORG_CHART_UPLOAD_PATH / unique_filename
        relative_url = f"/static/images/org_chart_pictures/{unique_filename}"

        try:
            contents = await chart_picture.read()
            with open(file_path, "wb") as buffer:
                buffer.write(contents)
            chart_node_to_update.chart_picture_url = relative_url
            sever_link = True 
        except Exception as e:
            print(f"Error saving chart picture for node {node_id}: {e}")

    if first_name is not None:
        chart_node_to_update.first_name = first_name
    if last_name is not None:
        chart_node_to_update.last_name = last_name
    if position is not None:
        chart_node_to_update.position = position

    if chart_node_to_update.admin_id is not None and linked_admin_original:

        if (first_name is not None and chart_node_to_update.first_name != linked_admin_original.first_name) or \
           (last_name is not None and chart_node_to_update.last_name != linked_admin_original.last_name) or \
           (position is not None and chart_node_to_update.position != linked_admin_original.position):
            sever_link = True

    if sever_link:
        if chart_node_to_update.admin_id is not None: 
            chart_node_to_update.admin_id = None 
    try:
        db.commit()
        db.refresh(chart_node_to_update)

        response_id_for_return = str(chart_node_to_update.admin_id) if chart_node_to_update.admin_id else f"chart_node_{chart_node_to_update.id}"

        description = f"Admin '{authenticated_entity.first_name} {authenticated_entity.last_name}' updated org chart node for ID '{node_id}'."
        if sever_link and original_admin_id is not None:
            description += f" (Link to Admin ID {original_admin_id} ({original_admin_name}) severed)."
        elif is_newly_created_chart_node:
            description = f"Admin '{authenticated_entity.first_name} {authenticated_entity.last_name}' created new org chart node via update path for ID '{response_id_for_return}'."

        await crud.create_admin_log(
            db=db,
            admin_id=authenticated_entity.admin_id,
            organization_id=organization.id,
            action_type="Org Chart Node Updated (Unified)",
            description=description,
            request=request,
            target_entity_type="OrgChartNode",
            target_entity_id=chart_node_to_update.id
        )
        db.commit() # Commit the log

        return schemas.OrgChartNodeUpdateResponse(
            message="Organizational chart node data updated successfully.",
            id=response_id_for_return,
            first_name=chart_node_to_update.first_name,
            last_name=chart_node_to_update.last_name,
            position=chart_node_to_update.position,
            chart_picture_url=chart_node_to_update.chart_picture_url
        )

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Database integrity error: {e.orig}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update chart node: {e}")

@router.post("/api/admin/org_chart_node", response_model=schemas.OrgChartNodeUpdateResponse)
async def create_org_chart_node(
    request: Request,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    position: str = Form(...),
    chart_picture: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    admin_org_data: Tuple[models.Admin, models.Organization] = Depends(get_current_admin_with_org)
):
    """
    Creates a new organizational chart node, including an optional profile picture.
    """
    authenticated_entity, organization = admin_org_data

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this organization."
        )
    
    new_chart_node = models.OrgChartNode(
        organization_id=organization.id,
        admin_id=None,
        first_name=first_name,
        last_name=last_name,
        position=position,
    )

    new_chart_node.chart_picture_url = "/static/images/your_image_name.jpg"

    if chart_picture and chart_picture.size > 0:
        file_extension = Path(chart_picture.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = FULL_ORG_CHART_UPLOAD_PATH / unique_filename
        relative_url = f"/static/images/org_chart_pictures/{unique_filename}"

        try:
            contents = await chart_picture.read()
            with open(file_path, "wb") as buffer:
                buffer.write(contents)
            new_chart_node.chart_picture_url = relative_url
        except Exception as e:
            print(f"Error saving chart picture for new node: {e}")

    try:
        db.add(new_chart_node)
        db.commit()
        db.refresh(new_chart_node)

        # Log the creation
        description = f"Admin '{authenticated_entity.first_name} {authenticated_entity.last_name}' created new org chart node with position '{new_chart_node.position}' and ID '{new_chart_node.id}'."
        await crud.create_admin_log(
            db=db,
            admin_id=authenticated_entity.admin_id,
            organization_id=organization.id,
            action_type="Org Chart Node Created",
            description=description,
            request=request,
            target_entity_type="OrgChartNode",
            target_entity_id=new_chart_node.id
        )
        db.commit()

        return schemas.OrgChartNodeUpdateResponse(
            message="Organizational chart node created successfully.",
            id=f"chart_node_{new_chart_node.id}",
            first_name=new_chart_node.first_name,
            last_name=new_chart_node.last_name,
            position=new_chart_node.position,
            chart_picture_url=new_chart_node.chart_picture_url
        )

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Database integrity error: {e.orig}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create chart node: {e}")
    
# Route for Organization Positions
@router.get("/api/admin/organizations/{organization_id}/taken_positions", response_model=List[str])
async def get_taken_positions(organization_id: int, db: Session = Depends(get_db)):
    taken_positions_query = db.query(models.Admin.position).join(models.Admin.organizations).filter(
        models.Organization.id == organization_id
    ).distinct().all()

    taken_positions = [position[0] for position in taken_positions_query if position[0]]

    return taken_positions

@router.put("/api/admin/org_chart_node/{node_id}/overwrite", response_model=schemas.OrgChartNodeUpdateResponse)
async def overwrite_org_chart_node(
    node_id: str,
    payload: schemas.OrgChartNodeOverwriteRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_org_data: Tuple[models.Admin, models.Organization] = Depends(get_current_admin_with_org)
):
    authenticated_entity, organization = admin_org_data

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this organization."
        )

    if node_id.startswith("new_placeholder_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot overwrite a temporary placeholder node. Please edit it directly to create a permanent entry first, then you can overwrite it."
        )

    chart_node_to_overwrite = None
    original_admin_id_linked_to_node = None

    if node_id.startswith("chart_node_"):
        try:
            chart_node_db_id = int(node_id.split("_")[2])
            chart_node_to_overwrite = db.query(models.OrgChartNode).filter(
                models.OrgChartNode.id == chart_node_db_id,
                models.OrgChartNode.organization_id == organization.id
            ).first()
            if chart_node_to_overwrite and chart_node_to_overwrite.admin_id:
                original_admin_id_linked_to_node = chart_node_to_overwrite.admin_id

        except (ValueError, IndexError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chart node ID format.")
    else: 
        try:
            admin_id_from_node_id = int(node_id)
            chart_node_to_overwrite = db.query(models.OrgChartNode).filter(
                models.OrgChartNode.admin_id == admin_id_from_node_id,
                models.OrgChartNode.organization_id == organization.id
            ).first()
            if chart_node_to_overwrite:
                original_admin_id_linked_to_node = chart_node_to_overwrite.admin_id
            else:
                admin_to_link_initial = db.query(models.Admin).filter(models.Admin.admin_id == admin_id_from_node_id).first()
                if admin_to_link_initial:
                    chart_node_to_overwrite = models.OrgChartNode(
                        organization_id=organization.id,
                        admin_id=admin_to_link_initial.admin_id,
                        first_name=admin_to_link_initial.first_name,
                        last_name=admin_to_link_initial.last_name,
                        position=admin_to_link_initial.position,
                        chart_picture_url=admin_to_link_initial.profile_picture
                    )
                    db.add(chart_node_to_overwrite)
                    db.flush() 
                else:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin associated with node ID not found.")

        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid node ID format. Must be an integer admin ID or a chart node string.")


    if not chart_node_to_overwrite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organizational chart node to overwrite not found.")

    existing_admin_id_to_link = payload.existing_admin_id
    existing_admin_to_link = db.query(models.Admin).filter(models.Admin.admin_id == existing_admin_id_to_link).first()

    if not existing_admin_to_link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Existing admin to link not found.")

    is_org_admin_check = db.query(models.organization_admins).filter(
        models.organization_admins.c.organization_id == organization.id,
        models.organization_admins.c.admin_id == existing_admin_id_to_link
    ).first()
    if not is_org_admin_check:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The selected existing admin does not belong to your organization.")

    if chart_node_to_overwrite.admin_id == existing_admin_id_to_link:
        pass
    else:
        existing_chart_node_linked_to_admin = db.query(models.OrgChartNode).filter(
            models.OrgChartNode.organization_id == organization.id,
            models.OrgChartNode.admin_id == existing_admin_id_to_link
        ).first()

        if existing_chart_node_linked_to_admin:
            if chart_node_to_overwrite.id != existing_chart_node_linked_to_admin.id:
                previous_node_id = existing_chart_node_linked_to_admin.id
                previous_node_admin_name = f"{existing_admin_to_link.first_name} {existing_admin_to_link.last_name}"

                existing_chart_node_linked_to_admin.admin_id = None
                existing_chart_node_linked_to_admin.first_name = "Vacant"
                existing_chart_node_linked_to_admin.last_name = ""
                existing_chart_node_linked_to_admin.position = "Empty Slot" 
                existing_chart_node_linked_to_admin.chart_picture_url = "/static/images/your_image_name.jpg" 

                db.add(existing_chart_node_linked_to_admin)
                db.flush() 

                description_previous = (
                    f"Admin '{authenticated_entity.first_name} {authenticated_entity.last_name}' "
                    f"unlinked existing admin '{previous_node_admin_name}' (ID: {existing_admin_id_to_link}) "
                    f"from Org Chart Node ID {previous_node_id} (to reassign to node {chart_node_to_overwrite.id})."
                )
                await crud.create_admin_log(
                    db=db,
                    admin_id=authenticated_entity.admin_id,
                    organization_id=organization.id,
                    action_type="Org Chart Node Admin Unlinked (Reassignment)",
                    description=description_previous,
                    request=request,
                    target_entity_type="OrgChartNode",
                    target_entity_id=previous_node_id
                )

        if original_admin_id_linked_to_node is not None and original_admin_id_linked_to_node != existing_admin_id_to_link:
            original_admin_on_target = db.query(models.Admin).filter(models.Admin.admin_id == original_admin_id_linked_to_node).first()
            original_admin_on_target_name = f"{original_admin_on_target.first_name} {original_admin_on_target.last_name}" if original_admin_on_target else "Unknown Admin"

            description_overwrite = (
                f"Admin '{authenticated_entity.first_name} {authenticated_entity.last_name}' "
                f"overwrote Org Chart Node ID {chart_node_to_overwrite.id}, "
                f"displacing Admin '{original_admin_on_target_name}' (ID: {original_admin_id_linked_to_node})."
            )
            await crud.create_admin_log(
                db=db,
                admin_id=authenticated_entity.admin_id,
                organization_id=organization.id,
                action_type="Org Chart Node Overwritten (Displaced Admin)",
                description=description_overwrite,
                request=request,
                target_entity_type="OrgChartNode",
                target_entity_id=chart_node_to_overwrite.id
            )

    chart_node_to_overwrite.admin_id = existing_admin_to_link.admin_id 
    chart_node_to_overwrite.first_name = existing_admin_to_link.first_name
    chart_node_to_overwrite.last_name = existing_admin_to_link.last_name
    chart_node_to_overwrite.position = existing_admin_to_link.position 
    chart_node_to_overwrite.chart_picture_url = existing_admin_to_link.profile_picture 

    try:
        db.add(chart_node_to_overwrite) 
        db.commit() 
        db.refresh(chart_node_to_overwrite)

        response_id_for_return = str(chart_node_to_overwrite.admin_id) if chart_node_to_overwrite.admin_id else f"chart_node_{chart_node_to_overwrite.id}"

        description = f"Admin '{authenticated_entity.first_name} {authenticated_entity.last_name}' linked org chart node '{node_id}' with existing admin '{existing_admin_to_link.first_name} {existing_admin_to_link.last_name}' (ID: {existing_admin_id_to_link})."
        await crud.create_admin_log(
            db=db,
            admin_id=authenticated_entity.admin_id,
            organization_id=organization.id,
            action_type="Org Chart Node Linked/Overwritten Success",
            description=description,
            request=request,
            target_entity_type="OrgChartNode",
            target_entity_id=chart_node_to_overwrite.id
        )
        db.commit() 

        return schemas.OrgChartNodeUpdateResponse(
            message="Organizational chart node linked/overwritten successfully.",
            id=response_id_for_return,
            first_name=chart_node_to_overwrite.first_name,
            last_name=chart_node_to_overwrite.last_name,
            position=chart_node_to_overwrite.position,
            chart_picture_url=chart_node_to_overwrite.chart_picture_url
        )

    except IntegrityError as e:
        db.rollback()

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Database integrity error: {e.orig}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to link/overwrite chart node: {e}")
    
# Admin Bulletin Board Post Creation
@router.post("/admin/bulletin_board/post", response_class=HTMLResponse, name="admin_post_bulletin")
async def admin_post_bulletin(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form(...),
    is_pinned: Optional[bool] = Form(False),
    image: Optional[UploadFile] = File(None), 
    video: Optional[UploadFile] = File(None), 
    db: Session = Depends(get_db),
):
    admin, admin_org = get_current_admin_with_org(request, db)

    image_path = None
    if image and image.filename:
        allowed_image_types = ["image/jpeg", "image/png", "image/gif", "image/svg+xml"]
        try:
            image_path = await handle_file_upload(
                upload_file=image,
                subdirectory="images/bulletin_board", 
                allowed_types=allowed_image_types,
                max_size_bytes=5 * 1024 * 1024 
            )
        except HTTPException as e:
            print(f"Image upload failed: {e.detail}")
            pass 

    video_path = None

    if video and video.filename: 
        allowed_video_types = [
            "video/mp4", 
            "video/mpeg", 
            "video/quicktime", 
            "video/webm", 
            "video/x-msvideo", 
            "video/x-flv"      
        ]
        try:
            video_path = await handle_file_upload(
                upload_file=video,
                subdirectory="videos/bulletin_board", 
                allowed_types=allowed_video_types,
                max_size_bytes=100 * 1024 * 1024 * 1024, 
            )
        except HTTPException as e:
            print(f"Video upload failed: {e.detail}")
            pass 

    db_post = models.BulletinBoard(
        title=title,
        content=content,
        category=category,
        is_pinned=is_pinned,
        admin_id=admin.admin_id,
        image_path=image_path, 
        video_path=video_path, #
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

    try:
        event_date = datetime.strptime(date, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date and time format. Please use YYYY-MM-DDTHH:MM (e.g., 2025-05-27T14:30)."
        )

    current_datetime = datetime.now()
    if event_date < current_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event date and time cannot be in the past. Please select a future date and time."
        )
    if max_participants < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Max participants cannot be less than 0. Please enter a valid non-negative number."
        )

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
    prices_by_size: str = Form(..., description="JSON string of prices by size, e.g., '{\"S\": 15.0, \"M\": 16.0}'"), 
    pre_order_deadline: datetime = Form(...),
    available_stock: int = Form(...),
    is_active: bool = Form(True),
    size_chart_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    admin, admin_org = get_current_admin_with_org(request, db)
    organization_id = admin_org.id if admin_org else None

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

    campaign_data = schemas.ShirtCampaignCreate(
        title=title,
        description=description,
        prices_by_size=parsed_prices_by_size,
        pre_order_deadline=pre_order_deadline,
        available_stock=available_stock,
        is_active=is_active,
        size_chart_image_path=size_chart_image_path
    )

    db_campaign = crud.create_shirt_campaign(
        db=db,
        campaign=campaign_data,
        admin_id=admin.admin_id,
        organization_id=organization_id,
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
    prices_by_size: Optional[str] = Form(None, description="Optional JSON string of prices by size for update"),
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
    update_data["size_chart_image_path"] = final_size_chart_image_path 

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
    order_update_data: schemas.StudentShirtOrderUpdate = Body(...), 
    db: Session = Depends(get_db)
):
    current_user, user_org = get_current_user_with_org(request, db)

    order = crud.get_student_shirt_order_by_id(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student Shirt Order not found.")

    if order.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this order. You can only update your own orders.")

    if order.campaign and order.campaign.organization_id != user_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this order. Order belongs to a different organization.")

    updated_order = crud.update_student_shirt_order(
        db=db,
        order_id=order_id,
        order_update=order_update_data, 
    )

    if not updated_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found after update attempt.")

    return updated_order

@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student_shirt_order_api(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    current_user, user_org = get_current_user_with_org(request, db)

    order = crud.get_student_shirt_order_by_id(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student Shirt Order not found.")

    if order.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this order. You can only delete your own orders.")

    if order.campaign and order.campaign.organization_id != user_org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this order. Order belongs to a different organization.")

    crud.delete_student_shirt_order(db, order_id=order_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/orders/", response_model=List[schemas.StudentShirtOrder]) 
async def get_all_organization_orders_for_admin(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),
):
    admin, organization = get_current_admin_with_org(request, db)

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

    shirt_campaigns = crud.get_all_shirt_campaigns(
        db,
        organization_id=organization_id,
        is_active=True,
        start_date=date.today() 
    )
    logger.info(f"Fetched Shirt Campaigns: {len(shirt_campaigns)} campaigns.")
    for campaign in shirt_campaigns:
        logger.info(f"   - Campaign ID: {campaign.id}, Name: {campaign.title}, Org ID: {campaign.organization_id}, Deadline: {campaign.pre_order_deadline}")

    student_shirt_orders = crud.get_student_shirt_orders_by_student_id(db, current_user.id)
    logger.info(f"Fetched Student Shirt Orders: {len(student_shirt_orders)} orders for student {current_user.id}.")
    for order in student_shirt_orders:
        logger.info(f"   - Order ID: {order.id}, Campaign ID: {order.campaign_id}, Payment Status: {order.payment.status if order.payment else 'No Payment Record'}")
       
    env = templates.env
    logger.info(f"Jinja2 Environment acquired: {env}")

    if 'now' not in env.globals:
        env.globals['now'] = datetime.now
        logger.info("Added 'now' to Jinja2 globals.")
    else:
        logger.info("'now' already exists in Jinja2 globals.")


    order_detail = None 
    logger.info(f"Order Detail set to: {order_detail}")

    context = await get_base_template_context(request, db)
    logger.info(f"Base Template Context Keys: {list(context.keys())}")

    context.update({
        "shirt_campaigns": shirt_campaigns,
        "student_shirt_orders": student_shirt_orders,
        "current_user": current_user,
        "order_detail": order_detail 
    })
    logger.info(f"Final Template Context Keys: {list(context.keys())}")


    logger.info("--- Exiting /student/shirt-management route (rendering template) ---")
    return templates.TemplateResponse(
        "student_dashboard/student_shirt_management.html", 
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
        start_date=date.today() 
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

#STUDENTS PROFILE
@router.get("/admin/students_profile", response_class=HTMLResponse, name="admin_students_profile")
async def admin_shirt_management(request: Request, db: Session = Depends(get_db)):
    admin, organization = get_current_admin_with_org(request, db)
    context = await get_base_template_context(request, db)
    context.update({
        "admin_id": admin.admin_id,
        "organization_id": organization.id,
    })
    return templates.TemplateResponse("admin_dashboard/admin_students_profile.html", context)

@router.get("/admin/students", response_model=List[dict])
async def get_students(
    db: Session = Depends(get_db),
    admin_with_org: Tuple[models.Admin, models.Organization] = Depends(get_current_admin_with_org),
    search: Optional[str] = Query(None, description="Search query for student name or student number"),
    year_level: Optional[str] = Query(None, description="Filter by year level"),
    section: Optional[str] = Query(None, description="Filter by section"),
    sort_by: Optional[str] = Query("last_name", description="Column to sort by (e.g., first_name, last_name, student_number, year_level, section, email)"),
    sort_direction: Optional[str] = Query("asc", description="Sort direction (asc or desc)"),
):
    """
    Retrieves a list of students for the admin's organization with optional search, filter, and sort capabilities.
    """
    admin, organization = admin_with_org 

    query = db.query(models.User)

    query = query.filter(models.User.organization_id == organization.id)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (models.User.first_name.ilike(search_pattern)) |
            (models.User.last_name.ilike(search_pattern)) |
            (models.User.student_number.ilike(search_pattern))
        )

    if year_level:
        query = query.filter(models.User.year_level == year_level)

    if section:
        query = query.filter(models.User.section == section)

    sortable_columns = {
        "student_number": models.User.student_number,
        "first_name": models.User.first_name,
        "last_name": models.User.last_name,
        "year_level": models.User.year_level,
        "section": models.User.section,
        "email": models.User.email,
    }

    sort_column_attr = sortable_columns.get(sort_by)
    if sort_column_attr:
        if sort_direction == 'desc':
            query = query.order_by(sort_column_attr.desc())
        else:
            query = query.order_by(sort_column_attr.asc())
    else:
        query = query.order_by(models.User.last_name.asc())

    students = query.all()

    students_data = [
        {
            "student_number": student.student_number,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "year_level": student.year_level,
            "section": student.section,
            "email": student.email,
        }
        for student in students
    ]

    return students_data

# Admin View Student Profile
@router.get("/admin/students/profile/{student_number}", response_model=dict)
async def get_student_profile(
    student_number: str,
    db: Session = Depends(get_db),
    admin_with_org: Tuple[models.Admin, models.Organization] = Depends(get_current_admin_with_org),
):
    """
    Retrieves the profile of a specific student by student_number,
    ensuring they belong to the viewing admin's organization.
    """
    admin, organization = admin_with_org 

    student = db.query(models.User).filter(
        models.User.student_number == student_number,
        models.User.organization_id == organization.id 
    ).first()

    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found or not in your organization.")

    student_profile_data = {
        "id": student.id,
        "student_number": student.student_number,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "email": student.email,
        "year_level": student.year_level,
        "section": student.section,
        "campus": student.campus,
        "semester": student.semester,
        "course": student.course,
        "school_year": student.school_year,
        "address": student.address,
        "birthdate": student.birthdate, 
        "sex": student.sex,
        "contact": student.contact,
        "guardian_name": student.guardian_name,
        "guardian_contact": student.guardian_contact,
        "registration_form": student.registration_form,
        "profile_picture": student.profile_picture,
        "is_verified": student.is_verified,
        "verified_by": student.verified_by,
        "verification_date": student.verification_date.isoformat() if student.verification_date else None,
        "organization_id": student.organization_id,
    }

    return student_profile_data

# Admin Payments Page
@router.get("/Admin/payments", response_class=HTMLResponse, name="admin_payments")
async def admin_payments(
    request: Request,
    db: Session = Depends(get_db),
    student_number: Optional[str] = None,
):
    admin, organization = get_current_admin_with_org(request, db)

    query = db.query(models.PaymentItem).join(models.User).filter(
        models.User.organization_id == organization.id,
        models.PaymentItem.student_shirt_order_id.is_(None) 
    )
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
                    "payment_item": payment_item_data 
                },
                "status": status_text,
                "user_name": f"{user.first_name} {user.last_name}",
                "student_number": user.student_number,
                "payment_date": payment.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            print(f"Skipping payment {payment.id} due to missing related data.")
            continue

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

    # Start with a query for users in the organization
    query = db.query(models.User).filter(models.User.organization_id == admin_org.id)

    # Apply filters by joining PaymentItem and filtering on its columns
    if academic_year or semester:
        # We need to join PaymentItem to filter users based on their payment items
        query = query.join(
            models.PaymentItem,
            models.User.id == models.PaymentItem.user_id
        )
        # Add payment item specific filters
        payment_item_filters = [
            models.PaymentItem.student_shirt_order_id.is_(None)
        ]
        if academic_year:
            payment_item_filters.append(models.PaymentItem.academic_year == academic_year)
        if semester:
            payment_item_filters.append(models.PaymentItem.semester == semester)
        
        query = query.filter(*payment_item_filters)
    
    # Ensure unique users are returned, and load payment items for calculation
    # We load all payment items now, but we'll still filter them in Python for robust sums
    # if a user has other payment items not related to the current filters
    users = query.options(joinedload(models.User.payment_items)).distinct(models.User.id).all()
    
    membership_data = []
    processed_sections = set()

    for user in users:
        # This approach assumes 'users' now contains only users relevant to the filters.
        # However, to maintain the section grouping and count, it's simpler to re-group
        # if the goal is counts per section for filtered users.
        
        # A more direct approach to get overall counts for the stat card:
        # Let's pivot this endpoint slightly. Since the frontend expects a sum
        # for 'total_members_count' and 'total_collected', it might be better
        # to return these aggregated values directly from this endpoint.
        # The current structure returns an array of sections, which requires the frontend
        # to sum them up. This is fine if section breakdown is still needed.

        # If you still need the section breakdown AND accurate section_users_count:
        # The 'users' list is now ALREADY filtered by academic_year and semester (if provided).
        # So, the original len(section_users) will now be correct for the filtered set.
        if user.section not in processed_sections:
            # section_users will now only contain users that have payment items matching filters
            section_users_for_filtered_period = [u for u in users if u.section == user.section]
            
            section_paid_count = 0
            overall_section_total_amount = 0.0
            overall_section_total_paid = 0.0

            for other_user in section_users_for_filtered_period: # Iterate over the already filtered users
                # user_relevant_payment_items will still filter by academic_year/semester for safety,
                # in case a user has payment items outside the main query filter.
                # But since the 'users' query is now pre-filtered, this loop will be more efficient.
                user_relevant_payment_items = [
                    pi for pi in other_user.payment_items
                    if (academic_year is None or pi.academic_year == academic_year) and
                       (semester is None or pi.semester == semester) and
                       (pi.student_shirt_order_id is None) 
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

            # Now, len(section_users_for_filtered_period) should be the correct filtered count
            status_text = f"{section_paid_count}/{len(section_users_for_filtered_period)}" if academic_year and semester else str(len(section_users_for_filtered_period))
            
            membership_data.append({
                'student_number': section_users_for_filtered_period[0].student_number, # Assuming at least one user in section
                'email': section_users_for_filtered_period[0].email,
                'first_name': section_users_for_filtered_period[0].first_name,
                'last_name': section_users_for_filtered_period[0].last_name,
                'year_level': section_users_for_filtered_period[0].year_level,
                'section': section_users_for_filtered_period[0].section,
                'status': status_text,
                'total_paid': overall_section_total_paid, 
                'total_amount': overall_section_total_amount,
                'academic_year': academic_year,
                'semester': semester,
                'section_users_count': len(section_users_for_filtered_period), # This will now be the filtered count
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

    query = db.query(models.User).outerjoin(
        models.PaymentItem,
        models.User.id == models.PaymentItem.user_id
    ).filter(models.User.organization_id == admin_org.id)

    payment_item_filters = [
        models.PaymentItem.student_shirt_order_id.is_(None) 
    ]
    if academic_year:
        payment_item_filters.append(models.PaymentItem.academic_year == academic_year)
    if semester:
        payment_item_filters.append(models.PaymentItem.semester == semester)

    if payment_item_filters:
        query = query.filter(*payment_item_filters)

    query = query.options(contains_eager(models.User.payment_items))
    
    query = query.distinct(models.User.id).order_by(models.User.id) 


    users = query.all()
    membership_data = []

    for user in users:
        total_paid = 0
        total_amount = 0
        payment_status = "No Dues" if not (academic_year or semester) else "Not Applicable"

        for pi in user.payment_items:
            if not pi.is_not_responsible:
                total_amount += pi.fee
                
                if pi.is_paid:
                    total_paid += pi.fee

        if total_amount > 0:
            payment_status = "Paid" if total_paid >= total_amount else "Partially Paid"
        else:
            if academic_year or semester:
                payment_status = "No Dues for Period"
            else:
                payment_status = "No Dues"

        membership_data.append({
            'student_number': user.student_number, 'email': user.email, 'first_name': user.first_name,
            'last_name': user.last_name, 'year_level': user.year_level, 'section': user.section,
            'total_paid': total_paid, 'total_amount': total_amount, 'payment_status': payment_status,
            'academic_year': academic_year, 'semester': semester,
        })
    return membership_data

# Financial Trends (Monthly Revenue)
@router.get("/financial_trends")
async def get_financial_trends(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: str = Query(None, description="Filter by academic year (e.g., '2023-2024')"),
    semester: str = Query(None, description="Filter by semester (e.g., '1st Semester', '2nd Semester')")
):
    admin, admin_org = get_current_admin_with_org(request, db)

    start_date_filter = None
    end_date_filter = None
    
    # Use a dictionary to store totals for each month-academic_year combination
    # The structure will be: { (year, month): { 'AY1': total1, 'AY2': total2, 'Total': overall_total } }
    # This will be transformed into Chart.js datasets later.
    monthly_academic_year_data = OrderedDict()

    if academic_year and academic_year != 'Academic Year ▼':
        try:
            start_year_str, end_year_str = academic_year.split('-')
            start_year = int(start_year_str)
            end_year = int(end_year_str)

            # Define academic year start and end months (e.g., August to July)
            academic_start_month = 8  # August
            academic_end_month = 7    # July of the next year

            start_date_filter = datetime(start_year, academic_start_month, 1).date()
            end_date_filter = datetime(end_year, academic_end_month, 1).date() + relativedelta(months=1) - relativedelta(days=1)

            # Populate monthly_academic_year_data for the entire selected academic year
            current_date_in_ay = start_date_filter
            while current_date_in_ay <= end_date_filter:
                month_key = (current_date_in_ay.year, current_date_in_ay.month)
                monthly_academic_year_data[month_key] = {} # Initialize for this month
                current_date_in_ay += relativedelta(months=1)

        except ValueError:
            print(f"Warning: Invalid academic_year format received: {academic_year}. Falling back to default.")
            academic_year = None
            
    if not academic_year: # Default behavior if no valid academic_year is provided
        num_months_to_display = 12
        today = date.today()
        for i in range(num_months_to_display - 1, -1, -1):
            target_date = today - relativedelta(months=i)
            month_key = (target_date.year, target_date.month)
            monthly_academic_year_data[month_key] = {} # Initialize for this month
        
        earliest_year, earliest_month = next(iter(monthly_academic_year_data.keys()))
        start_date_filter = datetime(earliest_year, earliest_month, 1).date()
        end_date_filter = today # Default end date is today

    query = db.query(
        func.extract('year', models.PaymentItem.updated_at).label('year'),  # Use PaymentItem.updated_at
        func.extract('month', models.PaymentItem.updated_at).label('month'), # Use PaymentItem.updated_at
        models.PaymentItem.academic_year.label('payment_academic_year'),
        func.sum(models.PaymentItem.fee).label('total'), # Sum PaymentItem.fee
    ).join(models.PaymentItem.user).filter( # Join PaymentItem directly with User
        and_(
            models.PaymentItem.is_paid == True, # Use PaymentItem.is_paid to determine success
            models.User.organization_id == admin_org.id,
            models.PaymentItem.student_shirt_order_id == None
        )
    )

    if start_date_filter:
        query = query.filter(models.PaymentItem.updated_at >= start_date_filter) # Filter by PaymentItem.updated_at
    if end_date_filter:
        query = query.filter(models.PaymentItem.updated_at <= end_date_filter) # Filter by PaymentItem.updated_at

    if semester and semester != 'Semester ▼':
        query = query.filter(models.PaymentItem.semester == semester)

    # Group by year, month, AND academic_year of the payment item to get breakdowns
    financial_data_raw = query.group_by('year', 'month', 'payment_academic_year').order_by('year', 'month', 'payment_academic_year').all()    
    for row in financial_data_raw:
        month_key = (int(row.year), int(row.month))
        payment_ay = row.payment_academic_year
        total_amount = float(row.total)

        if month_key in monthly_academic_year_data:
            if payment_ay not in monthly_academic_year_data[month_key]:
                monthly_academic_year_data[month_key][payment_ay] = 0.0
            monthly_academic_year_data[month_key][payment_ay] += total_amount
        else:
            print(f"Warning: Data for {month_key} found outside pre-populated range.")
            monthly_academic_year_data[month_key] = {payment_ay: total_amount}

    # Prepare data for Chart.js
    labels = []
    # Use a set to collect all unique academic years found in the data
    all_academic_years = set()
    
    # First pass: collect all unique academic years and ensure month keys are sorted
    sorted_month_keys = sorted(monthly_academic_year_data.keys())
    for year, month in sorted_month_keys:
        labels.append(f"{year}-{month:02d}")
        # Add academic years from the data to the set, excluding None
        for ay_key in monthly_academic_year_data[(year, month)].keys():
            if ay_key is not None:
                all_academic_years.add(ay_key)

    # Sort academic years for consistent legend ordering
    sorted_academic_years = sorted(list(all_academic_years))
    
    # Create datasets for each academic year
    datasets = []
    # Add a dataset for "Total Collections" across all academic years for that month
    total_collections_data = []
    for year, month in sorted_month_keys:
        month_total = sum(monthly_academic_year_data[(year, month)].values())
        total_collections_data.append(month_total)

    datasets.append({
        "label": "Total Collections",
        "data": total_collections_data,
        "borderColor": '#4285F4', # A default primary color
        "backgroundColor": 'transparent',
        "tension": 0.4,
        "pointBackgroundColor": '#4285F4',
        "borderWidth": 3,
        "pointRadius": 5,
        "pointHoverRadius": 7,
        "fill": False,
        "order": 0 # Ensure total is drawn first/on top
    })

    # Generate distinct colors for academic year lines
    # More colors added for better distinction if many academic years appear
    colors = [
        '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#03A9F4', '#00BCD4', '#009688',
        '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722', '#795548',
        '#607D8B', '#F44336'
    ]
    color_index = 0

    for ay in sorted_academic_years:
        # We ensure "Total Collections" is not considered an actual AY to avoid conflicts
        if ay == 'Total Collections':
            continue 
        
        current_color = colors[color_index % len(colors)]
        color_index += 1

        ay_data = []
        for year, month in sorted_month_keys:
            # Get the value for this academic year, or 0 if not present for the month
            ay_data.append(monthly_academic_year_data[(year, month)].get(ay, 0.0))
        
        datasets.append({
            "label": f"AY {ay}",
            "data": ay_data,
            "borderColor": current_color,
            "backgroundColor": 'transparent',
            "tension": 0.4,
            "pointBackgroundColor": current_color,
            "borderWidth": 2, # Slightly thinner for individual AY lines
            "pointRadius": 3,
            "pointHoverRadius": 5,
            "fill": False,
            "hidden": True, # Start with individual AY lines hidden, user can toggle
            "order": 1 # Draw individual AY lines behind the total line
        })

    return {"labels": labels, "datasets": datasets}

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

@router.get("/fund_distribution")
async def get_fund_distribution(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: str = Query(None, description="Filter by academic year (e.g., '2023-2024')"),
    semester: str = Query(None, description="Filter by semester (e.g., '1st Semester', '2nd Semester')")
):
    admin, admin_org = get_current_admin_with_org(request, db)

    query = db.query(
        models.PaymentItem.academic_year,
        models.PaymentItem.semester,
        func.sum(models.Payment.amount)
    ).join(
        models.Payment, models.PaymentItem.id == models.Payment.payment_item_id
    ).join(models.PaymentItem.user).filter(
        and_(
            models.Payment.status == "success",
            models.User.organization_id == admin_org.id,
            models.PaymentItem.student_shirt_order_id == None # Exclude shirt orders
        )
    )

    if academic_year and academic_year != 'Academic Year ▼':
        query = query.filter(models.PaymentItem.academic_year == academic_year)

    if semester and semester != 'Semester ▼':
        query = query.filter(models.PaymentItem.semester == semester)

    distribution_data = {}

    # Logic to handle grouping and labeling based on selected filters
    if academic_year and academic_year != 'Academic Year ▼' and semester and semester != 'Semester ▼':
        # If both are specific, group by academic_year and semester (will likely result in one slice)
        fund_allocation = query.group_by(models.PaymentItem.academic_year, models.PaymentItem.semester).all()
        for ay, sem, total_amount in fund_allocation:
            label = f"{ay} - {sem}"
            distribution_data[label] = distribution_data.get(label, 0.0) + float(total_amount)
    elif academic_year and academic_year != 'Academic Year ▼':
        # If only academic_year is specific, group by semester within that AY
        fund_allocation = query.group_by(models.PaymentItem.academic_year, models.PaymentItem.semester).all()
        for ay, sem, total_amount in fund_allocation:
            if ay == academic_year:
                label = ""
                if sem == "1st":
                    label = "1st Semester"
                elif sem == "2nd":
                    label = "2nd Semester"
                elif sem:
                    label = f"{sem} Semester"
                else:
                    label = "Unspecified Semester"
                distribution_data[label] = distribution_data.get(label, 0.0) + float(total_amount)
    elif semester and semester != 'Semester ▼':
        # If only semester is specific, group by academic_year for that semester
        fund_allocation = query.group_by(models.PaymentItem.academic_year, models.PaymentItem.semester).all()
        for ay, sem, total_amount in fund_allocation:
            if sem == semester:
                label = f"{ay if ay else 'Unspecified Academic Year'}"
                distribution_data[label] = distribution_data.get(label, 0.0) + float(total_amount)
    else:
        # If neither is specific, group by academic_year for a general overview
        fund_allocation = query.group_by(models.PaymentItem.academic_year).all()
        for ay, _, total_amount in fund_allocation: #semester is also in query, but not used in group_by
            label = f"{ay if ay else 'General Funds'}"
            distribution_data[label] = distribution_data.get(label, 0.0) + float(total_amount)

    return {"labels": list(distribution_data.keys()), "data": list(distribution_data.values())}

# Outstanding Dues
@router.get("/admin/outstanding_dues/")
async def admin_outstanding_dues(
    request: Request,
    db: Session = Depends(get_db),
    academic_year: Optional[str] = None,
    semester: Optional[str] = None, # <--- ADD THIS PARAMETER
) -> List[Dict[str, Any]]:
    admin, admin_org = get_current_admin_with_org(request, db)

    today = date.today()

    # Resolve Academic Year (already works fine)
    if academic_year:
        resolved_academic_year = academic_year
    else:
        start_year = today.year - 1 if today.month < 9 else today.year
        resolved_academic_year = f"{start_year}-{start_year + 1}"

    # Resolve Semester: Use provided 'semester' parameter first, then fallback to current_semester_name
    resolved_semester_name = None
    if semester: # <--- USE THE PROVIDED SEMESTER PARAMETER
        resolved_semester_name = semester
    else: # Fallback to calculating from today if no semester parameter is provided
        if 9 <= today.month <= 12 or today.month == 1:
            resolved_semester_name = "1st"
        elif 2 <= today.month <= 6:
            resolved_semester_name = "2nd"
        elif 7 <= today.month <= 8:
            resolved_semester_name = "Summer Break"

    total_outstanding_amount = 0.0
    # Only proceed if a valid semester (not Summer Break) is determined
    if resolved_semester_name in ["1st", "2nd"]: # <--- Use resolved_semester_name here
        relevant_payment_items = db.query(models.PaymentItem).join(models.User).filter(
            and_(
                func.lower(models.PaymentItem.academic_year) == resolved_academic_year.lower(),
                models.PaymentItem.semester == resolved_semester_name, # <--- Use resolved_semester_name here
                models.User.organization_id == admin_org.id,
                models.PaymentItem.is_not_responsible == False,
                models.PaymentItem.student_shirt_order_id == None 
            )
        ).all()

        total_outstanding_amount = sum(
            item.fee for item in relevant_payment_items
            if not item.is_paid
        )

    return [{
        "total_outstanding_amount": total_outstanding_amount,
        "semester_status": resolved_semester_name, # <--- Return resolved semester
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

@router.get("/api/admin/financial_data", response_class=JSONResponse, name="admin_financial_data_api")
async def admin_financial_data_api(request: Request, db: Session = Depends(get_db)):
    admin, organization = get_current_admin_with_org(request, db)
    
    current_year = datetime.now().year # This will be the current calendar year (e.g., 2025)
    today = datetime.now().date()

    # Determine the current academic year (e.g., if it's June 2025, current AY is 2024-2025)
    # This logic assumes academic year starts in August (month 8)
    academic_year_start_month = 8 # August
    current_academic_year_start = current_year
    if today.month < academic_year_start_month: # If before August, it's the previous academic year
        current_academic_year_start -= 1
    current_academic_year_str = f"{current_academic_year_start}-{current_academic_year_start + 1}"
    
    # Calculate Turnover Funds (Accumulated collected membership fees from previous academic years)
    # This query will sum all paid membership fees *before* the current academic year
    # We'll assume 'academic_year' in PaymentItem is stored as 'YYYY-YYYY' (e.g., '2023-2024')
    turnover_funds = db.query(func.sum(models.PaymentItem.fee)).join(models.User).filter(
        models.PaymentItem.is_paid == True,
        models.User.organization_id == organization.id,
        models.PaymentItem.student_shirt_order_id.is_(None), # Exclude shirt orders
        models.PaymentItem.academic_year < current_academic_year_str # Academic years strictly less than current AY
    ).scalar() or 0.0

    # Calculate Current Academic Year Revenue (Membership fees collected for the current academic year)
    current_ay_membership_revenue = db.query(func.sum(models.PaymentItem.fee)).join(models.User).filter(
        models.PaymentItem.is_paid == True,
        models.User.organization_id == organization.id,
        models.PaymentItem.student_shirt_order_id.is_(None), # Exclude shirt orders
        models.PaymentItem.academic_year == current_academic_year_str # Only for the current academic year
    ).scalar() or 0.0

    # Calculate Upcoming Year Funds (Collected) (Advanced payments for next academic year's fees and beyond)
    # This now includes ALL academic years greater than or equal to the immediate next one
    next_academic_year_start = current_academic_year_start + 1
    next_academic_year_str = f"{next_academic_year_start}-{next_academic_year_start + 1}"
    
    upcoming_funds_collected = db.query(func.sum(models.PaymentItem.fee)).join(models.User).filter(
        models.PaymentItem.is_paid == True,
        models.User.organization_id == organization.id,
        models.PaymentItem.student_shirt_order_id.is_(None), # Exclude shirt orders
        models.PaymentItem.academic_year >= next_academic_year_str # IMPORTANT CHANGE: >= to include all future AYs
    ).scalar() or 0.0

    # Total expenses for the current calendar year (This seems to be the current definition)
    total_expenses_ytd = db.query(func.sum(models.Expense.amount)).filter(
        extract('year', models.Expense.incurred_at) == current_year, # Assuming calendar year for expenses
        models.Expense.organization_id == organization.id
    ).scalar() or 0.0

    # Net Income YTD (Current AY Membership Fees - Current AY Expenses)
    net_income_ytd = current_ay_membership_revenue - total_expenses_ytd
    
    # Total Current Balance = Turnover Funds + Net Income (Current AY) + Upcoming Year Funds
    total_current_balance = turnover_funds + net_income_ytd + upcoming_funds_collected

    profit_margin_ytd = round((net_income_ytd / current_ay_membership_revenue) * 100, 2) if current_ay_membership_revenue != 0 else 0.0
    
    # Top Revenue Source - Adjusted to prioritize membership fees from current AY or upcoming AY if higher
    # Otherwise, consider previous AYs if they represent the highest single source
    top_revenue_source_query = db.query(
        models.PaymentItem.academic_year, 
        models.PaymentItem.semester, 
        func.sum(models.PaymentItem.fee).label('total_fee')
    ).join(models.User).filter(
        models.PaymentItem.is_paid == True, 
        models.User.organization_id == organization.id,
        models.PaymentItem.student_shirt_order_id.is_(None) 
    ).group_by(models.PaymentItem.academic_year, models.PaymentItem.semester).order_by(func.sum(models.PaymentItem.fee).desc()).first()

    top_revenue_source = {"name": "N/A", "amount": 0.0}
    if top_revenue_source_query:
        source_name = f"AY {top_revenue_source_query.academic_year} - {top_revenue_source_query.semester} Fees" if top_revenue_source_query.academic_year and top_revenue_source_query.semester else "Miscellaneous Membership Fees"
        top_revenue_source = {"name": source_name, "amount": round(float(top_revenue_source_query.total_fee), 2)}

    # Largest expense remains the same (based on calendar year)
    largest_expense_query = db.query(models.Expense.category, func.sum(models.Expense.amount).label('total_amount')).filter(
        extract('year', models.Expense.incurred_at) == current_year, models.Expense.organization_id == organization.id
    ).group_by(models.Expense.category).order_by(func.sum(models.Expense.amount).desc()).first()
    largest_expense_category = "N/A"
    largest_expense_amount = 0.0
    if largest_expense_query:
        largest_expense_category = largest_expense_query.category if largest_expense_query.category else "Uncategorized"
        largest_expense_amount = round(float(largest_expense_query.total_amount), 2)

    # Revenues Breakdown - structured by academic year, including upcoming funds
    revenues_breakdown_dict = {}

    all_membership_revenues = db.query(
        models.PaymentItem.academic_year, 
        models.PaymentItem.semester, 
        func.sum(models.PaymentItem.fee).label('total_fee')
    ).join(models.User).filter(
        models.PaymentItem.is_paid == True, 
        models.User.organization_id == organization.id,
        models.PaymentItem.student_shirt_order_id.is_(None) 
    ).group_by(models.PaymentItem.academic_year, models.PaymentItem.semester).order_by(models.PaymentItem.academic_year, models.PaymentItem.semester).all()

    # Helper to calculate percentage based on total collected (turnover + current AY + all upcoming)
    total_all_collected_membership_fees = turnover_funds + current_ay_membership_revenue + upcoming_funds_collected
    
    for item in all_membership_revenues:
        year_str = item.academic_year
        if year_str not in revenues_breakdown_dict:
            revenues_breakdown_dict[year_str] = {
                "year": year_str,
                "total": 0.0,
                "percentage": 0.0,
                "semesters": []
            }
        
        semester_source_name = f"{item.semester} Fees" if item.semester else "Miscellaneous Fees"
        item_percentage = round((float(item.total_fee) / total_all_collected_membership_fees) * 100, 2) if total_all_collected_membership_fees != 0 else 0.0
        
        revenues_breakdown_dict[year_str]["semesters"].append({
            "source": semester_source_name, 
            "amount": round(float(item.total_fee), 2), 
            "percentage": item_percentage
        })
        revenues_breakdown_dict[year_str]["total"] += round(float(item.total_fee), 2)
    
    revenues_breakdown = list(revenues_breakdown_dict.values())
    # Recalculate year percentages after all semesters are added for that year
    for year_data in revenues_breakdown:
        year_data["percentage"] = round((year_data["total"] / total_all_collected_membership_fees) * 100, 2) if total_all_collected_membership_fees != 0 else 0.0

    # Ensure all percentages sum to 100% or adjust if needed
    if revenues_breakdown and total_all_collected_membership_fees > 0:
        current_total_percentage = sum(item["percentage"] for item in revenues_breakdown)
        if abs(current_total_percentage - 100) > 0.01: # Allow for minor floating point discrepancies
            adjustment_factor = 100 / current_total_percentage
            for item in revenues_breakdown:
                item["percentage"] = round(item["percentage"] * adjustment_factor, 2)


    # Expenses breakdown (based on calendar year)
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

    # Monthly summary should reflect monthly collected fees (membership+upcoming) vs monthly expenses
    monthly_summary = []
    chart_net_income_trend_data = []
    chart_net_income_trend_labels = []
    
    # Iterate through months of the current calendar year
    for i in range(1, 13):
        dummy_date = date(current_year, i, 1)
        month_name_full = dummy_date.strftime('%B')
        month_name_abbr = dummy_date.strftime('%b')
        chart_net_income_trend_labels.append(month_name_abbr)

        # Monthly collected fees (includes current AY and any upcoming AY fees collected in this month)
        monthly_collected_fees = db.query(func.sum(models.PaymentItem.fee)).join(models.User).filter(
            extract('year', models.PaymentItem.updated_at) == current_year, 
            extract('month', models.PaymentItem.updated_at) == i,
            models.PaymentItem.is_paid == True, 
            models.User.organization_id == organization.id,
            models.PaymentItem.student_shirt_order_id.is_(None) # Exclude shirt orders
        ).scalar() or 0.0

        monthly_expenses = db.query(func.sum(models.Expense.amount)).filter(
            extract('year', models.Expense.incurred_at) == current_year, extract('month', models.Expense.incurred_at) == i,
            models.Expense.organization_id == organization.id
        ).scalar() or 0.0

        monthly_net_income = monthly_collected_fees - monthly_expenses
        monthly_summary.append({
            "month": month_name_full, "revenue": monthly_collected_fees, "expenses": monthly_expenses,
            "net_income": monthly_net_income, "net_income_class": "positive" if monthly_net_income >= 0 else "negative"
        })
        # The chart_net_income_trend_data will now reflect the monthly net income based on all collected fees vs expenses for that month
        chart_net_income_trend_data.append(round(monthly_net_income, 2))


    # Num paid/unpaid members based on *current academic year* membership fees
    num_paid_members = db.query(func.count(models.User.id.distinct())).join(models.PaymentItem).filter(
        models.PaymentItem.academic_year == current_academic_year_str,
        models.PaymentItem.is_paid == True, 
        models.User.organization_id == organization.id,
        models.PaymentItem.student_shirt_order_id.is_(None) # Count only members who paid current AY membership fees
    ).scalar() or 0
    total_members = db.query(func.count(models.User.id)).filter(models.User.is_active == True, models.User.organization_id == organization.id).scalar() or 0
    num_unpaid_members = max(0, total_members - num_paid_members)


    financial_data = {
        "organization_id": organization.id, 
        "organization_name": organization.name, 
        "year": str(current_year), # Still calendar year for general summary
        "total_current_balance": total_current_balance, # New definition
        "total_revenue_ytd": turnover_funds, # Now 'Turnover Funds' (previous AYs only)
        "upcoming_funds_ytd": upcoming_funds_collected, # Now 'Upcoming Year Funds' (all future AYs)
        "total_expenses_ytd": total_expenses_ytd, # Still current calendar year expenses
        "net_income_ytd": net_income_ytd, # New definition: Current AY membership revenue - Current AY expenses
        "balance_turnover": round(total_current_balance / turnover_funds, 2) if turnover_funds != 0 else 0.0, # Adjusted ratio
        "total_funds_available": total_current_balance, # This is the same as total_current_balance
        "reporting_date": today.strftime("%B %d, %Y"),
        "top_revenue_source_name": top_revenue_source["name"], 
        "top_revenue_source_amount": top_revenue_source['amount'],
        "largest_expense_category": largest_expense_category, 
        "largest_expense_amount": largest_expense_amount,
        "profit_margin_ytd": profit_margin_ytd, 
        "revenues_breakdown": revenues_breakdown, # Structured by academic year
        "expenses_breakdown": expenses_breakdown, 
        "monthly_summary": monthly_summary, # Monthly data for current calendar year
        "accounts_balances": [], 
        "chart_revenue_data": [current_ay_membership_revenue, total_expenses_ytd], # Reflects current AY revenue vs expenses
        "chart_net_income_data": chart_net_income_trend_data, # Trend for monthly net income (calendar year)
        "chart_net_income_labels": chart_net_income_trend_labels,
        "num_paid_members": num_paid_members, 
        "num_unpaid_members": num_unpaid_members, 
        "total_members": total_members
    }    

    if total_current_balance >= 0:
        financial_data["accounts_balances"] = [            
            {"account": "Savings Account", "balance": round(total_current_balance * 0.2, 2), "last_transaction": (today - timedelta(days=15)).strftime("%Y-%m-%d"), "status": "Active"},
            
        ]

        event_expenses_percentage = 0.10          # 10% - Increased for more realistic event needs
        operations_maintenance_percentage = 0.08   # 8% - Solid for ongoing operations and supplies
        food_refreshments_percentage = 0.05      # 5% - Dedicated for meeting/guest meals
        transportation_logistics_percentage = 0.03 # 3% - For travel and logistics

        # Dedicated Emergency Contingency
        contingency_fund_percentage = 0.15  

        financial_data["accounts_balances"].extend([
            {"account": "Event Expenses (Decoration, Tokens)", "balance": round(total_current_balance * event_expenses_percentage, 2), "last_transaction": today.strftime("%Y-%m-%d"), "status": "Budgeted"},
            {"account": "Operations & Maintenance (Supplies)", "balance": round(total_current_balance * operations_maintenance_percentage, 2), "last_transaction": today.strftime("%Y-%m-%d"), "status": "Budgeted"},
            {"account": "Food & Refreshments (Meeting/Event Meals)", "balance": round(total_current_balance * food_refreshments_percentage, 2), "last_transaction": today.strftime("%Y-%m-%d"), "status": "Budgeted"},
            {"account": "Transportation & Logistics (Fare/Allowance)", "balance": round(total_current_balance * transportation_logistics_percentage, 2), "last_transaction": today.strftime("%Y-%m-%d"), "status": "Budgeted"},
            {"account": "Contingency Fund (Emergency Use)", "balance": round(total_current_balance * contingency_fund_percentage, 2), "last_transaction": today.strftime("%Y-%m-%d"), "status": "Budgeted"}
        ])

        current_sum = sum(acc['balance'] for acc in financial_data["accounts_balances"])
        if abs(current_sum - total_current_balance) > 0.01:
            # Distribute the remainder to the last account for accuracy
            financial_data["accounts_balances"][-1]['balance'] += (total_current_balance - current_sum)
            financial_data["accounts_balances"][-1]['balance'] = round(financial_data["accounts_balances"][-1]['balance'], 2)
    else:
        financial_data["accounts_balances"] = [{"account": "Main Operating Account", "balance": total_current_balance, "last_transaction": today.strftime("%Y-%m-%d"), "status": "Critical"}]

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

    public_api_key = "pk-Z0OSzLvIcOI2UIvDhdTGVVfRSSeiGStnceqwUE7n0Ah"
    encoded_key = base64.b64encode(f"{public_api_key}:".encode()).decode()
    url = "https://pg-sandbox.paymaya.com/checkout/v1/checkouts"
    headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Basic {encoded_key}"}

    payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if not payment_item:
        logging.error(f"Payment item not found for payment_item_id={payment_item_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment item not found")
    
    if hasattr(payment_item, 'is_paid') and payment_item.is_paid: 
        logging.warning(f"Attempted to create payment for already paid PaymentItem ID: {payment_item_id}. User ID: {user.id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This item has already been paid for.")
  
    existing_reusable_payment = db.query(models.Payment).filter(
        models.Payment.payment_item_id == payment_item_id,
        models.Payment.user_id == user.id,
        models.Payment.status.notin_(['success', 'failed']) 
    ).order_by(
        models.Payment.paymaya_payment_id.is_(None).desc()
    ).first()

    db_payment = None
    if existing_reusable_payment:
        db_payment = existing_reusable_payment
        db.refresh(db_payment)
        if db_payment.status != "pending":
            db_payment.status = "pending"
            db.add(db_payment)
        logging.info(f"Reusing existing payment (ID: {db_payment.id}, Current Status: {db_payment.status}) for payment_item_id: {payment_item_id}. PayMaya ID: {db_payment.paymaya_payment_id}")
    else:
        db_payment = crud.create_payment(db, amount=payment_item.fee, user_id=user.id, payment_item_id=payment_item_id)
        db.add(db_payment)
        db.flush() 
        db_payment.status = "pending" 
        db.add(db_payment) 
        
        logging.info(f"Created new payment (ID: {db_payment.id}) and set status to 'pending' for payment_item_id: {payment_item_id}.")

    if payment_item.student_shirt_order_id:
        shirt_order = db.query(models.StudentShirtOrder).filter(
            models.StudentShirtOrder.id == payment_item.student_shirt_order_id
        ).first()

        if shirt_order:
            if shirt_order.payment_id != db_payment.id: 
                shirt_order.payment_id = db_payment.id
                db.add(shirt_order) 
                db.commit() 
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
    
    payload = {
        "totalAmount": {"currency": "PHP", "value": payment_item.fee},
        "requestReferenceNumber": f"shirt-order-{payment_item_id}-{db_payment.id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}", 
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
        crud.update_payment(db, payment_id=db_payment.id, paymaya_payment_id=paymaya_payment_id)
        db.commit()         
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
    public_api_key = "pk-Z0OSzLvIcOI2UIvDhdTGVVfRSSeiGStnceqwUE7n0Ah"
    encoded_key = base64.b64encode(f"{public_api_key}:".encode()).decode()
    url = "https://pg-sandbox.paymaya.com/checkout/v1/checkouts"
    headers = {"accept": "application/json", "content-type": "application/json", "authorization": f"Basic {encoded_key}"}

    payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if not payment_item:
        logging.error(f"Payment item not found for payment_item_id={payment_item_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment item not found")
 
    if payment_item.is_paid: 
        logging.warning(f"Attempted to create payment for already paid PaymentItem ID: {payment_item_id}. User ID: {user.id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This item has already been paid for.")
    
    existing_reusable_payment = db.query(models.Payment).filter(
        models.Payment.payment_item_id == payment_item_id,
        models.Payment.user_id == user.id,
        models.Payment.status.notin_(['success', 'failed']) 
    ).order_by(
        models.Payment.paymaya_payment_id.is_(None).desc() 
    ).first()

    db_payment = None
    if existing_reusable_payment:
        db_payment = existing_reusable_payment
        db.refresh(db_payment)
        if db_payment.status != "pending":
            db_payment.status = "pending"
            db.add(db_payment)
        logging.info(f"Reusing existing payment (ID: {db_payment.id}, Current Status: {db_payment.status}) for payment_item_id: {payment_item_id}. PayMaya ID: {db_payment.paymaya_payment_id}")
    else:
        db_payment = crud.create_payment(db, amount=payment_item.fee, user_id=user.id, payment_item_id=payment_item_id)
        db.add(db_payment)
        db.flush() 
        db_payment.status = "pending" 
        db.add(db_payment)         
        logging.info(f"Created new payment (ID: {db_payment.id}) and set status to 'pending' for payment_item_id: {payment_item_id}.")

    if payment_item.student_shirt_order_id:
        shirt_order = db.query(models.StudentShirtOrder).filter(
            models.StudentShirtOrder.id == payment_item.student_shirt_order_id
        ).first()

        if shirt_order:
            if shirt_order.payment_id != db_payment.id: 
                shirt_order.payment_id = db_payment.id
                db.add(shirt_order) 
                db.commit() 
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
        crud.update_payment(db, payment_id=db_payment.id, paymaya_payment_id=paymaya_payment_id)
        db.commit() 
        
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
    logging.info(f"Payment success callback received: paymentId={paymentId}, paymentItemId={paymentItemId}")

    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if not payment:
        logging.error(f"Payment record not found for paymentId={paymentId}. This might indicate an invalid callback or a race condition.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

    db.refresh(payment) 
    logging.info(f"Retrieved payment (ID: {payment.id}, Current Status: {payment.status}, User ID: {payment.user_id}) for update.")

    if payment.status == "success":
        logging.warning(f"Payment ID {paymentId} is already marked as success. Skipping further updates to prevent duplicate processing.")

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

    try:
        updated_payment = crud.update_payment(db, payment_id=payment.id, status="success")
        if not updated_payment:
            logging.error(f"Failed to update payment status for paymentId={paymentId} to 'success'. CRUD operation returned None.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update payment status.")
        logging.info(f"Payment ID {payment.id} status successfully updated to 'success'.")
    except Exception as e:
        logging.exception(f"Exception while updating payment status for paymentId={payment.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating payment status.")

    payment_item = crud.get_payment_item_by_id(db, payment_item_id=paymentItemId)
    if not payment_item:
        logging.error(f"Associated Payment Item not found for paymentItemId={paymentItemId}. This is critical for Payment ID {payment.id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated Payment Item not found.")

    if not payment_item.is_paid: 
        try:
            crud.mark_payment_item_as_paid(db, payment_item_id=paymentItemId)
            logging.info(f"Payment Item ID {paymentItemId} marked as paid successfully.")
        except Exception as e:
            logging.exception(f"Exception while marking Payment Item {paymentItemId} as paid: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error marking payment item as paid.")
    else:
        logging.info(f"Payment Item ID {paymentItemId} was already marked as paid. No action needed.")

    if payment_item.student_shirt_order_id:
        logging.info(f"Payment Item {paymentItemId} is linked to Student Shirt Order ID: {payment_item.student_shirt_order_id}.")
        shirt_order = crud.get_student_shirt_order_by_id(db, order_id=payment_item.student_shirt_order_id)
        if shirt_order:
            if shirt_order.status != "paid": 
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
                                              
                        if updated_shirt_order.campaign and updated_shirt_order.campaign.organization_id:
                            organization = db.query(models.Organization).filter(models.Organization.id == updated_shirt_order.campaign.organization_id).first()
                            if organization:
                                for admin in organization.admins:
                                    message = f"Shirt Order Payment: Student {updated_shirt_order.student_name} has paid for Shirt Order ID: {updated_shirt_order.id} (Campaign: {updated_shirt_order.campaign.title})."
                                    crud.create_notification(db, message, 
                                                            admin_id=admin.admin_id,
                                                            organization_id=organization.id, 
                                                            notification_type="shirt_order_payment",
                                                            payment_id=payment.id, 
                                                            url=f"/admin/shirt_management", 
                                                            event_identifier=f"shirt_order_payment_admin_{admin.admin_id}_order_{updated_shirt_order.id}") 
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
        logging.info(f"Payment Item {paymentItemId} is for general fees.")
        user = db.query(models.User).filter(models.User.id == payment.user_id).first()
        if user and user.organization and payment_item.academic_year and payment_item.semester: 
            logging.info(f"User {user.id} and organization {user.organization.id} found for general fee payment.")
            for admin in user.organization.admins:
                message = f"Payment Successful: {user.first_name} {user.last_name} has successfully paid {payment.amount} for {payment_item.academic_year} {payment_item.semester} fees."
                crud.create_notification(db, message, admin_id=admin.admin_id, organization_id=user.organization.id, notification_type="payment_success",
                                         payment_id=payment.id, 
                                         url=f"/admin/payments/total_members?student_number={user.student_number}",
                                         event_identifier=f"payment_success_admin_{admin.admin_id}_payment_{payment.id}")
                logging.info(f"Notification created for admin {admin.admin_id} for general fee payment {payment.id}.")
        else:
            logging.warning(f"Could not find user, organization, or academic year/semester for general fee payment {payment.id}. Notification skipped.")
    
    try:
        db.commit() 
        logging.info(f"Database transaction committed successfully for payment_id={payment.id}.")
    except Exception as e:
        db.rollback() 
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

    print(f"DEBUG: Current User ID: {user.id}")

    payment_items_from_db = db.query(models.PaymentItem).filter(
        models.PaymentItem.user_id == user.id,
        models.PaymentItem.is_not_responsible == False,
        models.PaymentItem.student_shirt_order_id == None
    ).order_by(models.PaymentItem.academic_year).all()

    print(f"DEBUG: Initial DB query found {len(payment_items_from_db)} payment items with NO student_shirt_order_id.")

    past_due_items = []
    unpaid_upcoming_items = []

    for item in payment_items_from_db: 
        if not item.is_paid and item.is_past_due:
            past_due_items.append(item)
        elif not item.is_paid and not item.is_past_due:
            unpaid_upcoming_items.append(item)

    items_with_shirt_id_in_past_due = [
        item for item in past_due_items if item.student_shirt_order_id is not None
    ]
    print(f"DEBUG: Found {len(items_with_shirt_id_in_past_due)} payment items WITH student_shirt_order_id in past_due_items (should be 0).")

    items_with_shirt_id_in_unpaid_upcoming = [
        item for item in unpaid_upcoming_items if item.student_shirt_order_id is not None
    ]
    print(f"DEBUG: Found {len(items_with_shirt_id_in_unpaid_upcoming)} payment items WITH student_shirt_order_id in unpaid_upcoming_items (should be 0).")

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
        if (
            payment_item is not None and
            payment_item.academic_year is not None and
            payment_item.semester is not None and
            payment_item.fee is not None and
            payment_item.due_date is not None and
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
            logging.warning(f"Skipping payment ID {payment.id} due to missing PaymentItem or incomplete data.")
            continue

    context = await get_base_template_context(request, db)
    context.update({"payment_history": payment_history_data, "current_user": user})
    return templates.TemplateResponse("student_dashboard/payment_history.html", context)

# Financial Statement (User)
@app.get("/FinancialStatement", response_class=HTMLResponse, name="financial_statement")
async def financial_statement(request: Request, db: Session = Depends(get_db)):
    """
    Retrieves and categorizes financial data for a user and their organization,
    excluding shirt payments from membership fee calculations.
    """
    user, user_org = get_current_user_with_org(request, db)

    # Filter out payment items related to student shirt orders for membership fee calculations
    all_user_membership_payment_items = db.query(models.PaymentItem).filter(
        models.PaymentItem.user_id == user.id,
        models.PaymentItem.student_shirt_order_id.is_(None)  # Exclude shirt orders
    ).all()

    total_paid_by_user = sum(item.fee for item in all_user_membership_payment_items if item.is_paid)
    total_outstanding_fees_user = sum(item.fee for item in all_user_membership_payment_items if not item.is_paid)
    total_past_due_fees_user = sum(item.fee for item in all_user_membership_payment_items if not item.is_paid and item.due_date and item.due_date < date.today())

    collected_fees_by_category_user = defaultdict(float)
    outstanding_fees_by_category_user = defaultdict(float)

    for item in all_user_membership_payment_items:
        category_name = ""
        # The `student_shirt_order_id` check is no longer strictly necessary here for categorizing
        # since we've already filtered them out from `all_user_membership_payment_items`.
        # However, keeping it makes the categorization logic robust if the filtering changes.
        if item.student_shirt_order_id is not None:
            # This branch won't be hit with the current filtering but is kept for logical completeness
            category_name = "Student Shirt Order Fees"
        elif item.academic_year and item.semester:
            category_name = f"AY {item.academic_year} - {item.semester} Fees (Membership)"
        else:
            category_name = "Miscellaneous Fees" 

        if item.is_paid:
            collected_fees_by_category_user[category_name] += item.fee
        else:
            outstanding_fees_by_category_user[category_name] += item.fee

    organization_total_revenue = 0.0
    # Filter organization's paid payment items to exclude shirt orders
    all_org_paid_membership_payment_items = db.query(models.PaymentItem).join(models.User).filter(
        models.PaymentItem.is_paid == True,
        models.User.organization_id == (user_org.id if user_org else None),
        models.PaymentItem.student_shirt_order_id.is_(None)  # Exclude shirt orders
    ).all()
    organization_total_revenue = sum(item.fee for item in all_org_paid_membership_payment_items)

    all_expenses_org = db.query(models.Expense).filter(models.Expense.organization_id == (user_org.id if user_org else None)).all()
    total_expenses_org = sum(expense.amount for expense in all_expenses_org)
    net_income_org = organization_total_revenue - total_expenses_org

    expenses_by_category_org = defaultdict(float)
    for expense in all_expenses_org:
        expenses_by_category_org[expense.category if expense.category else "Uncategorized"] += expense.amount

    financial_summary_items_combined = []
    # Only include membership-related payments in the combined summary
    for item in all_user_membership_payment_items:
        if item.is_paid and (item.updated_at or item.created_at):
            relevant_date = item.updated_at or item.created_at
            summary_category_name = ""
            if item.academic_year and item.semester:
                summary_category_name = f"AY {item.academic_year} - {item.semester} Fees (Your Payment)"
            else:
                summary_category_name = "Miscellaneous Fees (Your Payment)"
            financial_summary_items_combined.append({"date": relevant_date, "event_item": summary_category_name, "inflows": item.fee, "outflows": 0.00})

    for expense in all_expenses_org:
        if expense.incurred_at:
            financial_summary_items_combined.append({"date": expense.incurred_at, "event_item": f"Org Expense - {expense.category if expense.category else 'Uncategorized'}", "inflows": 0.00, "outflows": expense.amount})

    financial_summary_items_combined.sort(key=lambda x: x['date'])
    for item in financial_summary_items_combined:
        item['date'] = item['date'].strftime("%Y-%m-%d")

    months_full = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    org_inflows_by_month_current_year = defaultdict(float)
    # Use the filtered list for organization inflows
    for item in all_org_paid_membership_payment_items:
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

        monthly_data_org[month_name_lower] = {
            "starting_balance": starting_balance,
            "inflows": inflows_this_month_org,
            "outflows": outflows_this_month_org,
            "ending_balance": ending_balance
        }

    financial_data = {
        "user_financials": {
            "total_paid_by_user": total_paid_by_user,
            "total_outstanding_fees": total_outstanding_fees_user,
            "total_past_due_fees": total_past_due_fees_user,
            "collected_fees_by_category": [{"category": k, "amount": v} for k, v in collected_fees_by_category_user.items()],
            "outstanding_fees_by_category": [{"category": k, "amount": v} for k, v in outstanding_fees_by_category_user.items()],
        },
        "organization_financials": {
            "total_revenue_org": organization_total_revenue,
            "total_expenses_org": total_expenses_org,
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
                category_name = ""
                if item.student_shirt_order_id is not None:
                    category_name = "Student Shirt Order"
                elif item.academic_year and item.semester:
                    category_name = f"AY {item.academic_year} - {item.semester} Membership Fee"
                else:
                    category_name = "Miscellaneous Fee"
                status_str = "Paid" if item.is_paid else ("Past Due" if not item.is_paid and item.due_date and item.due_date < date.today() else "Unpaid")
                
                all_financial_events.append((relevant_date, f"You Paid - {category_name}", item.fee if item.is_paid else 0.00, 0.00, status_str, item.fee, item))

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
        if event_date < start_date_of_month: 
            current_running_balance += inflow - outflow
        else:
            starting_balance_month = current_running_balance
            break
    if not all_financial_events or all_financial_events[0][0] >= start_date_of_month:
        starting_balance_month = 0.00
    
    current_running_balance = starting_balance_month 

    for event_date, description, inflow, outflow, status_str, original_value, original_item_obj in all_financial_events:
        if start_date_of_month <= event_date <= end_date_of_month: 
            is_user_payment_event = "You Paid" in description 
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
    user_role = None 

    if user_id:
        current_entity = db.query(models.User).filter(models.User.id == user_id).first()
        if current_entity:
            first_name = current_entity.first_name
            profile_picture = current_entity.profile_picture
            is_verified_status = current_entity.is_verified
            user_role = "user" 
            if current_entity.organization:
                organization_data = schemas.Organization.model_validate(current_entity.organization)
                organization_theme_color = current_entity.organization.theme_color
    elif admin_id:
        current_entity = db.query(models.Admin).options(joinedload(models.Admin.organizations)).filter(models.Admin.admin_id == admin_id).first()
        if current_entity:
            first_name = current_entity.first_name
            profile_picture = current_entity.profile_picture 
            print(f"DEBUG: Backend fetched admin profile_picture for admin_id {admin_id}: {profile_picture}") 
            user_role = "admin"
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

    return schemas.UserDataResponse(
        first_name=first_name,
        profile_picture=profile_picture,
        organization=organization_data,
        is_verified=is_verified_status,
        role=user_role 
    )

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

@app.get("/bulletin/heart/{post_id}/users", response_model=schemas.LikedUsersResponse)
async def get_users_who_liked_post(
    post_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = None
    user_org = None
    admin = None
    admin_org = None

    try:
        user, user_org = get_current_user_with_org(request, db)
    except HTTPException:
        try:
            admin, admin_org = get_current_admin_with_org(request, db)
        except HTTPException:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    post = db.query(models.BulletinBoard).options(
        joinedload(models.BulletinBoard.admin).joinedload(models.Admin.organizations)
    ).get(post_id)

    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    org_id = None
    if user_org:
        org_id = user_org.id
    elif admin_org:
        org_id = admin_org.id

    if not post.admin or not post.admin.organizations or post.admin.organizations[0].id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You can only view likes for posts within your organization.")

    likers_query = db.query(models.User).join(
        models.UserLike, models.User.id == models.UserLike.user_id
    ).filter(models.UserLike.post_id == post_id).all()

    likers_list = [
        schemas.UserLikedPost(
            id=liker.id,
            first_name=liker.first_name,
            last_name=liker.last_name,
            email=liker.email,
            profile_picture=liker.profile_picture
        ) for liker in likers_query
    ]

    return schemas.LikedUsersResponse(
        post_id=post.post_id,
        title=post.title,
        likers=likers_list
    )

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