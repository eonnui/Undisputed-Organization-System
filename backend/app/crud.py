from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user(db: Session, student_number: str):
    return db.query(models.User).filter(models.User.student_number == student_number).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(
        student_number=user.student_number,
        email=user.email,
        organization=user.organization,
        first_name=user.first_name,
        last_name=user.last_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, student_number: str, password: str):
    user = get_user(db, student_number)
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user