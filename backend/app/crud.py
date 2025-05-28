from sqlalchemy.orm import Session
from . import models, schemas  # Import your models and schemas
from passlib.context import CryptContext
from datetime import datetime, date  # Import both datetime and date
import logging
from sqlalchemy.sql import exists
from typing import Optional, Tuple # Added Tuple for type hints
import json # Added json import for generate_custom_palette

# Configure logging
logging.basicConfig(level=logging.INFO)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_organization_by_name(db: Session, organization_name: str):
    """
    Retrieves an Organization by its name.
    """
    return db.query(models.Organization).filter(models.Organization.name == organization_name).first()

def create_user(db: Session, user: schemas.UserCreate):
    """
    Creates a new user, correctly linking to an organization by ID.
    """
    user_exists = db.query(exists().where(models.User.student_number == user.student_number)).scalar()
    if user_exists:
        existing_user = db.query(models.User).filter(models.User.student_number == user.student_number).first()
        logging.info(f"User with student_number: {user.student_number} already exists.")
        return existing_user

    hashed_password = pwd_context.hash(user.password)

    # Look up the Organization object by name to get its ID
    organization_obj = None
    organization_id_to_assign = None
    if user.organization: # user.organization is the name string from the frontend/schema
        organization_obj = get_organization_by_name(db, user.organization)
        if organization_obj:
            organization_id_to_assign = organization_obj.id
        else:
            logging.warning(f"Organization '{user.organization}' not found during user creation. User will be created without an assigned organization (organization_id will be NULL).")
            # You might want to raise an HTTPException here if an organization is mandatory
            # from fastapi import HTTPException
            # raise HTTPException(status_code=400, detail=f"Organization '{user.organization}' not found.")

    db_user = models.User(
        student_number=user.student_number,
        email=user.email,
        # Assign the ID to the foreign key column (organization_id), NOT the relationship attribute (organization)
        organization_id=organization_id_to_assign,
        first_name=user.first_name,
        last_name=user.last_name,
        hashed_password=hashed_password,
        # Other fields from schemas.UserCreate which might not be directly in models.User but are part of the schema
        # If your schemas.UserCreate has more fields than the direct columns in models.User,
        # you need to explicitly map them or adjust schemas.UserCreate.
        # Assuming UserCreate fields map directly to User model columns:
        # name=user.name, # If name is in UserCreate
        # campus=user.campus, # If campus is in UserCreate
        # etc.
        # Based on your schemas.UserCreate, these are the fields:
        # student_number, email, organization (handled above), first_name, last_name, password (hashed)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logging.info(f"Created user with student_number: {user.student_number}, email: {user.email}")
    return db_user

# --- Helper functions for color manipulation (from ad.txt) ---
def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Converts a hex color string (#RRGGBB) to an RGB tuple (R, G, B)."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb_color: Tuple[int, int, int]) -> str:
    """Converts an RGB tuple (R, G, B) to a hex color string (#RRGGBB)."""
    return '#%02x%02x%02x' % rgb_color

def adjust_rgb_lightness(rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    """Adjusts the lightness of an RGB color by a factor (e.g., 0.8 for darker, 1.2 for lighter)."""
    r, g, b = rgb
    r = int(max(0, min(255, r * factor)))
    g = int(max(0, min(255, g * factor)))
    b = int(max(0, min(255, b * factor)))
    return (r, g, b)

def get_contrast_text_color(bg_hex: str) -> str:
    """Returns #FFFFFF or #000000 based on the perceived lightness of the background color."""
    r, g, b = hex_to_rgb(bg_hex)
    # Calculate perceived lightness (luminance)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"

def generate_custom_palette(theme_color_hex: str) -> str:
    """
    Generates a full custom CSS variable palette based on a primary theme color.
    Uses a predefined template and adjusts relevant colors.
    """
    # Base template derived from the "Samahan ng Sikolohiya" example.
    base_palette = {
        "--org-bg-color": "#fdf5f5",
        "--org-login-bg": "#5c1011",
        "--org-button-bg": "#9a1415",
        "--org-button-text": "#FFFFFF",
        "--org-hover-effect": "#7a1012",
        "--org-accent-light": "#d32f2f",
        "--org-accent-dark": "#5c0b0b",
        "--org-highlight": "#ffebee",
        "--org-text-primary": "#212121",
        "--org-text-secondary": "#757575",
        "--org-text-inverse": "#FFFFFF",
        "--org-hover-dark": "#424242",
        "--org-hover-accent": "#b71c1c",
        "--org-focus-border": "transparent",
        "--org-success": "#4CAF50",
        "--org-error": "#F44336",
        "--org-warning": "#FFC107",
        "--org-info": "#2196F3",
        "--org-bg-secondary": "#FFFFFF",
        "--org-bg-dark": "#1a1a1a",
        "--org-border-light": "transparent",
        "--org-border-medium": "transparent",
        "--org-nav-item-bg": "transparent",
        "--org-nav-item-hover-bg": "rgba(154, 20, 21, 0.05)",
        "--org-nav-item-selected-bg": "rgba(154, 20, 21, 0.1)",
        "--org-sidebar-bg-color": "#a83232",
        "--org-sidebar-border-color": "transparent",
        "--org-logo-border-color": "transparent",
        "--org-nav-icon-color": "#FFFFFF",
        "--org-nav-hover-accent-color": "#fdf5f5",
        "--org-nav-selected-border-color": "transparent",
        "--org-top-bar-border-color": "transparent",
        "--org-menu-button-hover-bg": "rgba(0, 0, 0, 0.05)",
        "--org-profile-pic-border-color": "transparent",
        "--org-dropdown-bg": "#FFFFFF",
        "--org-dropdown-border": "transparent",
        "--org-dropdown-item-hover-bg": "#f5f5f5",
        "--org-dashboard-bg-color": "#fdf5f5",
        "--org-dashboard-title-color": "#5c0b0b",
        "--org-shadow-base-rgb": "0, 0, 0",
        "--org-card-bg": "#FFFFFF",
        "--org-announcement-card-bg": "#fefefe",
        "--org-dashboard-accent-primary": "#d32f2f",
        "--org-announcement-text-color": "#212121",
        "--org-announcement-meta-color": "#757575",
        "--org-view-details-hover": "#b71c1c",
        "--org-event-placeholder-color": "#9e9e9e",
        "--org-faq-border-color": "transparent",
        "--org-faq-item-bg": "#fefefe",
        "--org-faq-question-hover-bg": "#f5f5f5",
        "--org-faq-answer-color": "#424242",
        "--org-empty-state-color": "#9e9e9e",
        "--org-empty-state-bg": "#fefefe",
        "--org-post-card-border": "transparent",
        "--org-profile-image-bg": "#e0e0e0",
        "--org-post-info-color": "#5a5a5a",
        "--org-post-date-color": "#9e9e9e",
        "--org-post-content-color": "#333333",
        "--org-post-actions-color": "#757575",
        "--org-heart-hover-color": "#e57373",
        "--org-heart-button-color": "#e53935",
        "--org-pinned-bg": "#FFC107",
        "--org-event-meta-color": "#757575",
        "--org-event-description-color": "#424242",
        "--org-event-item-border": "transparent",
        "--org-event-item-hover-bg": "#f5f5f5",
        "--org-event-tag-bg": "#ffebee",
        "--org-event-tag-text": "#b71c1c",
        "--org-academic-tag-bg": "#fbe9e7",
        "--org-academic-tag-text": "#c62828",
        "--org-sports-tag-bg": "#e8f5e9",
        "--org-sports-tag-text": "#388e3c",
        "--org-arts-tag-bg": "#fffde7",
        "--org-arts-tag-text": "#f9a825",
        "--org-music-tag-bg": "#ffecb3",
        "--org-music-tag-text": "#f57f17",
        "--org-esports-tag-bg": "#e0f7fa",
        "--org-esports-tag-text": "#00838f",
        "--org-cultural-tag-bg": "#f3e5f5",
        "--org-cultural-tag-text": "#7b1fa2",
        "--org-join-btn-bg": "#43a047",
        "--org-join-btn-hover-bg": "#388e3c",
        "--org-leave-btn-bg": "#e53935",
        "--org-leave-btn-hover-bg": "#d32f2f",
        "--org-event-full-bg": "#9e9e9e",
        "--org-event-full-text": "#FFFFFF",
        "--org-join-button-bg": "#43a047",
        "--org-join-button-hover-bg": "#45a049",
        "--org-leave-button-bg": "#f44336",
        "--org-leave-button-hover-bg": "#d32f2f",
        "--org-full-button-bg": "#bdbdbd",
        "--org-full-button-text": "#424242",
        "--org-participants-count-color": "#757575",
        "--org-payments-container-bg": "#fdf5f5",
        "--org-border-light-darker": "transparent",
        "--org-text-primary-darker": "#000000",
        "--org-table-header-bg-payments": "#fbc4cb",
        "--org-table-header-text-payments": "#333333",
        "--org-table-data-text": "#333333",
        "--org-background-light-alt-darker": "#fefafa",
        "--org-status-unpaid-bg": "#ffebee",
        "--org-status-unpaid-text": "#b71c1c",
        "--org-error-border": "transparent",
        "--org-pay-button-bg-payments": "#e53935",
        "--org-pay-button-hover-bg-payments": "#d32f2f",
        "--org-standby-button-bg-payments": "#bdbdbd",
        "--org-button-disabled-text-darker": "#757575",
        "--org-past-due-bg": "#ffebee",
        "--org-past-due-text": "#b71c1c",
        "--org-past-due-hover-bg": "#ffcdd2",
        "--org-past-due-hover-text": "#b71c1c",
        "--org-surface": "#FFFFFF",
        "--org-radius-lg": "12px",
        "--org-shadow-md": "0 4px 10px rgba(0, 0, 0, 0.12)",
        "--org-transition": "all 0.3s ease-in-out",
        "--org-shadow-lg": "0 6px 15px rgba(0, 0, 0, 0.18)",
        "--org-primary": "#9a1415",
        "--org-radius-md": "8px",
        "--org-shadow-sm": "0 2px 5px rgba(0, 0, 0, 0.08)",
        "--org-text-light": "#FFFFFF",
        "--org-secondary-color": "#f5f5f5",
        "--org-primary-light": "#ffcdd2",
        "--org-primary-hover": "#b71c1c",
        "--org-settings-section-bg": "#f5f5f5",
        "--org-settings-title-color": "#212121",
        "--org-button-group-button-update-bg": "#a83232",
        "--org-button-group-button-update-hover-bg": "#862828",
        "--org-button-group-button-clear-bg": "#FFFFFF",
        "--org-button-group-button-clear-hover-bg": "transparent",
        "--org-profile-picture-border": "transparent",
        "--org-change-profile-pic-bg": "#a83232",
        "--org-change-profile-pic-hover-bg": "#862828",
        "--org-student-info-section-bg": "#FFFFFF",
        "--org-verified-bg": "#4CAF50",
        "--org-verified-text": "#FFFFFF",
        "--org-unverified-bg": "#FFC107",
        "--org-unverified-text": "#212121",
        "--org-registration-form-section-bg": "#FFFFFF",
        "--org-edit-icon-bg": "#FFFFFF",
        "--org-edit-icon-hover-bg": "#f5f5f5",
        "--org-read-only-input-bg": "#fdf5f5",
        "--org-read-only-input-text": "#757575",
        "--org-form-group-label-color": "#212121",
        "--org-form-group-input-border": "transparent",
        "--org-form-group-input-focus-border": "transparent"
    }

    custom_palette = base_palette.copy()
    theme_rgb = hex_to_rgb(theme_color_hex)

    dark_theme_rgb = adjust_rgb_lightness(theme_rgb, 0.7)
    darker_theme_rgb = adjust_rgb_lightness(theme_rgb, 0.5)
    light_theme_rgb = adjust_rgb_lightness(theme_rgb, 1.2)
    lighter_theme_rgb = adjust_rgb_lightness(theme_rgb, 1.6)

    dark_theme_hex = rgb_to_hex(dark_theme_rgb)
    darker_theme_hex = rgb_to_hex(darker_theme_rgb)
    light_theme_hex = rgb_to_hex(light_theme_rgb)
    lighter_theme_hex = rgb_to_hex(lighter_theme_rgb)

    whiteness_factor = .9
    very_light_bg_rgb = (
        int(theme_rgb[0] * (1 - whiteness_factor) + 255 * whiteness_factor),
        int(theme_rgb[1] * (1 - whiteness_factor) + 255 * whiteness_factor),
        int(theme_rgb[2] * (1 - whiteness_factor) + 255 * whiteness_factor)
    )
    very_light_bg_rgb = (
        max(0, min(255, very_light_bg_rgb[0])),
        max(0, min(255, very_light_bg_rgb[1])),
        max(0, min(255, very_light_bg_rgb[2]))
    )
    very_light_bg_hex = rgb_to_hex(very_light_bg_rgb)

    custom_palette["--org-bg-color"] = very_light_bg_hex
    custom_palette["--org-secondary-color"] = very_light_bg_hex
    custom_palette["--org-dashboard-bg-color"] = very_light_bg_hex
    custom_palette["--org-payments-container-bg"] = very_light_bg_hex
    custom_palette["--org-nav-hover-accent-color"] = very_light_bg_hex
    custom_palette["--org-settings-section-bg"] = very_light_bg_hex
    custom_palette["--org-read-only-input-bg"] = very_light_bg_hex

    button_text_color = get_contrast_text_color(theme_color_hex)

    custom_palette["--org-primary"] = theme_color_hex
    custom_palette["--org-button-bg"] = theme_color_hex
    custom_palette["--org-hover-effect"] = dark_theme_hex
    custom_palette["--org-accent-light"] = light_theme_hex
    custom_palette["--org-accent-dark"] = darker_theme_hex
    custom_palette["--org-hover-accent"] = dark_theme_hex
    custom_palette["--org-primary-hover"] = dark_theme_hex
    custom_palette["--org-primary-light"] = lighter_theme_hex
    custom_palette["--org-dashboard-accent-primary"] = light_theme_hex

    custom_palette["--org-login-bg"] = darker_theme_hex
    custom_palette["--org-sidebar-bg-color"] = dark_theme_hex
    custom_palette["--org-nav-item-hover-bg"] = f"rgba({theme_rgb[0]}, {theme_rgb[1]}, {theme_rgb[2]}, 0.05)"
    custom_palette["--org-nav-item-selected-bg"] = f"rgba({theme_rgb[0]}, {theme_rgb[1]}, {theme_rgb[2]}, 0.1)"
    custom_palette["--org-nav-icon-color"] = button_text_color

    custom_palette["--org-button-text"] = "#FFFFFF"
    custom_palette["--org-dashboard-title-color"] = darker_theme_hex
    custom_palette["--org-text-light"] = button_text_color

    custom_palette["--org-event-tag-bg"] = lighter_theme_hex
    custom_palette["--org-event-tag-text"] = dark_theme_hex

    custom_palette["--org-academic-tag-bg"] = adjust_rgb_lightness(hex_to_rgb(theme_color_hex), 1.4)
    custom_palette["--org-academic-tag-text"] = darker_theme_hex

    custom_palette["--org-table-header-bg-payments"] = lighter_theme_hex
    custom_palette["--org-table-header-text-payments"] = get_contrast_text_color(lighter_theme_hex)

    custom_palette["--org-settings-title-color"] = darker_theme_hex

    custom_palette["--org-button-group-button-update-bg"] = dark_theme_hex
    custom_palette["--org-button-group-button-update-hover-bg"] = darker_theme_hex
    custom_palette["--org-change-profile-pic-bg"] = dark_theme_hex
    custom_palette["--org-change-profile-pic-hover-bg"] = darker_theme_hex

    custom_palette["--org-highlight"] = very_light_bg_hex
    custom_palette["--org-primary"] = theme_color_hex

    return json.dumps(custom_palette, indent=2)

# --- END FIX FOR AttributeError ---


def get_user(db: Session, identifier: str):
    """
    Retrieves a user by student_number or email.
    """
    user = db.query(models.User).filter(models.User.student_number == identifier).first()
    if not user:
        user = db.query(models.User).filter(models.User.email == identifier).first()
    return user


def authenticate_user(db: Session, identifier: str, password: str) -> models.User | None:
    """
    Authenticates a user (student or admin) based on student number or email.
    """
    user = get_user(db, identifier)
    if not user:
        logging.warning(f"User with identifier: {identifier} not found.")
        return None
    if not pwd_context.verify(password, user.hashed_password):
        logging.warning(f"Invalid password for user: {identifier}")
        return None
    logging.info(f"User {identifier} authenticated successfully.")
    return user


def authenticate_admin_by_email(db: Session, email: str, password: str) -> models.Admin | None:
    """
    Authenticates an admin user by email.
    """
    admin = db.query(models.Admin).filter(models.Admin.email == email).first()
    if not admin:
        logging.warning(f"Admin with email: {email} not found.")
        return None
    if not pwd_context.verify(password, admin.password):
        logging.warning(f"Invalid password for admin: {email}")
        return None
    logging.info(f"Admin {email} authenticated successfully.")
    return admin


# Payment CRUD operations
def create_payment(db: Session, user_id: int, amount: float):
    """Creates a new payment record."""
    db_payment = models.Payment(
        user_id=user_id,
        amount=amount,
        created_at=date.today(),
        updated_at=date.today(),
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    logging.info(f"Created payment with user_id: {user_id}, amount: {amount}")
    return db_payment


def get_payment_by_id(db: Session, payment_id: int):
    """Retrieves a payment record by its ID."""
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if payment:
        logging.info(f"Retrieved payment with id: {payment_id}")
        return payment
    else:
        logging.warning(f"Payment with id: {payment_id} not found.")
        return None


def update_payment(
    db: Session,
    payment_id: int,
    paymaya_payment_id: Optional[str] = None,
    status: Optional[str] = None,
    payment_item_id: Optional[int] = None,
):
    """Updates a payment record's PayMaya ID, status, and/or payment_item_id."""
    db_payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if db_payment:
        if paymaya_payment_id is not None:
            db_payment.paymaya_payment_id = paymaya_payment_id
        if status is not None:
            db_payment.status = status
        if payment_item_id is not None:
            db_payment.payment_item_id = payment_item_id
        db_payment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_payment)
        logging.info(
            f"Updated payment with id: {payment_id}, paymaya_payment_id: {paymaya_payment_id}, status: {status}, payment_item_id: {payment_item_id}"
        )
        return db_payment
    else:
        logging.warning(f"Payment with id: {payment_id} not found for update.")
        return None


def add_payment_item(
    db: Session,
    academic_year: str,
    semester: str,
    fee: float,
    user_id: int,
    due_date: Optional[date] = None,
    year_level_applicable: Optional[int] = None,
    is_past_due: bool = False,
):
    """Adds a new payment item to the database."""
    db_payment_item = models.PaymentItem(
        academic_year=academic_year,
        semester=semester,
        fee=fee,
        user_id=user_id,
        due_date=due_date,
        created_at=date.today(),
        updated_at=date.today(),
        year_level_applicable=year_level_applicable,
        is_past_due=is_past_due,
    )
    db.add(db_payment_item)
    db.commit()
    db.refresh(db_payment_item)
    return db_payment_item


def get_all_payment_items(db: Session):
    """Retrieves all unpaid payment items from the database."""
    payment_items = db.query(models.PaymentItem).filter(models.PaymentItem.is_paid == False).all()
    logging.info(f"Retrieved all unpaid payment items. Count: {len(payment_items)}")
    return payment_items


def get_payment_item_by_id(db: Session, payment_item_id: int):
    """Retrieves a specific payment item by its ID."""
    payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if payment_item:
        logging.info(f"Retrieved payment item with id: {payment_item_id}")
    else:
        logging.warning(f"Payment item with id: {payment_item_id} not found.")
    return payment_item


def mark_payment_item_as_paid(db: Session, payment_item_id: int):
    """Marks a payment item as paid."""
    db_payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if db_payment_item:
        db_payment_item.is_paid = True
        db.commit()
        db_payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
        if db_payment_item:
            db_payment_item.created_at = db_payment_item.created_at
            db_payment_item.updated_at = db_payment_item.updated_at
        logging.info(f"Payment item with id: {payment_item_id} marked as paid.")
        return db_payment_item
    else:
        logging.warning(f"Payment item with id: {payment_item_id} not found for marking as paid.")
    return None
