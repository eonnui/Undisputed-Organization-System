import bcrypt
import getpass
import sys
import os
import json
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Adjust the path to correctly import from main.py and models.py
script_path = Path(__file__).resolve()
app_dir = script_path.parent
backend_dir = app_dir.parent
sys.path.insert(0, str(backend_dir))

# Now we can import directly
from app.models import Admin, Organization, User, NotificationTypeConfig, Event, BulletinBoard, Payment # Import models for type checking
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

# --- NEW: Function to display all notification type configurations ---
def display_all_notification_configs(db):
    """
    Displays all existing notification type configurations in a readable format.
    """
    try:
        configs = db.query(NotificationTypeConfig).all()
        if not configs:
            print("\nNo notification type configurations found in the database.")
            return

        print("\n" + "="*80)
        print("--- All Notification Type Configurations ---".center(80))
        print("="*80)

        for config in configs:
            print(f"\nType Name: {config.type_name}")
            print(f"  Display Name (plural): {config.display_name_plural}")
            print(f"  Group by Type Only: {config.group_by_type_only}")
            print(f"  Always Individual: {config.always_individual}")
            print(f"  Message Template (plural): {config.message_template_plural}")
            print(f"  Message Template (individual): {config.message_template_individual}")
            print(f"  Context Phrase Template: {config.context_phrase_template}")
            print(f"  Message Prefix to Strip: {config.message_prefix_to_strip}")
            print(f"  Entity Model Name: {config.entity_model_name}")
            print(f"  Entity Title Attribute: {config.entity_title_attribute}")
            print("-" * 70)
        print("\n" + "="*80)
    except Exception as e:
        print(f"An error occurred while displaying notification configurations: {e}")
    finally:
        db.close()


# --- NEW: Function to add or update notification type configuration ---
def add_notification_config(db):
    """
    Prompts the user for details to add or or update a notification type configuration.
    Automates remaining fields for new configs based on type_name.
    For existing configs, it allows interactive editing of all fields.
    """
    print("\n--- Add/Update Notification Type Configuration ---")
    type_name = input("Enter the Notification Type Name (e.g., 'past_due_payments', 'event_join'): ").strip()
    if not type_name:
        print("Notification Type Name cannot be empty.")
        return

    existing_config = db.query(NotificationTypeConfig).filter(NotificationTypeConfig.type_name == type_name).first()

    if existing_config:
        # --- UPDATE FLOW: Keep current interactive editing ---
        print(f"\nConfiguration for '{type_name}' already exists. You are now UPDATING it.")
        print("Enter new values. Press Enter to keep current value.")

        initial_display_name_plural = existing_config.display_name_plural
        initial_group_by_type_only = existing_config.group_by_type_only
        initial_always_individual = existing_config.always_individual
        initial_message_template_plural = existing_config.message_template_plural
        initial_message_template_individual = existing_config.message_template_individual
        initial_context_phrase_template = existing_config.context_phrase_template
        initial_message_prefix_to_strip = existing_config.message_prefix_to_strip
        initial_entity_model_name = existing_config.entity_model_name
        initial_entity_title_attribute = existing_config.entity_title_attribute

        # Input prompts for update (showing current, allowing override or keep)
        display_name_plural_prompt = f"Enter Display Name (plural, e.g., 'past due payments') (current: {initial_display_name_plural}): "
        display_name_plural = input(display_name_plural_prompt).strip() or initial_display_name_plural
        
        # Prompt for always_individual first to determine subsequent prompts
        always_individual_prompt = f"Always display individually (never group)? (yes/no) (current: {initial_always_individual}): "
        always_individual_input = input(always_individual_prompt).strip().lower()
        if always_individual_input == 'yes':
            always_individual = True
        elif always_individual_input == 'no':
            always_individual = False
        else:
            always_individual = initial_always_individual

        # Conditionally skip grouping-related prompts if always_individual is True
        if not always_individual:
            group_by_type_only_prompt = f"Group by type ONLY? (yes/no) (current: {initial_group_by_type_only}): "
            group_by_type_only_input = input(group_by_type_only_prompt).strip().lower()
            if group_by_type_only_input == 'yes':
                group_by_type_only = True
            elif group_by_type_only_input == 'no':
                group_by_type_only = False
            else:
                group_by_type_only = initial_group_by_type_only
        else:
            group_by_type_only = False # Force to False if always_individual

        entity_model_name_prompt = f"Enter Entity Model Name (e.g., 'User', 'Event', 'BulletinBoard') (current: {initial_entity_model_name}): "
        entity_model_name = input(entity_model_name_prompt).strip() or initial_entity_model_name
        
        entity_title_attribute_prompt = f"Enter Entity Title Attribute (e.g., 'first_name', 'title', 'name') (current: {initial_entity_title_attribute}): "
        entity_title_attribute = input(entity_title_attribute_prompt).strip() or initial_entity_title_attribute

        # Conditionally skip context_phrase_template and message_template_plural if always_individual is True
        if not always_individual:
            context_phrase_template_prompt = (
                f"Enter Context Phrase Template (for grouped messages, e.g., ' for {{entity_title}}')\n"
                f"  Available placeholders: {{entity_title}} (the title of the related entity)\n"
                f"  (current: {initial_context_phrase_template}): "
            )
            context_phrase_template = input(context_phrase_template_prompt).strip() or initial_context_phrase_template
            
            message_prefix_to_strip_prompt = f"Enter Message Prefix to Strip (e.g., 'Past Due Payments: ') (current: {initial_message_prefix_to_strip}): "
            message_prefix_to_strip = input(message_prefix_to_strip_prompt).strip() or initial_message_prefix_to_strip

            message_template_plural_prompt = (
                f"Enter Message Template (plural, for grouped messages, e.g., '{{count}} {{display_name_plural}}{{context_phrase}}: {{summary_items_with_others}}.')\n"
                f"  Available placeholders:\n"
                f"    {{count}}: total number of notifications in the group\n"
                f"    {{display_name_plural}}: the 'Display Name (plural)' you set above\n"
                f"    {{context_phrase}}: the formatted 'Context Phrase Template'\n"
                f"    {{summary_items_with_others}}: a summary of up to 3 stripped messages, plus 'X others'\n"
                f"    {{summary_items}}: a summary of up to 3 stripped messages (no 'X others')\n"
                f"  (current: {initial_message_template_plural}): "
            )
            message_template_plural = input(message_template_plural_prompt).strip() or initial_message_template_plural
        else:
            context_phrase_template = initial_context_phrase_template # Keep current or set to None/empty if not applicable
            message_prefix_to_strip = initial_message_prefix_to_strip # Still relevant for individual messages
            message_template_plural = "{message}" # Set to a dummy value, won't be used

        # Always prompt for message_template_individual
        message_template_individual_prompt = (
            f"Enter Message Template (individual, for single notifications, e.g., '{{message}}')\n"
            f"  Available placeholders:\n"
            f"    {{message}}: the original notification message (after 'Message Prefix to Strip')\n"
            f"    {{entity_title}}: the title of the related entity (e.g., bulletin post title, user name)\n"
            f"  (current: {initial_message_template_individual}): "
        )
        message_template_individual = input(message_template_individual_prompt).strip() or initial_message_template_individual


        try:
            existing_config.display_name_plural = display_name_plural
            existing_config.group_by_type_only = group_by_type_only
            existing_config.always_individual = always_individual
            existing_config.message_template_plural = message_template_plural
            existing_config.message_template_individual = message_template_individual # Set individual template
            existing_config.context_phrase_template = context_phrase_template
            existing_config.message_prefix_to_strip = message_prefix_to_strip
            existing_config.entity_model_name = entity_model_name
            existing_config.entity_title_attribute = entity_title_attribute
            db.add(existing_config)
            db.commit()
            db.refresh(existing_config)
            print(f"Notification type configuration for '{type_name}' updated successfully.")
            display_all_notification_configs(db)
        except Exception as e:
            print(f"Error updating notification type configuration: {e}")
            db.rollback()

    else:
        # --- NEW CONFIG FLOW: Now prompts for message_template_individual ---
        print(f"\nCreating NEW configuration for '{type_name}'.")
        display_name_plural = input(f"Enter Display Name (plural, e.g., 'past due payments'): ").strip()
        if not display_name_plural:
            print("Display Name (plural) cannot be empty. Aborting.")
            return

        always_individual_input = input(f"Always display individually (never group)? (yes/no, default: no): ").strip().lower()
        always_individual = True if always_individual_input == 'yes' else False

        # Conditionally skip grouping-related prompts if always_individual is True
        if not always_individual:
            group_by_type_only_input = input(f"Group by type ONLY? (yes/no, default: no): ").strip().lower()
            group_by_type_only = True if group_by_type_only_input == 'yes' else False
        else:
            group_by_type_only = False # Force to False if always_individual


        # --- AUTOMATIC INFERENCE / PROMPTS FOR REMAINING FIELDS ---
        entity_model_name = None
        entity_title_attribute = None
        context_phrase_template = None
        message_prefix_to_strip = None
        message_template_plural = None
        message_template_individual = "{message}" # Default for individual template (now prompted)

        if type_name == 'past_due_payments' or type_name == 'user_past_due' or type_name == 'member_verification':
            entity_model_name = 'User'
            entity_title_attribute = 'first_name'
            if type_name == 'past_due_payments':
                message_prefix_to_strip = 'Past Due Payments: '
            elif type_name == 'user_past_due':
                message_prefix_to_strip = 'You have past due payment items. Please check your payments page.'
            elif type_name == 'member_verification':
                message_prefix_to_strip = 'Member '
            if not always_individual: # Only set context phrase if not always individual
                context_phrase_template = " for {entity_title}"

        elif type_name == 'bulletin_like' or type_name == 'bulletin_post':
            entity_model_name = 'BulletinBoard'
            entity_title_attribute = 'title'
            if type_name == 'bulletin_like':
                message_prefix_to_strip = ' liked your bulletin post: '
                if not always_individual:
                    context_phrase_template = ' on your post "{entity_title}"'
            elif type_name == 'bulletin_post':
                message_prefix_to_strip = 'New bulletin post: '
                if not always_individual:
                    context_phrase_template = ' "{entity_title}"'

        elif type_name == 'event_join' or type_name == 'event':
            entity_model_name = 'Event'
            entity_title_attribute = 'title'
            if type_name == 'event_join':
                message_prefix_to_strip = ' joined your event: '
                if not always_individual:
                    context_phrase_template = ' for your event "{entity_title}"'
            elif type_name == 'event':
                message_prefix_to_strip = 'New event: '
                if not always_individual:
                    context_phrase_template = ' "{entity_title}"'

        elif type_name == 'payment_success':
            entity_model_name = 'Payment'
            entity_title_attribute = 'id'
            message_prefix_to_strip = 'Payment Successful: '
            if not always_individual:
                context_phrase_template = " for payment ID {entity_title}"
        
        # Determine message_template_plural based on inferred values and grouping flags
        if not always_individual: # Only set plural template if not always individual
            if display_name_plural:
                if group_by_type_only is True:
                    message_template_plural = f"{{count}} {display_name_plural}: {{summary_items_with_others}}."
                else:
                    if context_phrase_template and "{entity_title}" in (context_phrase_template or ""):
                        message_template_plural = f"{{count}} {display_name_plural}{{context_phrase}}: {{summary_items_with_others}}."
                    else:
                        message_template_plural = f"{{count}} {display_name_plural}: {{summary_items_with_others}}."
            else:
                message_template_plural = "{count} items: {summary_items_with_others}."
        else:
            message_template_plural = "{message}" # Dummy value, won't be used


        # Prompt for message_template_individual for new configs (moved up)
        message_template_individual_prompt = (
            f"Enter Message Template (individual, e.g., '{{message}}', default: '{message_template_individual}')\n"
            f"  Available placeholders:\n"
            f"    {{message}}: the original notification message (after 'Message Prefix to Strip')\n"
            f"    {{entity_title}}: the title of the related entity (e.g., bulletin post title, user name)\n"
            f"  : "
        )
        message_template_individual = input(message_template_individual_prompt).strip() or message_template_individual


        try:
            new_config = NotificationTypeConfig(
                type_name=type_name,
                display_name_plural=display_name_plural,
                group_by_type_only=group_by_type_only,
                always_individual=always_individual,
                message_template_plural=message_template_plural,
                message_template_individual=message_template_individual, # Set individual template
                context_phrase_template=context_phrase_template,
                message_prefix_to_strip=message_prefix_to_strip,
                entity_model_name=entity_model_name,
                entity_title_attribute=entity_title_attribute,
            )
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            print(f"\nNotification type configuration for '{type_name}' added successfully and automated.")
            print("\n--- New Notification Type Configuration Details ---")
            print(f"Type Name: {new_config.type_name}")
            print(f"  Display Name (plural): {new_config.display_name_plural}")
            print(f"  Group by Type Only: {new_config.group_by_type_only}")
            print(f"  Always Individual: {new_config.always_individual}")
            print(f"  Message Template (plural): {new_config.message_template_plural}")
            print(f"  Message Template (individual): {new_config.message_template_individual}")
            print(f"  Context Phrase Template: {new_config.context_phrase_template}")
            print(f"  Message Prefix to Strip: {new_config.message_prefix_to_strip}")
            print(f"  Entity Model Name: {new_config.entity_model_name}")
            print(f"  Entity Title Attribute: {new_config.entity_title_attribute}")
            print("-" * 70)

        except Exception as e:
            print(f"Error adding new notification type configuration: {e}")
            db.rollback()

# --- Main menu function ---
def main():
    check_database_url()

    while True:
        print("\n--- Admin Setup Menu ---")
        print("1. Create a NEW organization and its first admin.")
        print("2. Create an admin for an EXISTING organization.")
        print("3. Edit theme color for an EXISTING organization.")
        print("4. Update an admin's position.")
        print("5. Delete an organization and its associated admins/users.")
        print("6. Display ALL organizations, admins, and users.")
        print("7. Add/Update Notification Type Configuration.")
        print("8. Display ALL Notification Type Configurations.")
        print("9. Exit")

        choice = input("Enter your choice (1-9): ")

        db = SessionLocal()
        try:
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

                organization = create_organization(db, org_name, theme_color, primary_course_code)
                if organization:
                    admin = create_admin_user(db, admin_email, admin_password, admin_name, organization_id=organization.id, position=admin_position)
                    if admin:
                        print(f"Admin '{admin_email}' successfully linked to organization '{org_name}'.")
                    else:
                        print("Admin creation failed. Organization was created but no admin linked.")
                else:
                    print("Organization creation failed. No admin was created.")

            elif choice == '2':
                organizations = get_all_organizations(db)
                if not organizations:
                    print("No existing organizations found. Please create one first.")
                    continue

                print("\n--- Existing Organizations ---")
                for org in organizations:
                    print(f"ID: {org.id}, Name: {org.name}, Theme Color: {org.theme_color}, Primary Course: {org.primary_course_code if org.primary_course_code else 'N/A'}")

                org_id_input = input("Enter the ID of the organization to add an admin to: ")
                try:
                    selected_org_id = int(org_id_input)
                except ValueError:
                    print("Invalid organization ID. Please enter a number.")
                    continue

                selected_organization = db.get(Organization, selected_org_id)
                if not selected_organization:
                    print(f"Organization with ID {selected_org_id} not found.")
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

            elif choice == '3':
                organizations = get_all_organizations(db)
                if not organizations:
                    print("No existing organizations found.")
                    continue

                print("\n--- Existing Organizations ---")
                for org in organizations:
                    print(f"ID: {org.id}, Name: {org.name}, Current Theme Color: {org.theme_color}, Primary Course: {org.primary_course_code if org.primary_course_code else 'N/A'}")

                org_id_input = input("Enter the ID of the organization to edit its theme color: ")
                try:
                    selected_org_id = int(org_id_input)
                except ValueError:
                    print("Invalid organization ID. Please enter a number.")
                    continue

                organization_to_edit = db.get(Organization, selected_org_id)
                if not organization_to_edit:
                    print(f"Organization with ID {selected_org_id} not found.")
                    continue

                new_theme_color = input(f"Enter the NEW theme color for '{organization_to_edit.name}' (e.g., #RRGGBB): ")
                if not (new_theme_color.startswith('#') and len(new_theme_color) == 7 and all(c in '0123456789abcdefABCDEF' for c in new_theme_color[1:])):
                    print("Invalid theme color format. Please enter a valid hex code (e.g., #f0ad4e).")
                    continue

                update_organization_theme_color(db, selected_org_id, new_theme_color)

            elif choice == '4': # Update Admin Position
                admins = db.query(Admin).all()
                if not admins:
                    print("No admins found.")
                    continue

                print("\n--- Existing Admins ---")
                for admin in admins:
                    print(f"ID: {admin.admin_id}, Name: {admin.name}, Email: {admin.email}, Current Position: {admin.position if admin.position else 'N/A'}")

                admin_id_input = input("Enter the ID of the admin to update their position: ")
                try:
                    selected_admin_id = int(admin_id_input)
                except ValueError:
                    print("Invalid admin ID. Please enter a number.")
                    continue

                admin_to_edit = db.get(Admin, selected_admin_id)
                if not admin_to_edit:
                    print(f"Admin with ID {selected_admin_id} not found.")
                    continue

                new_position = input(f"Enter the NEW position for '{admin_to_edit.name}' (e.g., President, Secretary, etc.): ")
                if not new_position:
                    print("Position cannot be empty.")
                    continue

                update_admin_position(db, selected_admin_id, new_position)

            elif choice == '5': # Delete Organization
                organizations = get_all_organizations(db)
                if not organizations:
                    print("No existing organizations found.")
                    continue

                print("\n--- Existing Organizations ---")
                for org in organizations:
                    print(f"ID: {org.id}, Name: {org.name}, Primary Course: {org.primary_course_code if org.primary_course_code else 'N/A'}")

                org_id_input = input("Enter the ID of the organization to DELETE (THIS ACTION IS IRREVERSIBLE): ")
                try:
                    selected_org_id = int(org_id_input)
                except ValueError:
                    print("Invalid organization ID. Please enter a number.")
                    continue

                confirm = input(f"Are you sure you want to delete organization with ID {selected_org_id} and all its associated admins and users? Type 'yes' to confirm: ")
                if confirm.lower() == 'yes':
                    delete_organization(db, selected_org_id)
                else:
                    print("Organization deletion cancelled.")

            elif choice == '6': # Display ALL data
                display_all_data(db)
                db.close()

            elif choice == '7': # Add/Update Notification Type Configuration
                add_notification_config(db)

            elif choice == '8': # Display ALL Notification Type Configurations
                display_all_notification_configs(db)

            elif choice == '9': # Exit choice
                print("Exiting setup.")
                break
            else:
                print("Invalid choice. Please enter a number between 1 and 9.")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            db.rollback()
        finally:
            if db.is_active:
                db.close()


if __name__ == "__main__":
    main()
