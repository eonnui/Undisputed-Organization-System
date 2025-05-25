from sqlalchemy.orm import Session
from . import models, schemas  # Import your models and schemas
from passlib.context import CryptContext
from datetime import datetime, date  # Import both datetime and date
import logging
from sqlalchemy.sql import exists
from typing import Optional

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
