from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from . import models, schemas, crud
from .database import SessionLocal, engine
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from io import BytesIO  # Import BytesIO
from PIL import Image  # Import PIL for image processing
import os
import secrets

from starlette.middleware.sessions import SessionMiddleware

# Import the necessary functions from text.py
from .text import extract_text_from_pdf, extract_student_info, is_valid_school_year, is_within_valid_school_year

# Initialize the database
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Add SessionMiddleware.  You MUST replace "your_secret_key" with a real secret key.
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

# Calculate paths relative to this file
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "frontend" / "static"),
    name="static"
)

# Setup templates
templates = Jinja2Templates(directory=BASE_DIR / "frontend" / "templates")


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Function to generate a secure random filename
def generate_secure_filename(original_filename: str) -> str:
    """Generates a secure, unique filename."""
    _, file_extension = os.path.splitext(original_filename)
    random_prefix = secrets.token_hex(16)  # 32 character hex string
    return f"{random_prefix}{file_extension}"


# Endpoint for logout
@app.get("/logout", response_class=RedirectResponse, name="logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


# Endpoint for root
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Endpoint for home
@app.get("/home", response_class=HTMLResponse, name="home")
async def home(request: Request, db: Session = Depends(get_db)):
    latest_bulletin_posts = db.query(models.BulletinBoard).order_by(models.BulletinBoard.created_at.desc()).limit(5).all()
    temporary_faqs = [
        {"question": "What is the schedule for student orientation?",
         "answer": "The student orientation will be held on August 20, 2025, from 9:00 AM to 12:00 PM in the main auditorium."},
        {"question": "How do I access the online learning platform?",
         "answer": "You can access the online learning platform by visiting our website and clicking on the 'Student Portal' link. Use your student ID and password to log in."},
        {"question": "Who should I contact for academic advising?",
         "answer": "For academic advising, please contact the Dean's office of your respective faculty. You can find their contact information on the university website under the 'Academics' section."},
    ]
    return templates.TemplateResponse("student_dashboard/home.html",
                                      {"request": request, "year": "2025", "bulletin_posts": latest_bulletin_posts,
                                       "faqs": temporary_faqs})


# Endpoint for bulletin board
@app.get("/BulletinBoard", response_class=HTMLResponse, name="bulletin_board")
async def bulletin_board(request: Request, db: Session = Depends(get_db)):
    posts = db.query(models.BulletinBoard).order_by(models.BulletinBoard.created_at.desc()).all()
    hearted_posts = []
    return templates.TemplateResponse(
        "student_dashboard/bulletin_board.html",
        {"request": request, "year": "2025", "posts": posts, "hearted_posts": hearted_posts}
    )


# Endpoint for events
@app.get("/Events", response_class=HTMLResponse, name="events")
async def events(request: Request, db: Session = Depends(get_db)):
    events_list = db.query(models.Event).options(joinedload(models.Event.participants)).order_by(models.Event.date).all()
    # current_user_id = 1 # Removed hardcoded user ID
    current_user_id = request.session.get("user_id")  # Get user ID from session
    if not current_user_id:
        current_user_id = 0  # set to 0 or handle unauthenticated user as you prefer
    for event in events_list:
        event.participant_ids = [user.id for user in event.participants]
    return templates.TemplateResponse(
        "student_dashboard/events.html",
        {"request": request, "year": "2025", "events": events_list, "current_user_id": current_user_id}
    )


# Endpoint for payments
@app.get("/Payments", response_class=HTMLResponse, name="payments")
async def payments(request: Request):
    return templates.TemplateResponse("student_dashboard/payments.html", {"request": request, "year": "2025"})


# Endpoint for financial statement
@app.get("/FinancialStatement", response_class=HTMLResponse, name="financial_statement")
async def financial_statement(request: Request):
    return templates.TemplateResponse("student_dashboard/financial_statement.html", {"request": request, "year": "2025"})


# Endpoint for settings
@app.get("/Settings", response_class=HTMLResponse, name="settings")
async def settings(request: Request, db: Session = Depends(get_db)):
    # Get the current user's data to pre-populate the form
    current_user_id = request.session.get("user_id")  # Get user ID from session
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = db.query(models.User).filter(models.User.id == current_user_id).first()  # changed from student_number to id
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse("student_dashboard/settings.html",
                                      {"request": request, "year": "2025", "user": user})  # Pass the user object to the template


# Endpoint for signup
@app.post("/api/signup/")
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, student_number=user.student_number)
    if db_user:
        raise HTTPException(status_code=400, detail="Student number already registered")

    db_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = crud.create_user(db=db, user=user)
    return {"message": "User created successfully", "user_id": new_user.id}  # Return the new user's ID


# Endpoint for login
@app.post("/api/login/")
async def login(form_data: schemas.UserLogin, request: Request, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.student_number, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect student number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.session["user_id"] = user.id  # Store the user ID in the session
    return {"message": "Login successful"}


# Endpoint for hearting a post
@app.post("/bulletin/heart/{post_id}")
async def heart_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    action = form_data.get('action')
    user_id = 1  # Removed hardcoded user ID
    user_id = request.session.get("user_id")  # Get user ID from session
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    post = db.query(models.BulletinBoard).filter(models.BulletinBoard.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if action == 'heart':
        post.heart_count += 1
    elif action == 'unheart' and post.heart_count > 0:
        post.heart_count -= 1

    db.commit()
    db.refresh(post)
    return {"heart_count": post.heart_count}


# Endpoint for joining an event
@app.post("/Events/join/{event_id}")
async def join_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    # current_user_id = 1 # Removed hardcoded user ID
    current_user_id = request.session.get("user_id")  # Get user ID from session
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    event = db.query(models.Event).options(joinedload(models.Event.participants)).filter(
        models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    user = db.query(models.User).filter(models.User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user in event.participants:
        raise HTTPException(status_code=400, detail="You are already joined in this event.")

    if event.joined_count() >= event.max_participants:
        raise HTTPException(status_code=400, detail="This event is full.")

    event.participants.append(user)
    db.commit()
    return RedirectResponse(url="/Events", status_code=status.HTTP_303_SEE_OTHER)


# Endpoint for leaving an event
@app.post("/Events/leave/{event_id}")
async def leave_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    # current_user_id = 1 # Removed hardcoded user ID
    current_user_id = request.session.get("user_id")  # Get user ID from session
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    event = db.query(models.Event).options(joinedload(models.Event.participants)).filter(
        models.Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    user = db.query(models.User).filter(models.User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user not in event.participants:
        raise HTTPException(status_code=400, detail="You are not joined in this event.")

    event.participants.remove(user)
    db.commit()
    return RedirectResponse(url="/Events", status_code=status.HTTP_303_SEE_OTHER)


# Endpoint for upcoming events summary
@app.get("/api/events/upcoming_summary")
async def get_upcoming_events_summary(db: Session = Depends(get_db)):
    now = datetime.now()
    upcoming_events = db.query(models.Event).filter(models.Event.date >= now).order_by(
        models.Event.date).limit(5).all()
    return [{"title": event.title, "date": event.date.isoformat(), "location": event.location,
             "classification": event.classification} for event in upcoming_events]


# New endpoint to handle PDF upload and student verification
@app.post("/api/verify_student/")
async def verify_student(
    request: Request,  # Add the request parameter
    student_number: str = Form(...),  # Get student number from form data
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Verifies a student's information by extracting data from a PDF,
    validating it, and updating the user's record in the database.
    """
    # 1.  Basic file validation (check content type and size)
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type.  Only PDF files are allowed.")

    # Optional: Size limit (e.g., 500KB) -  Good practice to limit file size.
    max_file_size_bytes = 500 * 1024  # 500KB
    file_content = await file.read()  # Read the file content
    if len(file_content) > max_file_size_bytes:
        raise HTTPException(status_code=413,
                            detail=f"File size too large. Maximum allowed size is {max_file_size_bytes} bytes.")

    # 2. Extract text from the PDF
    extracted_text = extract_text_from_pdf(BytesIO(file_content))  # Pass file content as BytesIO
    if not extracted_text:
        raise HTTPException(status_code=400,
                            detail="Could not extract text from PDF.  The PDF might be corrupted or empty.")

    # 3. Extract student information from the text
    student_info = extract_student_info(extracted_text)
    if not student_info:
        raise HTTPException(status_code=400,
                            detail="Could not extract student information from the PDF content.")

    # 4. Validate the extracted school year
    extracted_school_year = student_info.get('school_year')  # Safely get school year
    if not extracted_school_year or not is_valid_school_year(extracted_school_year):
        raise HTTPException(
            status_code=400,
            detail="Invalid school year format in the PDF.  Expected format is-YYYY (e.g., 2024-2025).",
        )

    if not is_within_valid_school_year(extracted_school_year):
        raise HTTPException(
            status_code=400,
            detail="The school year in the PDF is not the current or previous school year.",
        )
    # 5.  Get the user from the database
    user = crud.get_user(db, student_number=student_number)
    if not user:
        raise HTTPException(status_code=404, detail="Student not found.")

    # 6. Check if the user is already verified
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Student is already verified.")

    # 7. Update user information with extracted data
    #   Only update fields that were successfully extracted.
    if 'name' in student_info and student_info['name']:
        user.name = student_info['name']
    if 'campus' in student_info and student_info['campus']:
        user.campus = student_info['campus']
    if 'semester' in student_info and student_info['semester']:
        user.semester = student_info['semester']
    if 'course' in student_info and student_info['course']:
        user.course = student_info['course']
    if 'school_year' in student_info and student_info['school_year']:
        user.school_year = student_info['school_year']
    if 'year_level' in student_info and student_info['year_level']:
        user.year_level = student_info['year_level']
    if 'section' in student_info and student_info['section']:
        user.section = student_info['section']
    if 'address' in student_info and student_info['address']:
        user.address = student_info['address']

    # 8. Mark the user as verified
    user.is_verified = True
    user.verified_by = "Admin"  # Set the verified_by field
    user.verification_date = datetime.now()  # set the date

    db.commit()
    db.refresh(user)

    return {"message": "Student information verified successfully", "user": user}


# Endpoint to update user profile information
@app.post("/api/profile/update/")
async def update_profile(
    request: Request,
    name: Optional[str] = Form(None),
    campus: Optional[str] = Form(None),
    semester: Optional[str] = Form(None),
    course: Optional[str] = Form(None),
    school_year: Optional[str] = Form(None),
    year_level: Optional[str] = Form(None),
    section: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    birthdate: Optional[datetime] = Form(None),
    sex: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    guardian_name: Optional[str] = Form(None),
    guardian_contact: Optional[str] = Form(None),
    registration_form: Optional[str] = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Updates the user's profile information, including handling the profile picture upload.
    """
    # 1.  Get the user from the database.
    # current_user_id = 1 # Replace with actual user identification logic
    current_user_id = request.session.get("user_id")  # Get user ID from session
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = crud.get_user(db, student_number=current_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Update the user object with the provided data
    if name is not None:
        user.name = name
    if campus is not None:
        user.campus = campus
    if semester is not None:
        user.semester = semester
    if course is not None:
        user.course = course
    if school_year is not None:
        user.school_year = school_year
    if year_level is not None:
        user.year_level = year_level
    if section is not None:
        user.section = section
    if address is not None:
        user.address = address
    if birthdate is not None:
        user.birthdate = birthdate
    if sex is not None:
        user.sex = sex
    if contact is not None:
        user.contact = contact
    if guardian_name is not None:
        user.guardian_name = guardian_name
    if guardian_contact is not None:
        user.guardian_contact = guardian_contact
    if registration_form is not None:
        user.registration_form = registration_form

    # 3. Handle profile picture upload
    if profile_picture:
        # Validate image file type
        if not profile_picture.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail="Invalid file type. Only images are allowed."
            )

        #  Check image file size (optional)
        max_image_size_bytes = 2 * 1024 * 1024  # 2MB
        image_content = await profile_picture.read()
        if len(image_content) > max_image_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Image size too large. Maximum allowed size is {max_image_size_bytes} bytes.",
            )
        try:
            # Use PIL to open and validate the image
            img = Image.open(BytesIO(image_content))
            img.verify()  # Check if it's a valid image
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

        # Generate a secure filename
        filename = generate_secure_filename(profile_picture.filename)
        # Construct the full file path
        file_path = os.path.join("frontend", "static", "images", "profile_pictures",
                                 filename)  # Save in profile_pictures directory

        # Save the image file
        with open(file_path, "wb") as f:
            f.write(image_content)
        user.profile_picture = f"/static/images/profile_pictures/{filename}"  # Store the relative path in the database

    # 4. Commit the changes to the database
    db.commit()
    db.refresh(user)  # Refresh the user object to get the updated values

    # 5. Return the updated user data
    return {"message": "Profile updated successfully", "user": user}
