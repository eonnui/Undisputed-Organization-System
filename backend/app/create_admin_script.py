import bcrypt
import getpass
import sys
import os
import json
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Adjust the path to correctly import from main.py and models.py
script_path = Path(__file__).resolve()
app_dir = script_path.parent
backend_dir = app_dir.parent
sys.path.insert(0, str(backend_dir))

# Now we can import directly
from app.models import Admin, Organization, User
from app.database import SQLALCHEMY_DATABASE_URL

def check_database_url():
    """
    Prints the database URL being used by the script.
    This function helps to verify that the script is using the correct database path.
    """
    print(f"Database URL being used: {SQLALCHEMY_DATABASE_URL}")

# Directly use the database URL from database.py, but modify
# to be an absolute path.
engine = create_engine(
    "sqlite:///" + os.path.join(backend_dir, "sql_app.db"),
    connect_args={"check_same_thread": False}
)

# Create a SQLAlchemy session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Helper functions for color manipulation ---
def hex_to_rgb(hex_color):
    """Converts a hex color string (#RRGGBB) to an RGB tuple (R, G, B)."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb_color):
    """Converts an RGB tuple (R, G, B) to a hex color string (#RRGGBB)."""
    return '#%02x%02x%02x' % rgb_color

def adjust_rgb_lightness(rgb, factor):
    """Adjusts the lightness of an RGB color by a factor (e.g., 0.8 for darker, 1.2 for lighter)."""
    r, g, b = rgb
    r = int(max(0, min(255, r * factor)))
    g = int(max(0, min(255, g * factor)))
    b = int(max(0, min(255, b * factor)))
    return (r, g, b)

def get_contrast_text_color(bg_hex):
    """Returns #FFFFFF or #000000 based on the perceived lightness of the background color."""
    r, g, b = hex_to_rgb(bg_hex)
    # Calculate perceived lightness (luminance)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"


# --- Modified create_organization function ---
def create_organization(db, org_name, theme_color, primary_course_code=None):
    """Creates a new organization in the database with an auto-generated custom palette."""
    try:
        # Check if the organization name already exists
        existing_org = db.query(Organization).filter(Organization.name == org_name).first()
        if existing_org:
            print(f"Error: Organization with name '{org_name}' already exists.")
            return None # Return None for org

        default_custom_palette = json.dumps({}) # Or load a default palette from a file/constant

        # Create a new Organization object
        new_org = Organization(
            name=org_name,
            theme_color=theme_color,
            custom_palette=default_custom_palette, # Use default or empty palette
            primary_course_code=primary_course_code, # Add primary_course_code
            # logo_url is removed
        )
        db.add(new_org)
        db.commit()
        db.refresh(new_org) # Refresh to get the ID
        print(f"Organization '{org_name}' created successfully with id: {new_org.id}.")
        return new_org # Return the organization
    except Exception as e:
        print(f"Error creating organization: {e}")
        db.rollback()
        raise


def create_admin_user(db, email, password, name="Admin", role="Admin", organization_id=None, position=None):
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
        new_admin = Admin(name=name, email=email, password=hashed_password, role=role, position=position)
        db.add(new_admin)
        db.flush() # Flush to get admin_id before linking organization

        if organization_id:
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
        raise

def get_all_organizations(db):
    """Fetches all existing organizations from the database."""
    return db.query(Organization).all()

# --- Modified function to update organization theme color ---
def update_organization_theme_color(db, org_id: int, new_theme_color: str):
    """
    Updates the theme color of an existing organization. The custom palette
    will NOT be regenerated here, assuming it's managed externally or defaults.
    """
    try:
        organization = db.get(Organization, org_id)
        if not organization:
            print(f"Error: Organization with ID {org_id} not found.")
            return False

        # Update the theme_color
        organization.theme_color = new_theme_color

        db.add(organization)
        db.commit()
        db.refresh(organization)
        print(f"Organization '{organization.name}' (ID: {org_id}) theme color updated to {new_theme_color}.")
        return True
    except Exception as e:
        print(f"An unexpected error occurred during theme color update: {e}")
        db.rollback()
        return False

# --- Function to update an admin's position ---
def update_admin_position(db, admin_id: int, new_position: str):
    """
    Updates the position of an existing admin.
    """
    try:
        admin = db.get(Admin, admin_id)
        if not admin:
            print(f"Error: Admin with ID {admin_id} not found.")
            return False

        admin.position = new_position
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Admin '{admin.name}' (ID: {admin_id}) position updated to '{new_position}' successfully.")
        return True
    except Exception as e:
        print(f"An unexpected error occurred during admin position update: {e}")
        db.rollback()
        return False

# --- Function to delete an organization and its associated admins and users ---
def delete_organization(db, org_id: int):
    """
    Deletes an organization and all associated admins and users.
    """
    try:
        organization = db.get(Organization, org_id)
        if not organization:
            print(f"Error: Organization with ID {org_id} not found.")
            return False

        admins_to_delete = db.query(Admin).filter(Admin.organizations.any(id=org_id)).all()
        for admin in admins_to_delete:
            print(f"Deleting admin: {admin.email} (ID: {admin.admin_id})")
            db.delete(admin)

        users_to_delete = db.query(User).filter(User.organization_id == org_id).all()
        for user in users_to_delete:
            print(f"Deleting user: {user.email} (ID: {user.id})")
            db.delete(user)

        print(f"Deleting organization: {organization.name} (ID: {org_id})")
        db.delete(organization)

        db.commit()
        print(f"Organization '{organization.name}' (ID: {org_id}) and its associated admins/users deleted successfully.")
        return True
    except Exception as e:
        print(f"An unexpected error occurred during organization deletion: {e}")
        db.rollback()
        return False

# --- NEW: Function to display all organizations, their admins, and users ---
def display_all_data(db):
    """
    Displays all organizations, their associated admins, and all users,
    with users neatly segregated by their organization in a table format.
    """
    try:
        organizations = db.query(Organization).all()
        all_users = db.query(User).all()

        if not organizations and not all_users:
            print("\nNo organizations or users found in the database.")
            return

        # Create a dictionary to hold users by organization ID
        users_by_org = {org.id: [] for org in organizations}
        users_by_org[None] = [] # For users without an organization

        for user in all_users:
            if user.organization_id in users_by_org:
                users_by_org[user.organization_id].append(user)
            else:
                users_by_org[None].append(user)


        print("\n" + "="*80)
        print("--- All Organizations and Their Members ---".center(80))
        print("="*80)

        if organizations:
            for org in organizations:
                print(f"\n{'='*70}")
                print(f"Organization: {org.name} (ID: {org.id})".ljust(70))
                print(f"Theme Color: {org.theme_color}".ljust(70))
                # Display Primary Course Code
                print(f"Primary Course Code: {org.primary_course_code if org.primary_course_code else 'N/A'}".ljust(70))
                print(f"{'-'*70}")

                # Display Admins for this organization
                org_admins = db.query(Admin).filter(Admin.organizations.any(id=org.id)).all()
                if org_admins:
                    print(f"  Admins for '{org.name}':")
                    print(f"  {'Admin ID':<10} | {'Name':<20} | {'Email':<30} | {'Position':<15}")
                    print(f"  {'-'*10}-+-{'-'*20}-+-{'-'*30}-+-{'-'*15}")
                    for admin in org_admins:
                        position = admin.position if admin.position else 'N/A'
                        print(f"  {admin.admin_id:<10} | {admin.name:<20} | {admin.email:<30} | {position:<15}")
                else:
                    print(f"  No admins found for '{org.name}'.")
                print("\n")

                # Display Users for this organization
                org_users = users_by_org.get(org.id, [])
                if org_users:
                    print(f"  Users for '{org.name}':")
                    print(f"  {'User ID':<10} | {'Student No.':<15} | {'Name':<25} | {'Email':<30}")
                    print(f"  {'-'*10}-+-{'-'*15}-+-{'-'*25}-+-{'-'*30}")
                    for user in org_users:
                        full_name = f"{user.first_name} {user.last_name}"
                        print(f"  {user.id:<10} | {user.student_number:<15} | {full_name:<25} | {user.email:<30}")
                else:
                    print(f"  No users found for '{org.name}'.")
                print(f"\n{'='*70}\n")
        else:
            print("No organizations found in the database.")

        # Display users without an organization
        unassigned_users = users_by_org.get(None, [])
        if unassigned_users:
            print("\n" + "="*80)
            print("--- Users Without an Assigned Organization ---".center(80))
            print("="*80)
            print(f"  {'User ID':<10} | {'Student No.':<15} | {'Name':<25} | {'Email':<30}")
            print(f"  {'-'*10}-+-{'-'*15}-+-{'-'*25}-+-{'-'*30}")
            for user in unassigned_users:
                full_name = f"{user.first_name} {user.last_name}"
                print(f"  {user.id:<10} | {user.student_number:<15} | {full_name:<25} | {user.email:<30}")
            print("\n" + "="*80)
        elif not organizations:
             pass

    except Exception as e:
        print(f"An unexpected error occurred while displaying data: {e}")
    finally:
        db.close()


def main():
    check_database_url()

    while True:
        print("\n--- Admin Setup Menu ---")
        print("1. Create a NEW organization and its first admin.")
        print("2. Create an admin for an EXISTING organization.")
        print("3. Edit theme color for an EXISTING organization.")
        print("4. Update an admin's position.")
        print("5. Delete an organization and its associated admins/users.")
        print("6. Display ALL organizations, admins, and users.") # NEW MENU OPTION
        print("7. Exit") # Updated exit option

        choice = input("Enter your choice (1, 2, 3, 4, 5, 6, or 7): ") # Updated prompt

        if choice == '1':
            org_name = input("Enter NEW organization name: ")
            theme_color = input("Enter NEW organization theme color (e.g., #RRGGBB, must be a hex code): ")
            if not (theme_color.startswith('#') and len(theme_color) == 7 and all(c in '0123456789abcdefABCDEF' for c in theme_color[1:])):
                print("Invalid theme color format. Please enter a valid hex code (e.g., #f0ad4e).")
                continue
            primary_course_code = input("Enter the primary course code for the new organization (optional): ") or None

            admin_email = input("Enter admin email: ")
            admin_password = getpass.getpass("Enter admin password: ")
            admin_name = input("Enter admin name (optional, default 'Admin'): ") or "Admin"
            admin_position = input("Enter admin position (e.g., President, Secretary, etc.): ")

            db = SessionLocal()
            try:
                organization = create_organization(db, org_name, theme_color, primary_course_code) # Pass primary_course_code
                if organization:
                    admin = create_admin_user(db, admin_email, admin_password, admin_name, organization_id=organization.id, position=admin_position)
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

        elif choice == '2':
            db = SessionLocal()
            try:
                organizations = get_all_organizations(db)
                if not organizations:
                    print("No existing organizations found. Please create one first.")
                    db.close()
                    continue

                print("\n--- Existing Organizations ---")
                for org in organizations:
                    print(f"ID: {org.id}, Name: {org.name}, Theme Color: {org.theme_color}, Primary Course: {org.primary_course_code if org.primary_course_code else 'N/A'}")

                org_id_input = input("Enter the ID of the organization to add an admin to: ")
                try:
                    selected_org_id = int(org_id_input)
                except ValueError:
                    print("Invalid organization ID. Please enter a number.")
                    db.close()
                    continue

                selected_organization = db.get(Organization, selected_org_id)
                if not selected_organization:
                    print(f"Organization with ID {selected_org_id} not found.")
                    db.close()
                    continue

                admin_email = input(f"Enter admin email for '{selected_organization.name}': ")
                admin_password = getpass.getpass("Enter admin password: ")
                admin_name = input("Enter admin name (optional, default 'Admin'): ") or "Admin"
                admin_position = input("Enter admin position (e.g., President, Secretary, etc.): ")


                admin = create_admin_user(db, admin_email, admin_password, admin_name, organization_id=selected_organization.id, position=admin_position)
                if admin:
                    print(f"Admin '{admin_email}' successfully added to organization '{selected_organization.name}'.")
                else:
                    print("Admin creation failed for existing organization.")
            except Exception as e:
                print(f"An unexpected error occurred during existing organization admin setup: {e}")
                db.rollback()
            finally:
                db.close()

        elif choice == '3':
            db = SessionLocal()
            try:
                organizations = get_all_organizations(db)
                if not organizations:
                    print("No existing organizations found.")
                    db.close()
                    continue

                print("\n--- Existing Organizations ---")
                for org in organizations:
                    print(f"ID: {org.id}, Name: {org.name}, Current Theme Color: {org.theme_color}, Primary Course: {org.primary_course_code if org.primary_course_code else 'N/A'}")

                org_id_input = input("Enter the ID of the organization to edit its theme color: ")
                try:
                    selected_org_id = int(org_id_input)
                except ValueError:
                    print("Invalid organization ID. Please enter a number.")
                    db.close()
                    continue

                organization_to_edit = db.get(Organization, selected_org_id)
                if not organization_to_edit:
                    print(f"Organization with ID {selected_org_id} not found.")
                    db.close()
                    continue

                new_theme_color = input(f"Enter the NEW theme color for '{organization_to_edit.name}' (e.g., #RRGGBB): ")
                if not (new_theme_color.startswith('#') and len(new_theme_color) == 7 and all(c in '0123456789abcdefABCDEF' for c in new_theme_color[1:])):
                    print("Invalid theme color format. Please enter a valid hex code (e.g., #f0ad4e).")
                    db.close()
                    continue

                update_organization_theme_color(db, selected_org_id, new_theme_color)

            except Exception as e:
                print(f"An unexpected error occurred during theme color update: {e}")
                db.rollback()
            finally:
                db.close()

        elif choice == '4': # Update Admin Position
            db = SessionLocal()
            try:
                admins = db.query(Admin).all()
                if not admins:
                    print("No admins found.")
                    db.close()
                    continue

                print("\n--- Existing Admins ---")
                for admin in admins:
                    print(f"ID: {admin.admin_id}, Name: {admin.name}, Email: {admin.email}, Current Position: {admin.position if admin.position else 'N/A'}")

                admin_id_input = input("Enter the ID of the admin to update their position: ")
                try:
                    selected_admin_id = int(admin_id_input)
                except ValueError:
                    print("Invalid admin ID. Please enter a number.")
                    db.close()
                    continue

                admin_to_edit = db.get(Admin, selected_admin_id)
                if not admin_to_edit:
                    print(f"Admin with ID {selected_admin_id} not found.")
                    db.close()
                    continue

                new_position = input(f"Enter the NEW position for '{admin_to_edit.name}' (e.g., President, Secretary, etc.): ")
                if not new_position:
                    print("Position cannot be empty.")
                    db.close()
                    continue

                update_admin_position(db, selected_admin_id, new_position)

            except Exception as e:
                print(f"An unexpected error occurred during admin position update: {e}")
                db.rollback()
            finally:
                db.close()

        elif choice == '5': # Delete Organization
            db = SessionLocal()
            try:
                organizations = get_all_organizations(db)
                if not organizations:
                    print("No existing organizations found.")
                    db.close()
                    continue

                print("\n--- Existing Organizations ---")
                for org in organizations:
                    print(f"ID: {org.id}, Name: {org.name}, Primary Course: {org.primary_course_code if org.primary_course_code else 'N/A'}")

                org_id_input = input("Enter the ID of the organization to DELETE (THIS ACTION IS IRREVERSIBLE): ")
                try:
                    selected_org_id = int(org_id_input)
                except ValueError:
                    print("Invalid organization ID. Please enter a number.")
                    db.close()
                    continue

                confirm = input(f"Are you sure you want to delete organization with ID {selected_org_id} and all its associated admins and users? Type 'yes' to confirm: ")
                if confirm.lower() == 'yes':
                    delete_organization(db, selected_org_id)
                else:
                    print("Organization deletion cancelled.")

            except Exception as e:
                print(f"An unexpected error occurred during organization deletion: {e}")
                db.rollback()
            finally:
                db.close()

        elif choice == '6': # Display ALL data
            db = SessionLocal()
            display_all_data(db) # Call the new function
            # The function handles closing the db session internally

        elif choice == '7': # Exit choice
            print("Exiting setup.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, 5, 6, or 7.")

if __name__ == "__main__":
    main()
