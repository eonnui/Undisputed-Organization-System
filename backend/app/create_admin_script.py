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
from app.models import Admin, Organization   # Import Organization as well
from app.database import SQLALCHEMY_DATABASE_URL   # Import the database URL
import os   # Import the os module

def check_database_url():
    """
    Prints the database URL being used by the script.
    This function helps to verify that the script is using the correct database path.
    """
    print(f"Database URL being used: {SQLALCHEMY_DATABASE_URL}")

# Directly use the database URL from database.py, but modify it here
# to be an absolute path.
engine = create_engine(
    "sqlite:///" + os.path.join(backend_dir, "sql_app.db"),   # Corrected path here
    connect_args={"check_same_thread": False}
)

# Create a SQLAlchemy session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_organization(db, org_name, theme_color, styles_json_str="{}"):
    """Creates a new organization in the database."""
    try:
        # Check if the organization name already exists
        existing_org = db.query(Organization).filter(Organization.name == org_name).first()
        if existing_org:
            print(f"Error: Organization with name '{org_name}' already exists.")
            return None   # Return None to indicate failure

        # Create a new Organization object
        new_org = Organization(name=org_name, theme_color=theme_color, styles=styles_json_str)
        db.add(new_org)
        db.commit()
        db.refresh(new_org) # Refresh to get the ID
        print(f"Organization '{org_name}' created successfully with id: {new_org.id}.")
        return new_org   # Return the new organization object
    except Exception as e:
        print(f"Error creating organization: {e}")
        db.rollback()
        raise   # Re-raise the exception


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
        db.add(new_admin)
        db.flush() # Flush to get admin_id before linking organization

        if organization_id:   #if organization_id is provided.
            organization = db.get(Organization, organization_id)
            if organization:
                new_admin.organizations.append(organization) #Link the admin to the org
            else:
                print(f"Warning: Organization with ID {organization_id} not found. Admin created without organization link.")
        
        db.commit()
        db.refresh(new_admin) # Refresh to get the relationships loaded if needed later
        print(f"Admin user '{email}' created successfully with id: {new_admin.admin_id}.")
        return new_admin
    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        raise   # Re-raise the exception

def get_all_organizations(db):
    """Fetches all existing organizations from the database."""
    return db.query(Organization).all()

def main():
    check_database_url()

    while True:
        print("\n--- Admin Setup Menu ---")
        print("1. Create a NEW organization and its first admin.")
        print("2. Create an admin for an EXISTING organization.")
        print("3. Exit")

        choice = input("Enter your choice (1, 2, or 3): ")

        if choice == '1':
            org_name = input("Enter NEW organization name: ")
            theme_color = input("Enter NEW organization theme color (e.g., #f0ad4e or blue): ")
            admin_email = input("Enter admin email: ")
            admin_password = getpass.getpass("Enter admin password: ")
            admin_name = input("Enter admin name (optional, default 'Admin'): ") or "Admin"

            db = SessionLocal()
            try:
                # Create the organization
                organization = create_organization(db, org_name, theme_color)
                if organization:
                    # Create the admin user and link to the organization.
                    admin = create_admin_user(db, admin_email, admin_password, admin_name, organization_id=organization.id)
                    if admin:
                        print(f"Admin '{admin_email}' successfully linked to organization '{org_name}'.")
                    else:
                        print("Admin creation failed. Organization was created but no admin linked.")
                else:
                    print("Organization creation failed. No admin was created.")
            except Exception as e:
                print(f"An unexpected error occurred during new organization setup: {e}")
                db.rollback()
            finally:
                db.close()
            break # Exit after successful operation or failure in this path

        elif choice == '2':
            db = SessionLocal()
            try:
                organizations = get_all_organizations(db)
                if not organizations:
                    print("No existing organizations found. Please create one first.")
                    db.close()
                    continue # Go back to main menu

                print("\n--- Existing Organizations ---")
                for org in organizations:
                    print(f"ID: {org.id}, Name: {org.name}, Theme Color: {org.theme_color}")

                org_id_input = input("Enter the ID of the organization to add an admin to: ")
                try:
                    selected_org_id = int(org_id_input)
                except ValueError:
                    print("Invalid organization ID. Please enter a number.")
                    db.close()
                    continue # Go back to main menu

                # Verify if the organization exists
                selected_organization = db.get(Organization, selected_org_id)
                if not selected_organization:
                    print(f"Organization with ID {selected_org_id} not found.")
                    db.close()
                    continue # Go back to main menu

                admin_email = input(f"Enter admin email for '{selected_organization.name}': ")
                admin_password = getpass.getpass("Enter admin password: ")
                admin_name = input("Enter admin name (optional, default 'Admin'): ") or "Admin"

                admin = create_admin_user(db, admin_email, admin_password, admin_name, organization_id=selected_organization.id)
                if admin:
                    print(f"Admin '{admin_email}' successfully added to organization '{selected_organization.name}'.")
                else:
                    print("Admin creation failed for existing organization.")
            except Exception as e:
                print(f"An unexpected error occurred during existing organization admin setup: {e}")
                db.rollback()
            finally:
                db.close()
            break # Exit after successful operation or failure in this path

        elif choice == '3':
            print("Exiting setup.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
