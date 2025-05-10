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


def get_user(db: Session, identifier: str):
    """
    Retrieves a user by student_number or email.
    """
    user = db.query(models.User).filter(models.User.student_number == identifier).first()
    if not user:
        user = db.query(models.User).filter(models.User.email == identifier).first()
    return user


def create_user(db: Session, user: schemas.UserCreate):
    """
    Creates a new user with a specific ID if they don't exist.  Modified to handle ID.
    """
    user_exists = db.query(exists().where(models.User.student_number == user.student_number)).scalar()
    if not user_exists:
        hashed_password = pwd_context.hash(user.password)
        db_user = models.User(
            student_number=user.student_number,
            email=user.email,
            organization=user.organization,
            first_name=user.first_name,
            last_name=user.last_name,
            hashed_password=hashed_password,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logging.info(f"Created user with student_number: {user.student_number}, email: {user.email}")
        return db_user
    else:
        existing_user = db.query(models.User).filter(models.User.student_number == user.student_number).first()
        logging.info(f"User with student_number: {user.student_number} already exists.")
        return existing_user


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
        created_at=date.today(),  # Corrected: Use date.today()
        updated_at=date.today(),  # Corrected: Use date.today()
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
    db: Session, payment_id: int, paymaya_payment_id: str = None, status: str = None
):
    """Updates a payment record's PayMaya ID and/or status."""
    db_payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if db_payment:
        if paymaya_payment_id is not None:
            db_payment.paymaya_payment_id = paymaya_payment_id
        if status is not None:
            db_payment.status = status
        db_payment.updated_at = datetime.utcnow()  # Corrected import # This is correct, it should be a datetime
        db.commit()
        db.refresh(db_payment)
        logging.info(
            f"Updated payment with id: {payment_id}, paymaya_payment_id: {paymaya_payment_id}, status: {status}"
        )
        return db_payment
    else:
        logging.warning(f"Payment with id: {payment_id} not found for update.")
        return None


def add_payment_item(
    db: Session, academic_year: str, semester: str, fee: float, user_id: int, due_date: Optional[date] = None
):
    db_payment_item = models.PaymentItem(
        academic_year=academic_year,
        semester=semester,
        fee=fee,
        user_id=user_id,
        due_date=due_date,  # Save the date object
        created_at=date.today(), # corrected
        updated_at=date.today(), # corrected
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
        # Instead of db.refresh(), re-fetch and extract the date
        db_payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
        if db_payment_item:  # check if the item was really found.
            db_payment_item.created_at = db_payment_item.created_at  # no need to change this, but keep it for consistency
            db_payment_item.updated_at = db_payment_item.updated_at
        logging.info(f"Payment item with id: {payment_item_id} marked as paid.")
        return db_payment_item
    else:
        logging.warning(f"Payment item with id: {payment_item_id} not found for marking as paid.")
        return None