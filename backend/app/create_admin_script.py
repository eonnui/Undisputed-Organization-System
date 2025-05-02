import bcrypt
import getpass
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Adjust the path to correctly import from main.py and models.py
script_path = Path(__file__).resolve()
app_dir = script_path.parent
backend_dir = app_dir.parent
sys.path.insert(0, str(backend_dir))

# Now we can import directly
from app.models import Admin  # Import only Admin, not Base
from app.database import SQLALCHEMY_DATABASE_URL  # Import the database URL
import os  # Import the os module

def check_database_url():
    """
    Prints the database URL being used by the script.
    This function helps to verify that the script is using the correct database path.
    """
    print(f"Database URL being used: {SQLALCHEMY_DATABASE_URL}")

# Directly use the database URL from database.py, but modify it here
# to be an absolute path.
engine = create_engine(
    "sqlite:///" + os.path.join(backend_dir, "sql_app.db"),  # Corrected path here
    connect_args={"check_same_thread": False}
)

# Create a SQLAlchemy session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_admin_user(email, password, name="Admin", role="Admin"):
    """Creates a new admin user in the database."""
    db = SessionLocal()
    try:
        # Check if the email already exists
        existing_admin = db.query(Admin).filter(Admin.email == email).first()
        if existing_admin:
            print(f"Error: Admin with email '{email}' already exists.")
            return

        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Create a new Admin object
        new_admin = Admin(name=name, email=email, password=hashed_password, role=role)

        db.add(new_admin)
        db.commit()
        print(f"Admin user '{email}' created successfully with id: {new_admin.admin_id}.")
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        raise  # Re-raise the exception to see the full traceback
    finally:
        db.close()


if __name__ == "__main__":
    # Print the database URL to the console
    check_database_url()

    email = input("Enter admin email: ")
    password = getpass.getpass("Enter admin password: ")  # Get password securely
    create_admin_user(email, password)
