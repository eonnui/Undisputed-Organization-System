from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Form, APIRouter, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
import re
import requests
import base64
import logging

from starlette.middleware.sessions import SessionMiddleware

# Import the necessary functions from text.py
from .text import extract_text_from_pdf, extract_student_info

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
router = APIRouter()
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
    """
    Handles the submission of new bulletin board posts by admins.
    """
    print("Received post request!")
    print(f"Title: {title}")
    print(f"Content: {content}")
    print(f"Category: {category}")
    print(f"Is Pinned: {is_pinned}")
    print(f"Image: {image}")
    print(f"Session Admin ID: {request.session.get('admin_id')}")
    try:
        admin_id = request.session.get("admin_id")
        if not admin_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated as admin",
            )

        admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin user not found",
            )

        image_path = None
        if image and image.filename:  # Check if an image was actually uploaded
            if image.content_type.startswith("image/"):
                try:
                    filename = generate_secure_filename(image.filename)
                    file_path = os.path.join(
                        "..", "frontend", "static", "images", "bulletin_board", filename
                    )
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "wb") as f:
                        f.write(await image.read())
                    image_path = f"/static/images/bulletin_board/{filename}"
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to save image: {e}",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image file type",
                )

        db_post = models.BulletinBoard(
            title=title,
            content=content,
            category=category,
            is_pinned=is_pinned,
            admin_id=admin_id,
            image_path=image_path,
        )
        db.add(db_post)
        db.commit()
        db.refresh(db_post)

        return RedirectResponse(url="/admin/bulletin_board",
                                    status_code=status.HTTP_303_SEE_OTHER)  # Changed redirect

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error processing post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during post creation",
        )

@router.get("/admin_settings/", response_class=HTMLResponse, name="admin_settings") # Added a trailing slash
async def admin_settings(request: Request, db: Session = Depends(get_db)):
    """Displays the admin settings, including payment settings."""

    # --- Placeholder Authentication and Authorization ---
    current_user_id: Optional[int] = request.session.get("user_id") or request.session.get("admin_id")
    user_role: Optional[str] = request.session.get("user_role")

    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if user_role != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions. Admin access required.")

     

    return templates.TemplateResponse(
        "admin_dashboard/admin_settings.html",
        {
            "request": request,
            "year": "2025",  # Keep this, assuming it's a global constant           
        },
    )

@router.post("/admin/events/create", name="admin_create_event") # Removed HTMLResponse
async def admin_create_event(
    request: Request,
    title: str = Form(...),
    classification: str = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    location: str = Form(...),
    max_participants: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handles the creation of new events by admins.  Redirects to events list after.
    """
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated as admin",
        )

    admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found",
        )

    try:
        event_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Please use %Y-%m-%d.",
        )

    db_event = models.Event(
        title=title,
        classification=classification,
        description=description,
        date=event_date,
        location=location,
        admin_id=admin_id,
        max_participants=max_participants,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Redirect to the events list page after successful creation
    return RedirectResponse(url="/admin/events", status_code=status.HTTP_303_SEE_OTHER) #changed


# Route to handle event deletion
@router.post("/admin/events/delete/{event_id}", response_class=HTMLResponse, name="admin_delete_event")
async def admin_delete_event(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Handles the deletion of events by admins.
    """
    print(f"Deleting event with ID: {event_id}")
    try:
        event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        print(f"Event found: {event}")
        db.delete(event)
        db.commit()
        print("Event deleted from database")
    except Exception as e:
        db.rollback()
        print(f"Error deleting event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    finally:
        db.close()
    # Redirect back to the events list page after successful deletion
    return RedirectResponse(url="/admin/events", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/bulletin_board/delete/{post_id}", response_class=HTMLResponse, name="admin_delete_bulletin_post")
async def admin_delete_bulletin_post(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db),
):
    """
    Handles the deletion of bulletin board posts by admins.
    """
    print(f"Deleting bulletin board post with ID: {post_id}")
    try:
        # Correct the attribute name here to .post_id
        post = db.query(models.BulletinBoard).filter(models.BulletinBoard.post_id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )
        print(f"Post found: {post}")
        db.delete(post)
        db.commit()
        print("Post deleted from database")
    except Exception as e:
        db.rollback()
        print(f"Error deleting post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    finally:
        db.close()
    # Redirect back to the bulletin board page after successful deletion
    return RedirectResponse(url="/admin/bulletin_board", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/admin/payments", name="admin_add_payment_item")
async def admin_add_payment_item(
    request: Request,
    user_id: int = Form(...),
    academic_year: str = Form(...),
    semester: str = Form(...),
    fee: float = Form(...),
    due_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Handles the form submission for adding a new payment item."""
    current_user_id: Optional[int] = request.session.get("user_id") or request.session.get("admin_id")
    user_role: Optional[str] = request.session.get("user_role")

    if not current_user_id or user_role != "Admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated or insufficient permissions")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with ID {user_id} not found.")

    due_date_obj = None
    if due_date:
        try:
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()  # Parse as date
            logging.info(f"Parsed due_date: {due_date_obj}")
        except ValueError as e:
            logging.error(f"Error parsing due date: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid due date format (YYYY-MM-DD).")

    logging.info(f"Adding new payment item for user_id: {user_id}, academic_year: {academic_year}, semester: {semester}, fee: {fee}, due_date: {due_date_obj}")
    new_payment_item = crud.add_payment_item(db, academic_year=academic_year, semester=semester, fee=fee, user_id=user_id, due_date=due_date_obj)
    logging.info(f"New payment item successfully added: {new_payment_item}")
    logging.info(f"New payment item created: {new_payment_item}")

    return RedirectResponse(router.url_path_for("admin_payments"), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/Admin/payments", response_class=HTMLResponse, name="admin_payments")
async def admin_payments(request: Request, db: Session = Depends(get_db)):
    current_user_id: Optional[int] = request.session.get("user_id") or request.session.get("admin_id")
    user_role: Optional[str] = request.session.get("user_role")

    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if user_role != "Admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions. Admin access required.")

    payment_items = crud.get_all_payment_items(db)  # Fetch only unpaid payment items

    return templates.TemplateResponse(
        "admin_dashboard/admin_payments.html",
        {"request": request, "year": "2025", "payment_items": payment_items},
    )

@router.get("/admin/payments/total_members", response_class=HTMLResponse, name="payments_total_members")
async def payments_total_members(request: Request, db: Session = Depends(get_db)):
    year = 2025  # Or however you determine the year
    users = db.query(models.User).all()  # Fetch all users from the database
    return templates.TemplateResponse(
        "admin_dashboard/payments/total_members.html",
        {"request": request, "year": year, "members": users},
    )

@router.get('/admin/bulletin_board', response_class=HTMLResponse)
def admin_bulletin_board(request: Request, db: Session = Depends(get_db)):
    """
    Displays the admin bulletin board page with recent posts.
    """
    posts: List[models.BulletinBoard] = db.query(models.BulletinBoard).order_by(
        models.BulletinBoard.created_at.desc()).all()
    return templates.TemplateResponse("admin_dashboard/admin_bulletin_board.html", {"request": request, "posts": posts})

@router.get("/admin/events", response_class=HTMLResponse, name="admin_events")
async def admin_events(request: Request, db: Session = Depends(get_db)):
    """
    Displays the list of events to the admin.
    """
    admin_id = request.session.get("admin_id")  # Get admin ID from the session
    if not admin_id:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found"
        )

    events = db.query(models.Event).all()  # Fetch ALL events from the database
    return templates.TemplateResponse(
        "admin_dashboard/admin_events.html", {"request": request, "events": events}  # Pass the events to the template
    )

@router.get("/admin/financial_statement", response_class=HTMLResponse, name="admin_financial_statement")
async def admin_financial_statement(request: Request):
    return templates.TemplateResponse("admin_dashboard/admin_financial_statement.html", {"request": request, "year": "2025"})

# ---------------------- PayMaya Sandbox Integration ----------------------
@router.post("/payments/paymaya/create", response_class=JSONResponse, name="paymaya_create_payment")
async def paymaya_create_payment(
    request: Request,
    payment_item_id: int = Form(...),  # Expect payment_item_id from the form
    db: Session = Depends(get_db),
):
    """
    Creates a PayMaya payment request. Handles cases where the amount is
    provided directly or needs to be retrieved from a payment item.
    """
    public_api_key = "pk-rpwb5YR6EfnKiMsldZqY4hgpvJjuy8hhxW2bVAAiz2N"
    encoded_key = base64.b64encode(f"{public_api_key}:".encode()).decode()
    url = "https://pg-sandbox.paymaya.com/payby/v2/paymaya/payments"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Basic {encoded_key}"
    }

    # Get the user ID from the session.  This is crucial.
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated")

    # 2. Fetch the payment item from the database.
    payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if not payment_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment item not found")

    payment_amount = payment_item.fee  # Use the fee from the payment item.

    # Create a pending payment record in your database
    db_payment = crud.create_payment(db, amount=payment_amount, user_id=user_id)  # Pass the user_id here

    payload = {
        "totalAmount": {
            "currency": "PHP",
            "value": payment_amount
        },
        "requestReferenceNumber": f"your-unique-ref-{datetime.now().strftime('%Y%m%d%H%M%S')}-{db_payment.id}",  # Include your DB payment ID for easier tracking
        "redirectUrl": {
            "success": f"http://127.0.0.1:8000/Success?paymentId={db_payment.id}&paymentItemId={payment_item_id}",  # Pass your DB payment ID AND payment_item_id
            "failure": f"http://127.0.0.1:8000/Failure?paymentId={db_payment.id}&paymentItemId={payment_item_id}",  # Pass your DB payment ID AND payment_item_id
            "cancel": f"http://127.0.0.1:8000/Cancel?paymentId={db_payment.id}&paymentItemId={payment_item_id}"  # Pass your DB payment ID AND payment_item_id
        },
        "metadata": {
            "pf": {
                "smi": "CVSU",
                "smn": "Undisputed",
                "mci": "Imus City",
                "mpc": "608",
                "mco": "PHL",
                "postalCode": "1554",
                "contactNo": "0211111111",
                "addressLine1": "Palico",
            },
            "subMerchantRequestReferenceNumber": "63d9934f9281"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        payment_data = response.json()
        paymaya_payment_id = payment_data.get("paymentId")

        # Update your database record with the PayMaya payment ID
        crud.update_payment(db, payment_id=db_payment.id, paymaya_payment_id=paymaya_payment_id)

        print(f"Generated PayMaya payment ID: {paymaya_payment_id}, Our payment ID: {db_payment.id}")
        return payment_data

    except requests.exceptions.RequestException as e:
        logging.error(f"PayMaya API error: {e.response.text if hasattr(e.response, 'text') else str(e)}")
        crud.update_payment(db, payment_id=db_payment.id, status="failed")  # Update status in case of error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PayMaya API error: {e.response.text if hasattr(e.response, 'text') else str(e)}"
        )
    
@router.get("/Success", response_class=HTMLResponse, name="payment_success")
async def payment_success(
    request: Request,
    paymentId: int = Query(...),
    paymentItemId: int = Query(...),  # Extract paymentItemId from query
    db: Session = Depends(get_db),
):
    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

    crud.update_payment(db, payment_id=payment.id, status="success")

    # Mark the associated PaymentItem as paid
    payment_item = crud.get_payment_item_by_id(db, payment_item_id=paymentItemId)
    if payment_item:
        logging.info(f"Attempting to mark payment item {paymentItemId} as paid.")
        updated_item = crud.mark_payment_item_as_paid(db, payment_item_id=paymentItemId)
        return templates.TemplateResponse(
            "student_dashboard/payment_success.html",
            {"request": request, "payment_id": payment.paymaya_payment_id, "payment_item_id": paymentItemId, "updated": updated_item}
        )
    else:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PaymentItem with ID {paymentItemId} not found."
        )
    
@router.get("/Failure", response_class=HTMLResponse, name="payment_failure")
async def payment_failure(request: Request, paymentId: int, db: Session = Depends(get_db)):
    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if payment:
        crud.update_payment(db, payment_id=payment.id, status="failed")
        return templates.TemplateResponse("student_dashboard/payment_failure.html", {"request": request, "payment_id": payment.paymaya_payment_id})
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

@router.get("/Cancel", response_class=HTMLResponse, name="payment_cancel")
async def payment_cancel(request: Request, paymentId: int, db: Session = Depends(get_db)):
    payment = crud.get_payment_by_id(db, payment_id=paymentId)
    if payment:
        crud.update_payment(db, payment_id=payment.id, status="cancelled")
        return templates.TemplateResponse("student_dashboard/payment_cancel.html", {"request": request, "payment_id": payment.paymaya_payment_id})
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")
    
# ---------------------- End of PayMaya Sandbox Integration ----------------------

# Include the router in your main application
app.include_router(router)


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
async def home(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handles the /home route, displaying either the student or admin dashboard
    depending on the user's role stored in the session.
    """
    user_id = request.session.get("user_id") or request.session.get("admin_id") # changed
    user_role = request.session.get("user_role")

    if not user_id or not user_role:
        #  Redirect to login if the user is not logged in.
        return templates.TemplateResponse("index.html", {"request": request, "error": "Please log in to access this page."}) #adjust to your login template
    if user_role == "Admin":
        # Logic for admin dashboard
        # Fetch data needed for admin dashboard
        latest_bulletin_posts = (
            db.query(models.BulletinBoard)
            .order_by(models.BulletinBoard.created_at.desc())
            .limit(5)
            .all()
        )
        # You might have different templates for admin and student
        return templates.TemplateResponse(
            "admin_dashboard/home.html",  #  Admin template
            {
                "request": request,
                "year": "2025",
                "bulletin_posts": latest_bulletin_posts,
            },
        )
    elif user_role == "user":
        # Logic for student dashboard
        latest_bulletin_posts = (
            db.query(models.BulletinBoard)
            .order_by(models.BulletinBoard.created_at.desc())
            .limit(5)
            .all()
        )
        temporary_faqs = [
            {
                "question": "What is the schedule for student orientation?",
                "answer": "The student orientation will be held on August 20, 2025, from 9:00 AM to 12:00 PM in the main auditorium.",
            },
            {
                "question": "How do I access the online learning platform?",
                "answer": "You can access the online learning platform by visiting our website and clicking on the 'Student Portal' link. Use your student ID and password to log in.",
            },
            {
                "question": "Who should I contact for academic advising?",
                "answer": "For academic advising, please contact the Dean's office of your respective faculty. You can find their contact information on the university website under the 'Academics' section.",
            },
        ]
        return templates.TemplateResponse(
            "student_dashboard/home.html",  #  Student template
            {
                "request": request,
                "year": "2025",
                "bulletin_posts": latest_bulletin_posts,
                "faqs": temporary_faqs,
            },
        )
    else:
        # Handle unexpected roles (optional, but good practice)
        raise HTTPException(status_code=403, detail="Invalid user role")




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
async def payments(request: Request, db: Session = Depends(get_db)):
    """
    Renders the payments page with data for a student, displaying only their unpaid payment items
    and including the due date.
    """
    logging.info("Entering /Payments route")
    user_identifier = request.session.get("user_id") or request.session.get("admin_id")
    logging.info(f"User identifier: {user_identifier}")
    current_user = None

    if not user_identifier:
        logging.warning("User not authenticated, redirecting to /")
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    current_user = db.query(models.User).filter(models.User.id == user_identifier).first()
    if not current_user:
        logging.error(f"User not found with identifier: {user_identifier}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    logging.info(f"Current user: {current_user}")

    try:
        # Fetch only unpaid payment items for the current user.
        payment_items = (
            db.query(models.PaymentItem)
            .filter(models.PaymentItem.user_id == user_identifier)
            .filter(models.PaymentItem.is_paid == False)
            .all()
        )
        logging.info(f"Unpaid payment items: {payment_items}")

        return templates.TemplateResponse(
            "student_dashboard/payments.html",
            {
                "request": request,
                "payment_items": payment_items,
                "current_user": current_user,
            },
        )
    except Exception as e:
        logging.exception(f"Error fetching unpaid payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve unpaid payment information.",
        )


# Endpoint for financial statement
@app.get("/FinancialStatement", response_class=HTMLResponse, name="financial_statement")
async def financial_statement(request: Request):
    return templates.TemplateResponse("student_dashboard/financial_statement.html", {"request": request, "year": "2025"})



@app.get("/Settings", response_class=HTMLResponse, name="settings")
async def settings(request: Request, db: Session = Depends(get_db)):
    """
    Renders the settings page, including the user's birthdate in the correct format.
    """
    # Get the current user's data to pre-populate the form
    current_user_id = request.session.get("user_id")
    if not current_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = db.query(models.User).filter(models.User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    formatted_birthdate = ""
    if user.birthdate:
        try:
            # Try converting from a common format (adjust if yours is different)
            birthdate_object = datetime.strptime(user.birthdate, "%Y-%m-%d %H:%M:%S")  # Handle "2025-05-23 00:00:00" format
            formatted_birthdate = birthdate_object.strftime("%Y-%m-%d")
        except ValueError:
            try:
                birthdate_object = datetime.strptime(user.birthdate, "%Y-%m-%d")
                formatted_birthdate = birthdate_object.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    birthdate_object = datetime.strptime(user.birthdate, "%m/%d/%Y")
                    formatted_birthdate = birthdate_object.strftime("%Y-%m-%d")
                except ValueError:
                    print(f"Warning: Could not parse birthdate string: {user.birthdate}")
                    formatted_birthdate = user.birthdate  # Use the original string as a fallback

    return templates.TemplateResponse(
        "student_dashboard/settings.html",
        {"request": request, "year": "2025", "user": user, "formatted_birthdate": formatted_birthdate},
    )

# Endpoint for signup
@app.post("/api/signup/")
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, identifier=user.student_number)
    if db_user:
        raise HTTPException(status_code=400, detail="Student number already registered")

    db_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # NEW: Check for existing first and last name combination
    db_name_combination = db.query(models.User).filter(
        models.User.first_name == user.first_name,
        models.User.last_name == user.last_name
    ).first()
    if db_name_combination:
        raise HTTPException(status_code=400, detail="First and last name combination already registered") #ADDED THIS

    new_user = crud.create_user(db=db, user=user)
    return {"message": "User created successfully", "user_id": new_user.id}

@app.get("/api/user/{user_id}", response_model=schemas.User)
async def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, identifier=str(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/get_user_data", response_model=schemas.User)
async def get_user_data(request: Request, db: Session = Depends(get_db)):
    print("get_user_data function called")
    try:
        user_identifier = request.session.get("user_id") or request.session.get("admin_id")
        print(f"User identifier from session: {user_identifier}, type: {type(user_identifier)}")
        if not user_identifier:
            raise HTTPException(status_code=401, detail="User not authenticated")

        user = db.query(models.User).filter(models.User.id == user_identifier).first()
        print(f"User data from db.query: {user}")
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    except Exception as e:
        print(f"Error in get_user_data: {e}")
        raise

# Endpoint for login
@app.post("/api/login/")
async def login(request: Request, form_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Login endpoint that handles both user and admin login.
    Admins log in using their email, and users with their student number.
    """
    print(f"Attempting login with identifier: {form_data.identifier}, password: {form_data.password}")

    user = crud.authenticate_user(db, form_data.identifier, form_data.password)
    print(f"Result from authenticate_user: {user}")

    if user:
        print("authenticate_user succeeded")
        request.session["user_id"] = user.id  # Changed to user_id
        request.session["user_role"] = getattr(user, 'role', 'user')
        print(f"User login successful. Session: {request.session}")
        return {
            "message": "User login successful",
            "user_id": user.id,
            "user_role": request.session["user_role"],
        }
    else:
        print("authenticate_user failed, trying admin authentication")
        admin = crud.authenticate_admin_by_email(db, form_data.identifier, form_data.password)
        print(f"Result from authenticate_admin_by_email: {admin}")
        if admin:
            request.session["admin_id"] = admin.admin_id  # Changed to admin_id
            request.session["user_role"] = admin.role
            print(f"Admin login successful. Session: {request.session}")
            return {
                "message": "Admin login successful",
                "admin_id": admin.admin_id,  # Changed to admin_id
                "user_role": admin.role,
            }
        else:
            print("Admin authentication failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )



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

def generate_email(first_name: str, last_name: str) -> str:
    """Generates the email address based on the provided format."""
    if first_name and last_name:
        return f"ic.{first_name.lower()}.{last_name.lower()}@cvsu.edu.ph"
    return None  # Or some default/error value

@app.post("/api/profile/update/")
async def update_profile(
    request: Request,
    student_number: Optional[str] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    birthdate: Optional[datetime] = Form(None),
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
    registration_form: Optional[UploadFile] = File(None),  # Change to UploadFile
    profilePicture: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Updates the user's profile information, including handling the registration form file upload
    and extracting data from it. It also deletes the previous registration form and profile picture
    if new ones are uploaded.
    """
    # 1.  Get the user from the database.
    current_user_id = request.session.get("user_id")
    print(f"Current user ID from session: {current_user_id}")
    if not current_user_id:
        print("Error: Not authenticated")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = db.query(models.User).filter(models.User.id == current_user_id).first()
    if not user:
        print(f"Error: User not found with ID: {current_user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    print(f"Found user: {user.name}")

    # Function to safely delete a file
    def delete_file(file_path: Optional[str]):
        if file_path:
            full_path = os.path.join("..", file_path.lstrip("/"))  # Construct full path
            print(f"Attempting to delete file: {full_path}")
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                    print(f"Successfully deleted file: {full_path}")
                except Exception as e:
                    print(f"Error deleting file {full_path}: {e}")
            else:
                print(f"File not found, cannot delete: {full_path}")

    # 2. Update the user object with the provided data
    if student_number is not None:
        user.student_number = student_number
        print(f"Updating student_number: {student_number}")
    if first_name is not None:
        user.first_name = first_name
        print(f"Updating first_name: {first_name}")
    if last_name is not None:
        user.last_name = last_name
        print(f"Updating last_name: {last_name}")
    if email is not None:
        user.email = email
        print(f"Updating email: {email}")
    if name is not None:
        user.name = name
        print(f"Updating name: {name}")
    if address is not None:
        user.address = address
        print(f"Updating address: {address}")
    if birthdate is not None:
        user.birthdate = birthdate
        print(f"Updating birthdate: {birthdate}")
    if sex is not None:
        user.sex = sex
        print(f"Updating sex: {sex}")
    if contact is not None:
        user.contact = contact
        print(f"Updating contact: {contact}")
    if course is not None:
        user.course = course
        print(f"Updating course: {course}")
    if semester is not None:
        user.semester = semester
        print(f"Updating semester: {semester}")
    if campus is not None:
        user.campus = campus
        print(f"Updating campus: {campus}")
    if school_year is not None:
        user.school_year = school_year
        print(f"Updating school_year: {school_year}")
    if year_level is not None:
        user.year_level = year_level
        print(f"Updating year_level: {year_level}")
    if section is not None:
        user.section = section
        print(f"Updating section: {section}")
    if guardian_name is not None:
        user.guardian_name = guardian_name
        print(f"Updating guardian_name: {guardian_name}")
    if guardian_contact is not None:
        user.guardian_contact = guardian_contact
        print(f"Updating guardian_contact: {guardian_contact}")

    # 3. Handle Registration Form upload and data extraction
    if registration_form:
        print(
            f"Handling registration form upload: {registration_form.filename}, content_type: {registration_form.content_type}"
        )
        # Validate file type (optional, but recommended)
        if registration_form.content_type != "application/pdf":
            print(
                f"Error: Invalid file type for registration form: {registration_form.content_type}. Only PDF is allowed."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type for registration form. Only PDF is allowed.",
            )

        try:
            # Delete the previous registration form if it exists
            print(f"Previous registration form path: {user.registration_form}")
            delete_file(user.registration_form)

            pdf_content = await registration_form.read()
            filename = generate_secure_filename(registration_form.filename)
            pdf_file_path = os.path.join(
                "..",
                "frontend",
                "static",
                "documents",  # Store in 'documents'
                "registration_forms",
                filename,
            )
            os.makedirs(os.path.dirname(pdf_file_path), exist_ok=True)
            with open(pdf_file_path, "wb") as f:
                f.write(pdf_content)
            user.registration_form = (
                f"/static/documents/registration_forms/{filename}"  # Store relative path
            )
            print(f"Registration form saved to: {user.registration_form}")

            # Extract text from the PDF
            extracted_text = extract_text_from_pdf(pdf_file_path)
            print(f"Extracted text from PDF: {extracted_text}")

            # Extract student information
            student_info = extract_student_info(extracted_text)
            print(f"Extracted student info: {student_info}")

            # Update user object with extracted information if not already provided in the form
            if name is None and "name" in student_info and student_info["name"]:
                user.name = student_info["name"]
                print(f"Updated name from PDF: {user.name}")
            if course is None and "course" in student_info and student_info["course"]:
                user.course = student_info["course"]
                print(f"Updated course from PDF: {user.course}")
            if year_level is None and "year_level" in student_info and student_info["year_level"]:
                user.year_level = student_info["year_level"]
                print(f"Updated year_level from PDF: {user.year_level}")
            if section is None and "section" in student_info and student_info["section"]:
                user.section = student_info["section"]
                print(f"Updated section from PDF: {user.section}")
            if campus is None and "campus" in student_info and student_info["campus"]:
                user.campus = student_info["campus"]
                print(f"Updated campus from PDF: {user.campus}")
            if semester is None and "semester" in student_info and student_info["semester"]:
                user.semester = student_info["semester"]
                print(f"Updated semester from PDF: {user.semester}")
            if school_year is None and "school_year" in student_info and student_info["school_year"]:
                user.school_year = student_info["school_year"]
                print(f"Updated school_year from PDF: {user.school_year}")
            if address is None and "address" in student_info and student_info["address"]:
                user.address = student_info["address"]
                print(f"Updated address from PDF: {user.address}")

            # Update student number, first name, last name if found in PDF
            if "student_number" in student_info and student_info["student_number"]:
                user.student_number = student_info["student_number"]
                print(f"Updated student_number from PDF: {user.student_number}")
                        # Update student number, first name, last name if found in PDF
            if "student_number" in student_info and student_info["student_number"]:
                user.student_number = student_info["student_number"]
                print(f"Updated student_number from PDF: {user.student_number}")
            if "name" in student_info and student_info["name"]:
                name_str = student_info["name"].strip()

                # Remove any middle initial (like "b.")
                name_str = re.sub(r'\s+[a-zA-Z]\.\s+', ' ', name_str)  # between names
                name_str = re.sub(r'\s+[a-zA-Z]\.$', '', name_str)     # at the end
                name_str = re.sub(r'\s+[a-zA-Z]\.(?=\s)', '', name_str) # before last name
                name_str = re.sub(r'\s+', ' ', name_str).strip()       # clean spacing

                # Split the cleaned name
                name_parts = name_str.split()

                if len(name_parts) >= 2:
                    user.first_name = ' '.join(name_parts[:-1]).title()
                    user.last_name = name_parts[-1].title()
                elif len(name_parts) == 1:
                    user.first_name = name_parts[0].title()
                    user.last_name = ''

            # Update email if first_name and last_name are available
            if user.first_name and user.last_name:
                user.email = generate_email(user.first_name.replace(" ", ""), user.last_name)
                print(f"Updated email: {user.email}")

        except Exception as e:
            print(f"Error processing registration form: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process registration form: {e}",
            )
        print(f"User object registration_form after save: {user.registration_form}")

    # 4. Handle Profile picture upload
    if profilePicture:
        print(
            f"Handling profile picture upload: {profilePicture.filename}, content_type: {profilePicture.content_type}"
        )
        # Validate image file type
        if not profilePicture.content_type.startswith("image/"):
            print(
                f"Error: Invalid file type: {profilePicture.content_type}. Only images are allowed."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only images are allowed.",
            )

        # Check image file size (optional)
        max_image_size_bytes = 2 * 1024 * 1024  # 2MB
        try:
            # Delete the previous profile picture if it exists
            print(f"Previous profile picture path: {user.profile_picture}")
            delete_file(user.profile_picture)

            image_content = await profilePicture.read()
            print(f"Image content length: {len(image_content)}")
            if len(image_content) > max_image_size_bytes:
                print(
                    f"Error: Image size too large: {len(image_content)} bytes. Maximum allowed size is {max_image_size_bytes} bytes."
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Image size too large. Maximum allowed size is {max_image_size_bytes} bytes.",
                )
            # Use PIL to open and validate the image
            img = Image.open(BytesIO(image_content))
            img.verify()  # Check if it's a valid image
            print("Image validation successful")
        except Exception as e:
            print(f"Error: Invalid image file: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid image file: {e}"
            )

        # Generate a secure filename
        filename = generate_secure_filename(profilePicture.filename)
        print(f"Generated filename: {filename}")
        # Construct the full file path - use os.path.join correctly
        file_path = os.path.join(
            "..",
            "frontend",  # Start from the project root
            "static",
            "images",
            "profile_pictures",
            filename,
        )
        print(f"Saving image to: {file_path}")
        # Save the image file
        try:
            # Ensure the directory exists before saving.
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            print("Directory created (if needed)")
            with open(file_path, "wb") as f:
                f.write(image_content)
            print("Image saved successfully")
            user.profile_picture = (
                f"/static/images/profile_pictures/{filename}"  # Store relative path
            )
            print(f"Profile picture path set to: {user.profile_picture}")
        except Exception as e:
            print(f"Error saving image: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  # Correct status code
                detail=f"Failed to save image: {e}",
            )

    # 5.  Generate and update email.  <-- Simplified and moved
    if first_name and last_name:
        email = generate_email(first_name, last_name)
        user.email = email
        print(f"Updating email: {email}")

    # 6. Commit the changes to the database
    try:
        db.commit()
        db.refresh(user)  # Refresh the user object to get the updated values
        print("Database commit successful")
        print(f"Profile updated successfully. Session after update: {request.session}")
        print(f"User registration form in database: {user.registration_form}")
        print(f"User profile picture in database: {user.profile_picture}")
        print(f"User email in database: {user.email}")  # <--- Added this line
    except Exception as e:
        db.rollback()
        print(f"Error updating profile in database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  # Correct status code
            detail=f"Failed to update profile in database: {e}",
        )

    # 7. Return the updated user data
    return {"message": "Profile updated successfully", "user": user}