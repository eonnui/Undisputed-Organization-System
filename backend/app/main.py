from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from . import models, schemas, crud
from .database import SessionLocal, engine
from pathlib import Path

# Initialize the database
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

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

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/Home", response_class=HTMLResponse, name="home")
async def home(request: Request):
    return templates.TemplateResponse("student_dashboard/home.html", {"request": request, "year": "2025"})

@app.get("/BulletinBoard", response_class=HTMLResponse, name="bulletin_board")
async def bulletin_board(request: Request):
    return templates.TemplateResponse("student_dashboard/bulletin_board.html", {"request": request, "year": "2025"})

@app.get("/Events", response_class=HTMLResponse, name="events")
async def events(request: Request):
    return templates.TemplateResponse("student_dashboard/events.html", {"request": request, "year": "2025"})

@app.get("/Payments", response_class=HTMLResponse, name="payments")
async def payments(request: Request):
    return templates.TemplateResponse("student_dashboard/payments.html", {"request": request, "year": "2025"})

@app.get("/FinancialStatement", response_class=HTMLResponse, name="financial_statement")
async def financial_statement(request: Request):
    return templates.TemplateResponse("student_dashboard/financial_statement.html", {"request": request, "year": "2025"})

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
    return {"message": "Login successful"}