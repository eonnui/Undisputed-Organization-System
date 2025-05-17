import bcrypt
import getpass
import sys
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Adjust the path to correctly import from main.py and models.py
script_path = Path(__file__).resolve()
app_dir = script_path.parent
backend_dir = app_dir.parent
sys.path.insert(0, str(backend_dir))

# Now we can import directly
from app.models import Admin, Organization  # Import Organization as well
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


def create_organization(db, org_name, theme_color):
    """Creates a new organization in the database."""
    try:
        # Check if the organization name already exists
        existing_org = db.query(Organization).filter(Organization.name == org_name).first()
        if existing_org:
            print(f"Error: Organization with name '{org_name}' already exists.")
            return None  # Return None to indicate failure

        # Create a new Organization object
        new_org = Organization(name=org_name, theme_color=theme_color)
        db.add(new_org)
        db.commit()
        print(f"Organization '{org_name}' created successfully with id: {new_org.id}.")
        return new_org  # Return the new organization object
    except Exception as e:
        print(f"Error creating organization: {e}")
        db.rollback()
        raise  # Re-raise the exception
    #finally:  # Removed finally to handle the session in create_org_and_admin
    #    db.close()



def create_admin_user(db, email, password, name="Admin", role="Admin", organization_id=None):
    """Creates a new admin user in the database."""
    try:
        # Check if the email already exists
        existing_admin = db.query(Admin).filter(Admin.email == email).first()
        if existing_admin:
            print(f"Error: Admin with email '{email}' already exists.")
            return None

        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        # Create a new Admin object
        new_admin = Admin(name=name, email=email, password=hashed_password, role=role)
        if organization_id:  #if organization_id is provided.
            new_admin.organizations.append(db.get(Organization, organization_id)) #Link the admin to the org
        db.add(new_admin)
        db.commit()
        print(f"Admin user '{email}' created successfully with id: {new_admin.admin_id}.")
        return new_admin
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        raise  # Re-raise the exception to see the full traceback
    # finally: #Removed finally to handle session in create_org_and_admin
    #     db.close()

def create_org_and_admin(org_name, theme_color, admin_email, admin_password, admin_name="Admin"):
    """Creates an organization and an admin user, linking them."""
    db = SessionLocal() #Create one session.
    try:
        # 1. Create the organization
        organization = create_organization(db, org_name, theme_color)
        if organization is None:
            return  # Exit if organization creation failed

        # 2. Create the admin user and link to the organization.
        admin = create_admin_user(db, admin_email, admin_password, admin_name, organization_id=organization.id) #Pass the org id
        if admin is None:
            return # Exit if admin creation failed.

        db.commit() #Commit both at the end.
        print(f"Admin '{admin_email}' successfully linked to organization '{org_name}'.")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Print the database URL to the console
    check_database_url()

    org_name = input("Enter organization name: ")
    theme_color = input("Enter organization theme color (e.g., #f0ad4e or blue): ")
    admin_email = input("Enter admin email: ")
    admin_password = getpass.getpass("Enter admin password: ")
    admin_name = input("Enter admin name (optional, default 'Admin'): ") or "Admin" #Added admin name

    create_org_and_admin(org_name, theme_color, admin_email, admin_password, admin_name)
