from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext

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
    return db_user


def authenticate_user(db: Session, identifier: str, password: str) -> models.User | None:
    """
    Authenticates a user (student or admin) based on student number or email.
    """
    user = get_user(db, identifier)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user



def authenticate_admin_by_email(db: Session, email: str, password: str) -> models.Admin | None:
    """
    Authenticates an admin user by email.
    """
    admin = db.query(models.Admin).filter(models.Admin.email == email).first()
    if not admin:
        return None
    if not pwd_context.verify(password, admin.password):
        return None
    return admin