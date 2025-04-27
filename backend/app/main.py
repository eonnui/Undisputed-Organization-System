# main.py
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from . import models, schemas, crud
from .database import SessionLocal, engine
from pathlib import Path
from datetime import datetime

# Import SessionMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Initialize the database
models.Base.metadata.create_all(bind=engine) # Make sure this is called only once

app = FastAPI()

# Add SessionMiddleware.  You MUST replace "your_secret_key" with a real secret key.
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

# Calculate paths relative to this file
# Get the base directory of your project
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Goes up two levels from current file

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

@app.get("/logout", response_class=RedirectResponse, name="logout")
async def logout(request: Request):
    # Invalidate the user's session (example using request.session)
    request.session.clear()
    # Or, if you're using a different session management mechanism,
    # implement the appropriate logic here to clear the session.

    # Optionally, you can set a success message or perform other actions.

    # Redirect the user to the login page (your root "/")
    return RedirectResponse(url="/", status_code=303)  # Use 303 for POST redirect after GET

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/home", response_class=HTMLResponse, name="home")
async def home(request: Request, db: Session = Depends(get_db)):
    latest_bulletin_posts = db.query(models.BulletinBoard).order_by(models.BulletinBoard.created_at.desc()).limit(5).all()
    temporary_faqs = [
        {"question": "What is the schedule for student orientation?", "answer": "The student orientation will be held on August 20, 2025, from 9:00 AM to 12:00 PM in the main auditorium."},
        {"question": "How do I access the online learning platform?", "answer": "You can access the online learning platform by visiting our website and clicking on the 'Student Portal' link. Use your student ID and password to log in."},
        {"question": "Who should I contact for academic advising?", "answer": "For academic advising, please contact the Dean's office of your respective faculty. You can find their contact information on the university website under the 'Academics' section."},
    ]
    return templates.TemplateResponse("student_dashboard/home.html", {"request": request, "year": "2025", "bulletin_posts": latest_bulletin_posts, "faqs": temporary_faqs})

@app.get("/BulletinBoard", response_class=HTMLResponse, name="bulletin_board")
async def bulletin_board(request: Request, db: Session = Depends(get_db)):
    posts = db.query(models.BulletinBoard).order_by(models.BulletinBoard.created_at.desc()).all()
    # Assuming you have a way to get the current user's ID
    # For now, we'll just pass an empty list for hearted posts
    hearted_posts = []
    return templates.TemplateResponse(
        "student_dashboard/bulletin_board.html",
        {"request": request, "year": "2025", "posts": posts, "hearted_posts": hearted_posts}
    )

@app.get("/Events", response_class=HTMLResponse, name="events")
async def events(request: Request, db: Session = Depends(get_db)):
    events_list = db.query(models.Event).options(joinedload(models.Event.participants)).order_by(models.Event.date).all()
    # Assuming you have a way to get the current user's ID
    current_user_id = 1  # Replace with actual user identification logic
    for event in events_list:
        event.participant_ids = [user.id for user in event.participants]
    return templates.TemplateResponse(
        "student_dashboard/events.html",
        {"request": request, "year": "2025", "events": events_list, "current_user_id": current_user_id}
    )

@app.get("/Payments", response_class=HTMLResponse, name="payments")
async def payments(request: Request):
    return templates.TemplateResponse("student_dashboard/payments.html", {"request": request, "year": "2025"})

@app.get("/FinancialStatement", response_class=HTMLResponse, name="financial_statement")
async def financial_statement(request: Request):
    return templates.TemplateResponse("student_dashboard/financial_statement.html", {"request": request, "year": "2025"})

@app.get("/Settings", response_class=HTMLResponse, name="settings")
async def settings(request: Request):
    return templates.TemplateResponse("student_dashboard/settings.html", {"request": request, "year": "2025"})

@app.post("/api/signup/")
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, student_number=user.student_number)
    if db_user:
        raise HTTPException(status_code=400, detail="Student number already registered")
    
    db_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return crud.create_user(db=db, user=user)

@app.post("/api/login/")
async def login(form_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.student_number, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect student number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    #  Normally you would create a session here.  Since we don't have a full session management
    #  system in this example, we'll just return a success message.  In a real app,
    #  you'd set a cookie or JWT here.
    # In a real application, you would set a session here, e.g.,:
    # request.session["user_id"] = user.id
    return {"message": "Login successful"}

@app.post("/bulletin/heart/{post_id}")
async def heart_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    action = form_data.get('action')
    # Assuming you have a way to identify the current user (e.g., from session)
    user_id = 1  # Replace with actual user identification logic

    post = db.query(models.BulletinBoard).filter(models.BulletinBoard.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if action == 'heart':
        post.heart_count += 1
        # In a real application, you would likely record that the user has hearted this post
        # in a separate table to prevent multiple hearts from the same user.
    elif action == 'unheart' and post.heart_count > 0:
        post.heart_count -= 1
        # Similarly, you would update the record of the user's interaction.

    db.commit()
    db.refresh(post)
    return {"heart_count": post.heart_count}

@app.post("/Events/join/{event_id}")
async def join_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    # Assuming you have a way to identify the current user
    current_user_id = 1  # Replace with actual user identification logic

    event = db.query(models.Event).options(joinedload(models.Event.participants)).filter(models.Event.event_id == event_id).first()
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

@app.post("/Events/leave/{event_id}")
async def leave_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    # Assuming you have a way to identify the current user
    current_user_id = 1  # Replace with actual user identification logic

    event = db.query(models.Event).options(joinedload(models.Event.participants)).filter(models.Event.event_id == event_id).first()
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

@app.get("/api/events/upcoming_summary")
async def get_upcoming_events_summary(db: Session = Depends(get_db)):
    now = datetime.now()
    upcoming_events = db.query(models.Event).filter(models.Event.date >= now).order_by(models.Event.date).limit(5).all()  # Adjust limit as needed
    return [{"title": event.title, "date": event.date.isoformat(), "location": event.location, "classification": event.classification} for event in upcoming_events]