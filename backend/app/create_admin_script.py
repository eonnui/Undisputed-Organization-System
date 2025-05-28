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
from app.models import Admin, Organization
from app.database import SQLALCHEMY_DATABASE_URL

def check_database_url():
    """
    Prints the database URL being used by the script.
    This function helps to verify that the script is using the correct database path.
    """
    print(f"Database URL being used: {SQLALCHEMY_DATABASE_URL}")

# Directly use the database URL from database.py, but modify it here
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

# --- New function to generate custom palette ---
def generate_custom_palette(theme_color_hex):
    """
    Generates a full custom CSS variable palette based on a primary theme color.
    Uses a predefined template and adjusts relevant colors.
    """
    # Base template derived from the "Samahan ng Sikolohiya" example.
    # You can modify this template or create more if needed.
    base_palette = {
        "--org-bg-color": "#fdf5f5", # Original default light background color
        "--org-login-bg": "#5c1011",
        "--org-button-bg": "#9a1415",
        "--org-button-text": "#FFFFFF",
        "--org-hover-effect": "#7a1012",
        "--org-accent-light": "#d32f2f",
        "--org-accent-dark": "#5c0b0b",
        "--org-highlight": "#ffebee",
        "--org-text-primary": "#212121",
        "--org-text-secondary": "#757575",
        "--org-text-inverse": "#FFFFFF",
        "--org-hover-dark": "#424242",
        "--org-hover-accent": "#b71c1c",
        "--org-focus-border": "transparent",
        "--org-success": "#4CAF50",
        "--org-error": "#F44336",
        "--org-warning": "#FFC107",
        "--org-info": "#2196F3",
        "--org-bg-secondary": "#FFFFFF",
        "--org-bg-dark": "#1a1a1a",
        "--org-border-light": "transparent",
        "--org-border-medium": "transparent",
        "--org-nav-item-bg": "transparent",
        "--org-nav-item-hover-bg": "rgba(154, 20, 21, 0.05)",
        "--org-nav-item-selected-bg": "rgba(154, 20, 21, 0.1)",
        "--org-sidebar-bg-color": "#a83232",
        "--org-sidebar-border-color": "transparent",
        "--org-logo-border-color": "transparent",
        "--org-nav-icon-color": "#FFFFFF",
        "--org-nav-hover-accent-color": "#fdf5f5",
        "--org-nav-selected-border-color": "transparent",
        "--org-top-bar-border-color": "transparent",
        "--org-menu-button-hover-bg": "rgba(0, 0, 0, 0.05)",
        "--org-profile-pic-border-color": "transparent",
        "--org-dropdown-bg": "#FFFFFF",
        "--org-dropdown-border": "transparent",
        "--org-dropdown-item-hover-bg": "#f5f5f5",
        "--org-dashboard-bg-color": "#fdf5f5",
        "--org-dashboard-title-color": "#5c0b0b",
        "--org-shadow-base-rgb": "0, 0, 0",
        "--org-card-bg": "#FFFFFF",
        "--org-announcement-card-bg": "#fefefe",
        "--org-dashboard-accent-primary": "#d32f2f",
        "--org-announcement-text-color": "#212121",
        "--org-announcement-meta-color": "#757575",
        "--org-view-details-hover": "#b71c1c",
        "--org-event-placeholder-color": "#9e9e9e",
        "--org-faq-border-color": "transparent",
        "--org-faq-item-bg": "#fefefe",
        "--org-faq-question-hover-bg": "#f5f5f5",
        "--org-faq-answer-color": "#424242",
        "--org-empty-state-color": "#9e9e9e",
        "--org-empty-state-bg": "#fefefe",
        "--org-post-card-border": "transparent",
        "--org-profile-image-bg": "#e0e0e0",
        "--org-post-info-color": "#5a5a5a",
        "--org-post-date-color": "#9e9e9e",
        "--org-post-content-color": "#333333",
        "--org-post-actions-color": "#757575",
        "--org-heart-hover-color": "#e57373",
        "--org-heart-button-color": "#e53935",
        "--org-pinned-bg": "#FFC107",
        "--org-event-meta-color": "#757575",
        "--org-event-description-color": "#424242",
        "--org-event-item-border": "transparent",
        "--org-event-item-hover-bg": "#f5f5f5",
        "--org-event-tag-bg": "#ffebee",
        "--org-event-tag-text": "#b71c1c",
        "--org-academic-tag-bg": "#fbe9e7",
        "--org-academic-tag-text": "#c62828",
        "--org-sports-tag-bg": "#e8f5e9",
        "--org-sports-tag-text": "#388e3c",
        "--org-arts-tag-bg": "#fffde7",
        "--org-arts-tag-text": "#f9a825",
        "--org-music-tag-bg": "#ffecb3",
        "--org-music-tag-text": "#f57f17",
        "--org-esports-tag-bg": "#e0f7fa",
        "--org-esports-tag-text": "#00838f",
        "--org-cultural-tag-bg": "#f3e5f5",
        "--org-cultural-tag-text": "#7b1fa2",
        "--org-join-btn-bg": "#43a047",
        "--org-join-btn-hover-bg": "#388e3c",
        "--org-leave-btn-bg": "#e53935",
        "--org-leave-btn-hover-bg": "#d32f2f",
        "--org-event-full-bg": "#9e9e9e",
        "--org-event-full-text": "#FFFFFF",
        "--org-join-button-bg": "#43a047",
        "--org-join-button-hover-bg": "#45a049",
        "--org-leave-button-bg": "#f44336",
        "--org-leave-button-hover-bg": "#d32f2f",
        "--org-full-button-bg": "#bdbdbd",
        "--org-full-button-text": "#424242",
        "--org-participants-count-color": "#757575",
        "--org-payments-container-bg": "#fdf5f5",
        "--org-border-light-darker": "transparent",
        "--org-text-primary-darker": "#000000",
        "--org-table-header-bg-payments": "#fbc4cb",
        "--org-table-header-text-payments": "#333333",
        "--org-table-data-text": "#333333",
        "--org-background-light-alt-darker": "#fefafa",
        # These values are now fixed as per user's request
        "--org-status-unpaid-bg": "#ffebee",
        "--org-status-unpaid-text": "#b71c1c",
        "--org-error-border": "transparent",
        "--org-pay-button-bg-payments": "#e53935",
        "--org-pay-button-hover-bg-payments": "#d32f2f",
        "--org-standby-button-bg-payments": "#bdbdbd",
        "--org-button-disabled-text-darker": "#757575",
        "--org-past-due-bg": "#ffebee",
        "--org-past-due-text": "#b71c1c",
        "--org-past-due-hover-bg": "#ffcdd2",
        "--org-past-due-hover-text": "#b71c1c",
        "--org-surface": "#FFFFFF",
        "--org-radius-lg": "12px",
        "--org-shadow-md": "0 4px 10px rgba(0, 0, 0, 0.12)",
        "--org-transition": "all 0.3s ease-in-out",
        "--org-shadow-lg": "0 6px 15px rgba(0, 0, 0, 0.18)",
        "--org-primary": "#9a1415",
        "--org-radius-md": "8px",
        "--org-shadow-sm": "0 2px 5px rgba(0, 0, 0, 0.08)",
        "--org-text-light": "#FFFFFF",
        "--org-secondary-color": "#f5f5f5",
        "--org-primary-light": "#ffcdd2",
        "--org-primary-hover": "#b71c1c",
        "--org-settings-section-bg": "#f5f5f5",
        "--org-settings-title-color": "#212121",
        "--org-button-group-button-update-bg": "#a83232",
        "--org-button-group-button-update-hover-bg": "#862828",
        "--org-button-group-button-clear-bg": "#FFFFFF",
        "--org-button-group-button-clear-hover-bg": "transparent",
        "--org-profile-picture-border": "transparent",
        "--org-change-profile-pic-bg": "#a83232",
        "--org-change-profile-pic-hover-bg": "#862828",
        "--org-student-info-section-bg": "#FFFFFF",
        "--org-verified-bg": "#4CAF50",
        "--org-verified-text": "#FFFFFF",
        "--org-unverified-bg": "#FFC107",
        "--org-unverified-text": "#212121",
        "--org-registration-form-section-bg": "#FFFFFF",
        "--org-edit-icon-bg": "#FFFFFF",
        "--org-edit-icon-hover-bg": "#f5f5f5",
        "--org-read-only-input-bg": "#fdf5f5",
        "--org-read-only-input-text": "#757575",
        "--org-form-group-label-color": "#212121",
        "--org-form-group-input-border": "transparent",
        "--org-form-group-input-focus-border": "transparent"
    }

    # Start with a copy of the base palette
    custom_palette = base_palette.copy()

    # Convert theme_color to RGB for manipulation
    theme_rgb = hex_to_rgb(theme_color_hex)

    # Derive new colors based on the theme_color
    dark_theme_rgb = adjust_rgb_lightness(theme_rgb, 0.7) # 30% darker
    darker_theme_rgb = adjust_rgb_lightness(theme_rgb, 0.5) # 50% darker
    light_theme_rgb = adjust_rgb_lightness(theme_rgb, 1.2) # 20% lighter
    lighter_theme_rgb = adjust_rgb_lightness(theme_rgb, 1.6) # 60% lighter

    # Convert derived RGBs back to hex
    dark_theme_hex = rgb_to_hex(dark_theme_rgb)
    darker_theme_hex = rgb_to_hex(darker_theme_rgb)
    light_theme_hex = rgb_to_hex(light_theme_rgb)
    lighter_theme_hex = rgb_to_hex(lighter_theme_rgb)

    # Calculate the very light background color by blending with white
    whiteness_factor = .9 # Adjust this (e.g., 0.9 to 0.98) for desired lightness
    very_light_bg_rgb = (
        int(theme_rgb[0] * (1 - whiteness_factor) + 255 * whiteness_factor),
        int(theme_rgb[1] * (1 - whiteness_factor) + 255 * whiteness_factor),
        int(theme_rgb[2] * (1 - whiteness_factor) + 255 * whiteness_factor)
    )
    # Ensure values are clamped to 0-255
    very_light_bg_rgb = (
        max(0, min(255, very_light_bg_rgb[0])),
        max(0, min(255, very_light_bg_rgb[1])),
        max(0, min(255, very_light_bg_rgb[2]))
    )
    very_light_bg_hex = rgb_to_hex(very_light_bg_rgb) # This is the new light background color

    # --- NEW LOGIC: Ensure all specified variables are connected to very_light_bg_hex ---
    custom_palette["--org-bg-color"] = very_light_bg_hex
    custom_palette["--org-secondary-color"] = very_light_bg_hex
    custom_palette["--org-dashboard-bg-color"] = very_light_bg_hex
    custom_palette["--org-payments-container-bg"] = very_light_bg_hex
    custom_palette["--org-nav-hover-accent-color"] = very_light_bg_hex
    custom_palette["--org-settings-section-bg"] = very_light_bg_hex
    custom_palette["--org-read-only-input-bg"] = very_light_bg_hex


    # Determine contrast text color for buttons/primary elements
    button_text_color = get_contrast_text_color(theme_color_hex)

    # Update specific relevant variables in the custom_palette that are linked to the theme
    custom_palette["--org-primary"] = theme_color_hex
    custom_palette["--org-button-bg"] = theme_color_hex
    custom_palette["--org-hover-effect"] = dark_theme_hex
    custom_palette["--org-accent-light"] = light_theme_hex # Adjusted for lighter accent
    custom_palette["--org-accent-dark"] = darker_theme_hex
    custom_palette["--org-hover-accent"] = dark_theme_hex
    custom_palette["--org-primary-hover"] = dark_theme_hex
    custom_palette["--org-primary-light"] = lighter_theme_hex
    custom_palette["--org-dashboard-accent-primary"] = light_theme_hex # Adjusted for lighter accent

    # Derived colors for navigation, sidebar based on primary
    custom_palette["--org-login-bg"] = darker_theme_hex
    custom_palette["--org-sidebar-bg-color"] = dark_theme_hex
    custom_palette["--org-nav-item-hover-bg"] = f"rgba({theme_rgb[0]}, {theme_rgb[1]}, {theme_rgb[2]}, 0.05)"
    custom_palette["--org-nav-item-selected-bg"] = f"rgba({theme_rgb[0]}, {theme_rgb[1]}, {theme_rgb[2]}, 0.1)"
    # custom_palette["--org-nav-hover-accent-color"] is now set to very_light_bg_hex
    custom_palette["--org-nav-icon-color"] = button_text_color # Icons on primary-like background

    # Button/Text colors related to primary/accents
    custom_palette["--org-button-text"] = button_text_color
    custom_palette["--org-dashboard-title-color"] = darker_theme_hex # Titles might be darker primary
    custom_palette["--org-text-light"] = button_text_color # Text on primary backgrounds

    # Update specific tag/status colors if they are meant to follow the primary
    custom_palette["--org-event-tag-bg"] = lighter_theme_hex # Light background for tags
    custom_palette["--org-event-tag-text"] = dark_theme_hex # Dark text for tags

    custom_palette["--org-academic-tag-bg"] = adjust_rgb_lightness(hex_to_rgb(theme_color_hex), 1.4) # Even lighter
    custom_palette["--org-academic-tag-text"] = darker_theme_hex

    # Payments specific colors
    # custom_palette["--org-payments-container-bg"] is now set to very_light_bg_hex
    custom_palette["--org-table-header-bg-payments"] = lighter_theme_hex
    custom_palette["--org-table-header-text-payments"] = get_contrast_text_color(lighter_theme_hex) # Text on light header

    # The following variables are now explicitly set to the user-defined fixed values
    # and will not be dynamically updated based on the theme color.
    # --org-status-unpaid-bg: #ffebee
    # --org-status-unpaid-text: #b71c1c
    # --org-pay-button-bg-payments: #e53935
    # --org-pay-button-hover-bg-payments: #d32f2f
    # --org-past-due-bg: #ffebee
    # --org-past-due-text: #b71c1c
    # --org-past-due-hover-bg: #ffcdd2
    # --org-past-due-hover-text: #b71c1c

    # Update for settings section
    # custom_palette["--org-settings-section-bg"] is now set to very_light_bg_hex
    custom_palette["--org-settings-title-color"] = darker_theme_hex

    # Update for button groups in settings
    custom_palette["--org-button-group-button-update-bg"] = dark_theme_hex
    custom_palette["--org-button-group-button-update-hover-bg"] = darker_theme_hex
    custom_palette["--org-change-profile-pic-bg"] = dark_theme_hex
    custom_palette["--org-change-profile-pic-hover-bg"] = darker_theme_hex

    # Read-only inputs
    # custom_palette["--org-read-only-input-bg"] is now set to very_light_bg_hex

    # Set --org-highlight to be the same as the very light background color
    custom_palette["--org-highlight"] = very_light_bg_hex

    # Ensure the main primary color is always the theme color
    custom_palette["--org-primary"] = theme_color_hex


    # Return the palette as a JSON string
    return json.dumps(custom_palette, indent=2)

# --- Modified function to generate logo URL and suggested filename ---
def generate_logo_url(org_name: str) -> tuple[str, str]:
    """
    Generates the logo URL following the /static/images/ format
    and a suggested filename based on the organization name.
    Returns a tuple: (logo_url, suggested_filename).
    """
    formatted_name = org_name.lower().replace(" ", "_") 
    
    # Define a default image extension, e.g., ".png"
    default_extension = ".png"
    
    suggested_filename = f"{formatted_name}_logo{default_extension}" # Append _logo
    # Use the specified static path format
    logo_url = f"/static/images/{suggested_filename}" 
    
    return logo_url, suggested_filename


# --- Modified create_organization function ---
def create_organization(db, org_name, theme_color):
    """Creates a new organization in the database with an auto-generated custom palette and logo URL."""
    try:
        # Check if the organization name already exists
        existing_org = db.query(Organization).filter(Organization.name == org_name).first()
        if existing_org:
            print(f"Error: Organization with name '{org_name}' already exists.")
            return None, None # Return None for both org and filename

        # Generate the custom palette based on the theme_color
        generated_custom_palette_json = generate_custom_palette(theme_color)
        
        # Generate the logo URL and suggested filename based on the organization name
        generated_logo_url, suggested_filename = generate_logo_url(org_name)

        # Create a new Organization object, including the logo_url
        new_org = Organization(
            name=org_name,
            theme_color=theme_color,
            custom_palette=generated_custom_palette_json,
            logo_url=generated_logo_url  # Add the generated logo_url here
        )
        db.add(new_org)
        db.commit()
        db.refresh(new_org) # Refresh to get the ID
        print(f"Organization '{org_name}' created successfully with id: {new_org.id}.")
        return new_org, suggested_filename # Return both organization and suggested filename
    except Exception as e:
        print(f"Error creating organization: {e}")
        db.rollback()
        raise


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

# --- New function to update organization theme color ---
def update_organization_theme_color(db, org_id: int, new_theme_color: str):
    """
    Updates the theme color of an existing organization and regenerates its custom palette.
    """
    try:
        organization = db.get(Organization, org_id)
        if not organization:
            print(f"Error: Organization with ID {org_id} not found.")
            return False

        # Update the theme_color
        organization.theme_color = new_theme_color
        
        # Regenerate the custom_palette based on the new theme color
        organization.custom_palette = generate_custom_palette(new_theme_color)
        
        db.add(organization)
        db.commit()
        db.refresh(organization)
        print(f"Organization '{organization.name}' (ID: {org_id}) theme color updated to {new_theme_color} and palette regenerated successfully.")
        return True
    except Exception as e:
        print(f"An unexpected error occurred during theme color update: {e}")
        db.rollback()
        return False

# --- NEW: Function to update an admin's position ---
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


def main():
    check_database_url()

    while True:
        print("\n--- Admin Setup Menu ---")
        print("1. Create a NEW organization and its first admin.")
        print("2. Create an admin for an EXISTING organization.")
        print("3. Edit theme color for an EXISTING organization.")
        print("4. Update an admin's position.") # NEW MENU OPTION
        print("5. Exit") # Updated exit option

        choice = input("Enter your choice (1, 2, 3, 4, or 5): ") # Updated prompt

        if choice == '1':
            org_name = input("Enter NEW organization name: ")
            theme_color = input("Enter NEW organization theme color (e.g., #RRGGBB, must be a hex code): ")
            if not (theme_color.startswith('#') and len(theme_color) == 7 and all(c in '0123456789abcdefABCDEF' for c in theme_color[1:])):
                print("Invalid theme color format. Please enter a valid hex code (e.g., #f0ad4e).")
                continue

            admin_email = input("Enter admin email: ")
            admin_password = getpass.getpass("Enter admin password: ")
            admin_name = input("Enter admin name (optional, default 'Admin'): ") or "Admin"
            # NEW: Prompt for position during initial admin creation
            admin_position = input("Enter admin position (e.g., President, Secretary, etc.): ")

            db = SessionLocal()
            try:
                organization, suggested_filename = create_organization(db, org_name, theme_color)
                if organization:
                    print(f"\n**Action Required:** Please upload the organization logo to your web server at the path: **{organization.logo_url}**")
                    print(f"The suggested filename for the image file is: **{suggested_filename}**")
                    # Pass position to create_admin_user
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
            # Removed break here to allow continuous use of the menu
            # If you want it to exit after this operation, uncomment the break below
            # break

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
                    print(f"ID: {org.id}, Name: {org.name}, Theme Color: {org.theme_color}, Logo URL: {org.logo_url if org.logo_url else 'N/A'}")

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
                # NEW: Prompt for position when adding admin to existing org
                admin_position = input("Enter admin position (e.g., President, Secretary, etc.): ")


                # Pass position to create_admin_user
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
            # Removed break here to allow continuous use of the menu
            # If you want it to exit after this operation, uncomment the break below
            # break
        
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
                    print(f"ID: {org.id}, Name: {org.name}, Current Theme Color: {org.theme_color}")

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
            # Removed break here to allow continuous use of the menu
            # If you want it to exit after this operation, uncomment the break below
            # break

        elif choice == '4': # NEW OPTION: Update Admin Position
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
            # Removed break here to allow continuous use of the menu
            # If you want it to exit after this operation, uncomment the break below
            # break

        elif choice == '5': # Updated exit choice
            print("Exiting setup.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.") # Updated prompt

if __name__ == "__main__":
    main()
