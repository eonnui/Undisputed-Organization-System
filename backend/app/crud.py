from sqlalchemy.orm import Session, joinedload
from . import models, schemas
from passlib.context import CryptContext
from datetime import datetime, date, timezone, timedelta
import logging
from sqlalchemy.sql import exists
from sqlalchemy import and_
from typing import Optional, Tuple, List, Dict, Any
import json
from collections import defaultdict
from fastapi import Request

logging.basicConfig(level=logging.INFO)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Organization CRUD Operations
def get_organization_by_name(db: Session, organization_name: str) -> Optional[models.Organization]:
    return db.query(models.Organization).filter(models.Organization.name == organization_name).first()

def get_organization_by_primary_course_code(db: Session, primary_course_code: str) -> Optional[models.Organization]:
    return db.query(models.Organization).filter(models.Organization.primary_course_code == primary_course_code).first()

def create_organization(db: Session, organization: schemas.OrganizationCreate) -> models.Organization:
    existing_org_by_name = get_organization_by_name(db, organization.name)
    if existing_org_by_name:
        logging.warning(f"Organization with name '{organization.name}' already exists.")
        return existing_org_by_name
    if organization.primary_course_code:
        existing_org_by_code = get_organization_by_primary_course_code(db, organization.primary_course_code)
        if existing_org_by_code:
            logging.warning(f"Organization with primary_course_code '{organization.primary_course_code}' already exists.")
            return existing_org_by_code
    custom_palette_json = generate_custom_palette(organization.theme_color)
    db_organization = models.Organization(
        name=organization.name,
        theme_color=organization.theme_color,
        custom_palette=custom_palette_json,
        logo_url=organization.logo_url,
        primary_course_code=organization.primary_course_code
    )
    db.add(db_organization)
    logging.info(f"Created organization: {organization.name} with theme: {organization.theme_color} and primary course code: {organization.primary_course_code}")
    return db_organization

# User CRUD Operations
def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    if db.query(exists().where(models.User.student_number == user.student_number)).scalar():
        existing_user = db.query(models.User).filter(models.User.student_number == user.student_number).first()
        logging.info(f"User with student_number: {user.student_number} already exists.")
        return existing_user
    hashed_password = pwd_context.hash(user.password)
    organization_id_to_assign = None
    if user.organization:
        organization_obj = get_organization_by_name(db, user.organization) or \
                           get_organization_by_primary_course_code(db, user.organization)
        if organization_obj:
            organization_id_to_assign = organization_obj.id
        else:
            logging.warning(f"Organization '{user.organization}' not found during user creation. User will be created without an assigned organization.")
    db_user = models.User(
        student_number=user.student_number,
        email=user.email,
        organization_id=organization_id_to_assign,
        first_name=user.first_name,
        last_name=user.last_name,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    logging.info(f"Created user with student_number: {user.student_number}, email: {user.email}")
    return db_user

def get_user(db: Session, identifier: str) -> Optional[models.User]:
    return db.query(models.User).filter(
        (models.User.student_number == identifier) | (models.User.email == identifier)
    ).first()

# Authentication Operations
def authenticate_user(db: Session, identifier: str, password: str) -> Optional[models.User]:
    user = get_user(db, identifier)
    if not user:
        logging.warning(f"User with identifier: {identifier} not found.")
        return None
    if not pwd_context.verify(password, user.hashed_password):
        logging.warning(f"Invalid password for user: {identifier}")
        return None
    logging.info(f"User {identifier} authenticated successfully.")
    return user

def authenticate_admin_by_email(db: Session, email: str, password: str) -> Optional[models.Admin]:
    admin = db.query(models.Admin).filter(models.Admin.email == email).first()
    if not admin:
        logging.warning(f"Admin with email: {email} not found.")
        return None
    if not pwd_context.verify(password, admin.password):
        logging.warning(f"Invalid password for admin: {email}")
        return None
    logging.info(f"Admin {email} authenticated successfully.")
    return admin

# Payment CRUD Operations
def create_payment(db: Session, user_id: int, amount: float, payment_item_id: Optional[int] = None) -> models.Payment:
    db_payment = models.Payment(
        user_id=user_id,
        amount=amount,
        payment_item_id=payment_item_id,
        status="pending",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(db_payment)
    logging.info(f"Created payment for user_id: {user_id}, amount: {amount}, payment_item_id: {payment_item_id}")
    return db_payment

def get_payment_by_id(db: Session, payment_id: int) -> Optional[models.Payment]:
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if payment:
        logging.info(f"Retrieved payment with id: {payment_id}")
    else:
        logging.warning(f"Payment with id: {payment_id} not found.")
    return payment

def update_payment(
    db: Session,
    payment_id: int,
    paymaya_payment_id: Optional[str] = None,
    status: Optional[str] = None,
    payment_item_id: Optional[int] = None,
) -> Optional[models.Payment]:
    db_payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if db_payment:
        if paymaya_payment_id is not None:
            db_payment.paymaya_payment_id = paymaya_payment_id
        if status is not None:
            db_payment.status = status
        if payment_item_id is not None:
            db_payment.payment_item_id = payment_item_id
        db_payment.updated_at = datetime.now(timezone.utc)
        logging.info(f"Updated payment with id: {payment_id}, status: {status}")
        return db_payment
    else:
        logging.warning(f"Payment with id: {payment_id} not found for update.")
        return None

def add_payment_item(
    db: Session,
    academic_year: str,
    semester: str,
    fee: float,
    user_id: int,
    due_date: Optional[date] = None,
    year_level_applicable: Optional[int] = None,
    is_past_due: bool = False,
) -> models.PaymentItem:
    db_payment_item = models.PaymentItem(
        academic_year=academic_year,
        semester=semester,
        fee=fee,
        user_id=user_id,
        due_date=due_date,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        year_level_applicable=year_level_applicable,
        is_past_due=is_past_due,
    )
    db.add(db_payment_item)
    logging.info(f"Added payment item for user {user_id} (AY: {academic_year}, Semester: {semester}, Fee: {fee})")
    return db_payment_item

def get_all_payment_items(db: Session) -> List[models.PaymentItem]:
    payment_items = db.query(models.PaymentItem).filter(models.PaymentItem.is_paid == False).all()
    logging.info(f"Retrieved all unpaid payment items. Count: {len(payment_items)}")
    return payment_items

def get_payment_item_by_id(db: Session, payment_item_id: int) -> Optional[models.PaymentItem]:
    payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if payment_item:
        logging.info(f"Retrieved payment item with id: {payment_item_id}")
    else:
        logging.warning(f"Payment item with id: {payment_item_id} not found.")
    return payment_item

def mark_payment_item_as_paid(db: Session, payment_item_id: int) -> Optional[models.PaymentItem]:
    db_payment_item = db.query(models.PaymentItem).filter(models.PaymentItem.id == payment_item_id).first()
    if db_payment_item:
        db_payment_item.is_paid = True
        db_payment_item.updated_at = datetime.now(timezone.utc)
        logging.info(f"Payment item with id: {payment_item_id} marked as paid.")
        return db_payment_item
    else:
        logging.warning(f"Payment item with id: {payment_item_id} not found for marking as paid.")
    return None

# Notification Operations
def create_notification(
    db: Session,
    message: str,
    event_identifier: str,
    organization_id: Optional[int] = None,
    user_id: Optional[int] = None,
    admin_id: Optional[int] = None,
    notification_type: Optional[str] = None,
    bulletin_post_id: Optional[int] = None,
    event_id: Optional[int] = None,
    payment_id: Optional[int] = None,
    payment_item_id: Optional[int] = None,
    verified_user_id: Optional[int] = None,
    url: Optional[str] = None
) -> Optional[models.Notification]:

    owner_filters = []

    if user_id is not None:
        owner_filters.append(models.Notification.user_id == user_id)
    if admin_id is not None:
        owner_filters.append(models.Notification.admin_id == admin_id)
    if organization_id is not None:
        owner_filters.append(models.Notification.organization_id == organization_id)
    
    if not owner_filters:
        logging.warning(f"Cannot create notification for event '{event_identifier}': No valid owner ID provided.")
        return None

    all_combined_filters = [models.Notification.event_identifier == event_identifier, and_(*owner_filters)]

    if bulletin_post_id is not None:
        all_combined_filters.append(models.Notification.bulletin_post_id == bulletin_post_id)
    if event_id is not None:
        all_combined_filters.append(models.Notification.event_id == event_id)
    if payment_id is not None:
        all_combined_filters.append(models.Notification.payment_id == payment_id)
    if payment_item_id is not None:
        all_combined_filters.append(models.Notification.payment_item_id == payment_item_id)
    if verified_user_id is not None:
        all_combined_filters.append(models.Notification.verified_user_id == verified_user_id)

    existing_notification = db.query(models.Notification).filter(and_(*all_combined_filters)).first()

    if existing_notification:
        if existing_notification.is_dismissed:
            return None
        else:
            return existing_notification
    else:
        db_notification = models.Notification(
            message=message,
            organization_id=organization_id,
            user_id=user_id,
            admin_id=admin_id,
            notification_type=notification_type,
            bulletin_post_id=bulletin_post_id,
            event_id=event_id,
            payment_id=payment_id,
            payment_item_id=payment_item_id,
            verified_user_id=verified_user_id,
            url=url,
            event_identifier=event_identifier,
            is_read=False,
            is_dismissed=False,
            created_at=datetime.utcnow()
        )
        db.add(db_notification)
        return db_notification

def mark_notification_as_dismissed_by_owner(
    db: Session,
    notification_id: int,
    user_id: Optional[int] = None,
    admin_id: Optional[int] = None,
    organization_id: Optional[int] = None
) -> Optional[models.Notification]:
    query = db.query(models.Notification).filter(models.Notification.id == notification_id)

    if user_id:
        query = query.filter(models.Notification.user_id == user_id)
    elif admin_id:
        query = query.filter(models.Notification.admin_id == admin_id)
    elif organization_id:
        query = query.filter(models.Notification.organization_id == organization_id)
    else:
        return None 

    notification_to_dismiss = query.first()

    if notification_to_dismiss:
        notification_to_dismiss.is_dismissed = True
        db.add(notification_to_dismiss) 
        db.commit()
        db.refresh(notification_to_dismiss)
        logging.info(f"Notification ID {notification_id} marked as dismissed.")
        return notification_to_dismiss
    return None

def mark_all_notifications_as_dismissed_by_owner(
    db: Session,
    user_id: Optional[int] = None,
    admin_id: Optional[int] = None,
    organization_id: Optional[int] = None
) -> int:
    query = db.query(models.Notification).filter(models.Notification.is_dismissed == False) 
    if user_id:
        query = query.filter(models.Notification.user_id == user_id)
    elif admin_id:
        query = query.filter(models.Notification.admin_id == admin_id)
    elif organization_id:
        query = query.filter(models.Notification.organization_id == organization_id)
    else:
        return 0  
    notifications_to_dismiss = query.all()
    count = 0
    for notif in notifications_to_dismiss:
        notif.is_dismissed = True
        db.add(notif)
        count += 1    
    db.commit() 
    logging.info(f"Marked {count} notifications as dismissed for owner.")
    return count

def get_notifications(
    db: Session,
    user_id: Optional[int] = None,
    admin_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    include_read: bool = False
) -> List[models.Notification]:
    notifications_query = db.query(models.Notification)

    filters = []    
    filters.append(models.Notification.is_dismissed == False)
    if user_id:
        user_org_id = db.query(models.User.organization_id).filter(models.User.id == user_id).scalar()
        filters.append(
            (models.Notification.user_id == user_id) |
            (
                (models.Notification.organization_id == user_org_id) &
                models.Notification.user_id.is_(None) &
                models.Notification.admin_id.is_(None)
            )
        )
    elif admin_id:
        admin_org_ids = [
            org.id for org in db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first().organizations
        ] if db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first() else []
        filters.append(
            (models.Notification.admin_id == admin_id) |
            (
                (models.Notification.organization_id.in_(admin_org_ids)) &
                models.Notification.user_id.is_(None) &
                models.Notification.admin_id.is_(None)
            )
        )
    elif organization_id:
        filters.append(
            (models.Notification.organization_id == organization_id) &
            models.Notification.user_id.is_(None) &
            models.Notification.admin_id.is_(None)
        )
    else:       
        return []
    
    if not include_read: 
        filters.append(models.Notification.is_read == False)
    if filters:
        notifications_query = notifications_query.filter(*filters)
         
    notifications = notifications_query.order_by(models.Notification.created_at.desc()).all()
    return notifications

def get_all_notification_configs_as_map(db: Session) -> Dict[str, Dict[str, Any]]:
    notification_configs = db.query(models.NotificationTypeConfig).all()
    return {
        config.type_name: {
            "group_by_type_only": config.group_by_type_only,
            "display_name_plural": config.display_name_plural,
            "message_template_plural": config.message_template_plural,
            "entity_model_name": config.entity_model_name,
            "entity_title_attribute": config.entity_title_attribute,
            "context_phrase_template": config.context_phrase_template,
            "message_prefix_to_strip": config.message_prefix_to_strip,
            "always_individual": config.always_individual,
        } for config in notification_configs
    }

def fetch_dynamic_entity_titles(
    db_session: Session,
    dynamic_entity_ids_to_fetch: defaultdict,
    config_map_local: dict
) -> Dict[str, str]:
    dynamic_entity_titles_local = {}
    pk_column_map = {
        "Event": models.Event.event_id,
        "BulletinBoard": models.BulletinBoard.post_id,
        "User": models.User.id,
        "Organization": models.Organization.id,
        "Payment": models.Payment.id,
        "PaymentItem": models.PaymentItem.id,
        "Expense": models.Expense.id,
        "Admin": models.Admin.admin_id,
    }
    for model_name, entity_ids in dynamic_entity_ids_to_fetch.items():
        if not entity_ids:
            continue
        model_class = getattr(models, model_name, None)
        pk_column = pk_column_map.get(model_name)
        if not model_class or not pk_column:
            logging.warning(f"Skipping entity fetch for unknown model: {model_name} or missing PK column.")
            continue
        entities = db_session.query(model_class).filter(pk_column.in_(list(entity_ids))).all()
        for entity in entities:
            entity_key = getattr(entity, pk_column.key)
            determined_title_attribute = None
            for cfg_details in config_map_local.values():
                if cfg_details.get("entity_model_name") == model_name and cfg_details.get("entity_title_attribute"):
                    determined_title_attribute = cfg_details["entity_title_attribute"]
                    break
            if not determined_title_attribute:
                if model_name == "User" and hasattr(entity, "first_name") and hasattr(entity, "last_name"):
                    dynamic_entity_titles_local[f"{model_name}_{entity_key}"] = f"{entity.first_name} {entity.last_name}"
                    continue
                elif hasattr(entity, "name"):
                    determined_title_attribute = "name"
                elif hasattr(entity, "title"):
                    determined_title_attribute = "title"
                elif hasattr(entity, "description"):
                    determined_title_attribute = "description"
            if determined_title_attribute and hasattr(entity, determined_title_attribute):
                dynamic_entity_titles_local[f"{model_name}_{entity_key}"] = getattr(entity, determined_title_attribute)
            else:
                dynamic_entity_titles_local[f"{model_name}_{entity_key}"] = f"Unknown {model_name} (ID: {entity_key})"
    return dynamic_entity_titles_local

def process_and_format_notifications(db: Session, raw_notifications: list, config_map: dict) -> list:
    individual_notifications_always = []
    notifications_for_grouping = defaultdict(lambda: {"count": 0, "latest_notification": None, "notifications": []})
    dynamic_entity_ids_to_fetch = defaultdict(set)

    for notification in raw_notifications:
        config = config_map.get(notification.notification_type)
        
        if notification.bulletin_post_id and config and config.get("entity_model_name") == "BulletinBoard":
            dynamic_entity_ids_to_fetch["BulletinBoard"].add(notification.bulletin_post_id)
        elif notification.event_id and config and config.get("entity_model_name") == "Event":
            dynamic_entity_ids_to_fetch["Event"].add(notification.event_id)
        elif notification.payment_id and config and config.get("entity_model_name") == "Payment":
            dynamic_entity_ids_to_fetch["Payment"].add(notification.payment_id)
        elif notification.payment_item_id and config and config.get("entity_model_name") == "PaymentItem":
            dynamic_entity_ids_to_fetch["PaymentItem"].add(notification.payment_item_id)
        elif notification.verified_user_id and config and config.get("entity_model_name") == "User":
            dynamic_entity_ids_to_fetch["User"].add(notification.verified_user_id)

        if not config or config.get("always_individual"):
            individual_notifications_always.append(notification)
            continue

        grouping_key_parts = [notification.notification_type]
        if not config.get("group_by_type_only"):
            if notification.bulletin_post_id:
                grouping_key_parts.append(f"bulletin_post_{notification.bulletin_post_id}")
            elif notification.event_id:
                grouping_key_parts.append(f"event_{notification.event_id}")
            elif notification.payment_id:
                grouping_key_parts.append(f"payment_{notification.payment_id}")
            elif notification.payment_item_id:
                grouping_key_parts.append(f"payment_item_{notification.payment_item_id}")
            elif notification.verified_user_id:
                grouping_key_parts.append(f"verified_user_{notification.verified_user_id}")
            if not (notification.bulletin_post_id or notification.event_id or notification.payment_id or notification.payment_item_id or notification.verified_user_id):
                if notification.user_id:
                    grouping_key_parts.append(f"user_{notification.user_id}")
                elif notification.admin_id:
                    grouping_key_parts.append(f"admin_{notification.admin_id}")
                elif notification.organization_id:
                    grouping_key_parts.append(f"org_{notification.organization_id}")

        grouping_key = tuple(grouping_key_parts)

        notifications_for_grouping[grouping_key]["notifications"].append(notification)
        
        current_created_at = notification.created_at
        if not isinstance(current_created_at, datetime):
            try:    
                current_created_at = datetime.fromisoformat(current_created_at) if isinstance(current_created_at, str) else datetime.min
            except ValueError:
                current_created_at = datetime.min
        
        latest_notif_in_group = notifications_for_grouping[grouping_key]["latest_notification"]
        if latest_notif_in_group is None or current_created_at > (latest_notif_in_group.created_at if isinstance(latest_notif_in_group.created_at, datetime) else datetime.min):
            notifications_for_grouping[grouping_key]["latest_notification"] = notification

    dynamic_entity_titles = fetch_dynamic_entity_titles(db, dynamic_entity_ids_to_fetch, config_map)
    final_notifications_data = []
    
    for individual_notif in sorted(individual_notifications_always, key=lambda n: n.created_at, reverse=True):
        try:
            created_at_iso = individual_notif.created_at.isoformat()
        except AttributeError:
            logging.warning(f"Notification ID {individual_notif.id} has invalid created_at format: {individual_notif.created_at}. Skipping.")
            continue
        final_notifications_data.append({
            "id": individual_notif.id,
            "message": individual_notif.message,
            "url": individual_notif.url,
            "notification_type": individual_notif.notification_type,
            "created_at": created_at_iso,
            "is_read": individual_notif.is_read, 
        })

    for key, value in notifications_for_grouping.items():
        count = len(value["notifications"])
        latest_notif = value["latest_notification"]
        notifications_in_group = value["notifications"]

        if not latest_notif:
            logging.warning(f"Skipping empty group for key: {key}")
            continue        
        
        group_is_read = all(n.is_read for n in notifications_in_group) 
        
        type_config = config_map.get(key[0])

        if count < 4:            
            sorted_individual_notifications = sorted(notifications_in_group, key=lambda n: n.created_at, reverse=True)
            for individual_notif in sorted_individual_notifications:
                try:
                    created_at_iso = individual_notif.created_at.isoformat()
                except AttributeError:
                    logging.warning(f"Notification ID {individual_notif.id} in group has invalid created_at format: {individual_notif.created_at}. Skipping.")
                    continue
                final_notifications_data.append({
                    "id": individual_notif.id,
                    "message": individual_notif.message,  
                    "url": individual_notif.url,
                    "notification_type": individual_notif.notification_type,
                    "created_at": created_at_iso,
                    "is_read": individual_notif.is_read, 
                })
        else:            
            formatted_message = _format_grouped_notification_message(
                count, latest_notif, notifications_in_group, type_config, dynamic_entity_titles, key
            )
            try:
                created_at_iso = latest_notif.created_at.isoformat()
            except AttributeError:
                logging.warning(f"Latest notification in group {key} has invalid created_at format: {latest_notif.created_at}. Skipping.")
                continue
            group_notification_ids = [n.id for n in notifications_in_group]

            final_notifications_data.append({
                "id": latest_notif.id, 
                "message": formatted_message,
                "url": latest_notif.url,
                "notification_type": latest_notif.notification_type,
                "created_at": created_at_iso,
                "is_read": group_is_read,
                "group_ids": group_notification_ids, 
            })

    final_notifications_data.sort(key=lambda x: x['created_at'], reverse=True)
    logging.info(f"Finished processing notifications. Total formatted: {len(final_notifications_data)}")
    return final_notifications_data

def _format_grouped_notification_message(
    count: int,
    latest_notif: models.Notification,
    notifications_in_group: List[models.Notification],
    type_config: Dict[str, Any],
    dynamic_entity_titles: Dict[str, str],
    grouping_key: Tuple[str, ...]
) -> str:
    notification_type = grouping_key[0]
    
    entity_identifier_part = grouping_key[1] if len(grouping_key) > 1 else None
    entity_id = None
    model_name_from_grouping = None
    if entity_identifier_part and '_' in entity_identifier_part:
        parts = entity_identifier_part.split('_')
        if len(parts) >= 2:
            model_prefix = parts[0]
            try:
                entity_id = int(parts[-1])
                if model_prefix == "bulletin_post": model_name_from_grouping = "BulletinBoard"
                elif model_prefix == "event": model_name_from_grouping = "Event"
                elif model_prefix == "payment": model_name_from_grouping = "Payment"
                elif model_prefix == "payment_item": model_name_from_grouping = "PaymentItem"
                elif model_prefix == "verified_user": model_name_from_grouping = "User"
            except ValueError:
                pass

    base_display_name = type_config.get("display_name_plural") or notification_type.replace('_', ' ').lower()
    context_phrase = ""

    if entity_id is not None and model_name_from_grouping:
        model_name = model_name_from_grouping
        fetched_title = dynamic_entity_titles.get(f"{model_name}_{entity_id}")
        if fetched_title:
            if type_config.get("context_phrase_template"):
                try:
                    context_phrase = type_config["context_phrase_template"].format(entity_title=fetched_title)
                except KeyError:
                    context_phrase = f" for {fetched_title}"
            else:
                context_phrase = f" for {fetched_title}"

    MAX_CHARS_IN_SUMMARY = 60
    unique_messages = list(set([n.message for n in notifications_in_group]))
    summary_items_list = []
    for msg in unique_messages[:3]:
        if type_config.get("message_prefix_to_strip"):
            prefix = type_config["message_prefix_to_strip"]
            if msg.startswith(prefix):
                msg = msg[len(prefix):].strip()
        processed_msg = msg[0].upper() + msg[1:] if msg else ""
        truncated_msg = (processed_msg[:MAX_CHARS_IN_SUMMARY] + '...') if len(processed_msg) > MAX_CHARS_IN_SUMMARY else processed_msg
        summary_items_list.append(truncated_msg)
    items_list_str = ""
    if len(summary_items_list) == 1:
        items_list_str = summary_items_list[0]
    elif len(summary_items_list) == 2:
        items_list_str = f"{summary_items_list[0]} and {summary_items_list[1]}"
    elif len(summary_items_list) > 2:
        items_list_str = f"{', '.join(summary_items_list[:-1])}, and {summary_items_list[-1]}"
    remaining_count = max(0, len(unique_messages) - len(summary_items_list))
    s_suffix = "s" if remaining_count > 1 else ""
    summary_items_with_others = items_list_str
    if remaining_count > 0:
        if items_list_str:
            summary_items_with_others += f" and {remaining_count} other{s_suffix}"
        else:
            summary_items_with_others = f"{remaining_count} other{s_suffix}"
    template_vars = {
        "count": count,
        "display_name_plural": base_display_name,
        "context_phrase": context_phrase,
        "summary_items": items_list_str,
        "summary_items_with_others": summary_items_with_others,
        "remaining_count": remaining_count,
        "s_suffix": s_suffix
    }
    if type_config.get("message_template_plural"):
        try:
            return type_config["message_template_plural"].format(**template_vars)
        except KeyError:
            logging.warning(f"Missing template variables for plural notification type '{notification_type}'. Using fallback message.")
            return f"{count} {base_display_name}{context_phrase}: {summary_items_with_others}."
    else:
        return f"{count} {base_display_name}{context_phrase}: {summary_items_with_others}."

def mark_notification_as_read(db: Session, notification_id: int) -> Optional[models.Notification]:     
    db_notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if db_notification:
        db_notification.is_read = True
        db_notification.read_at = datetime.utcnow()
        db.add(db_notification)
        logging.info(f"Notification with id: {notification_id} marked as read.")
        return db_notification
    else:
        logging.warning(f"Notification with id: {notification_id} not found for marking as read.")
    return None

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb_color: Tuple[int, int, int]) -> str:
    return '#%02x%02x%02x' % rgb_color

def adjust_rgb_lightness(rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    r, g, b = rgb
    r = int(max(0, min(255, r * factor)))
    g = int(max(0, min(255, g * factor)))
    b = int(max(0, min(255, b * factor)))
    return (r, g, b)

def get_contrast_text_color(bg_hex: str) -> str:
    r, g, b = hex_to_rgb(bg_hex)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"

def generate_custom_palette(theme_color_hex: str) -> str:
    base_palette = {
        "--org-bg-color": "#fdf5f5", "--org-login-bg": "#5c1011", "--org-button-bg": "#9a1415",
        "--org-button-text": "#FFFFFF", "--org-hover-effect": "#7a1012", "--org-accent-light": "#d32f2f",
        "--org-accent-dark": "#5c0b0b", "--org-highlight": "#ffebee", "--org-text-primary": "#212121",
        "--org-text-secondary": "#757575", "--org-text-inverse": "#FFFFFF", "--org-hover-dark": "#424242",
        "--org-hover-accent": "#b71c1c", "--org-focus-border": "transparent", "--org-success": "#4CAF50",
        "--org-error": "#F44336", "--org-warning": "#FFC107", "--org-info": "#2196F3",
        "--org-bg-secondary": "#FFFFFF", "--org-bg-dark": "#1a1a1a", "--org-border-light": "transparent",
        "--org-border-medium": "transparent", "--org-nav-item-bg": "transparent",
        "--org-nav-item-hover-bg": "rgba(154, 20, 21, 0.05)", "--org-nav-item-selected-bg":"#a83232", "--org-nav-selected-border-color": "#a83232",
        "--org-sidebar-bg-color": "#a83232", "--org-sidebar-border-color": "transparent",
        "--org-logo-border-color": "transparent", "--org-nav-icon-color": "#FFFFFF",
        "--org-nav-hover-accent-color": "#fdf5f5", "--org-top-bar-border-color": "transparent", "--org-menu-button-hover-bg": "rgba(0, 0, 0, 0.05)",
        "--org-profile-pic-border-color": "transparent", "--org-dropdown-bg": "#FFFFFF",
        "--org-dropdown-border": "transparent", "--org-dropdown-item-hover-bg": "#f5f5f5",
        "--org-dashboard-bg-color": "#fdf5f5", "--org-dashboard-title-color": "#5c0b0b",
        "--org-shadow-base-rgb": "0, 0, 0", "--org-card-bg": "#FFFFFF", "--org-announcement-card-bg": "#fefefe",
        "--org-dashboard-accent-primary": "#d32f2f", "--org-announcement-text-color": "#212121",
        "--org-announcement-meta-color": "#757575", "--org-view-details-hover": "#b71c1c",
        "--org-event-placeholder-color": "#9e9e9e", "--org-faq-border-color": "transparent",
        "--org-faq-item-bg": "#fefefe", "--org-faq-question-hover-bg": "#f5f5f5",
        "--org-faq-answer-color": "#424242", "--org-empty-state-color": "#9e9e9e",
        "--org-empty-state-bg": "#fefefe", "--org-post-card-border": "transparent",
        "--org-profile-image-bg": "#e0e0e0", "--org-post-info-color": "#5a5a5a",
        "--org-post-date-color": "#9e9e9e", "--org-post-content-color": "#333333",
        "--org-post-actions-color": "#757575", "--org-heart-hover-color": "#e57373",
        "--org-heart-button-color": "#e53935", "--org-pinned-bg": "#FFC107", "--org-event-meta-color": "#757575",
        "--org-event-description-color": "#424242", "--org-event-item-border": "transparent",
        "--org-event-item-hover-bg": "#f5f5f5", "--org-event-tag-bg": "#ffebee",
        "--org-event-tag-text": "#b71c1c", "--org-academic-tag-bg": "#fbe9e7",
        "--org-academic-tag-text": "#c62828", "--org-sports-tag-bg": "#e8f5e9",
        "--org-sports-tag-text": "#388e3c", "--org-arts-tag-bg": "#fffde7",
        "--org-arts-tag-text": "#f9a825", "--org-music-tag-bg": "#ffecb3",
        "--org-music-tag-text": "#f57f17", "--org-esports-tag-bg": "#e0f7fa",
        "--org-esports-tag-text": "#00838f", "--org-cultural-tag-bg": "#f3e5f5",
        "--org-cultural-tag-text": "#7b1fa2", "--org-join-btn-bg": "#43a047",
        "--org-join-btn-hover-bg": "#388e3c", "--org-leave-btn-bg": "#e53935",
        "--org-leave-btn-hover-bg": "#d32f2f", "--org-event-full-bg": "#9e9e9e",
        "--org-event-full-text": "#FFFFFF", "--org-join-button-bg": "#43a047",
        "--org-join-button-hover-bg": "#45a049", "--org-leave-button-bg": "#f44336",
        "--org-leave-button-hover-bg": "#d32f2f", "--org-full-button-bg": "#bdbdbd",
        "--org-full-button-text": "#424242", "--org-participants-count-color": "#757575",
        "--org-payments-container-bg": "#fdf5f5", "--org-border-light-darker": "transparent",
        "--org-text-primary-darker": "#000000", "--org-table-header-bg-payments": "#fbc4cb",
        "--org-table-header-text-payments": "#333333", "--org-table-data-text": "#333333",
        "--org-background-light-alt-darker": "#fefafa", "--org-status-unpaid-bg": "#ffebee",
        "--org-status-unpaid-text": "#b71c1c", "--org-error-border": "transparent",
        "--org-pay-button-bg-payments": "#e53935", "--org-pay-button-hover-bg-payments": "#d32f2f",
        "--org-standby-button-bg-payments": "#bdbdbd", "--org-button-disabled-text-darker": "#757575",
        "--org-past-due-bg": "#ffebee", "--org-past-due-text": "#b71c1c", "--org-past-due-hover-bg": "#ffcdd2",
        "--org-past-due-hover-text": "#b71c1c", "--org-surface": "#FFFFFF", "--org-radius-lg": "12px",
        "--org-shadow-md": "0 4px 10px rgba(0, 0, 0, 0.12)", "--org-transition": "all 0.3s ease-in-out",
        "--org-shadow-lg": "0 6px 15px rgba(0, 0, 0, 0.18)", "--org-primary": "#9a1415",
        "--org-radius-md": "8px", "--org-shadow-sm": "0 2px 5px rgba(0, 0, 0, 0.08)",
        "--org-text-light": "#FFFFFF", "--org-secondary-color": "#f5f5f5", "--org-primary-light": "#ffcdd2",
        "--org-primary-hover": "#b71c1c", "--org-settings-section-bg": "#f5f5f5",
        "--org-settings-title-color": "#212121", "--org-button-group-button-update-bg": "#a83232",
        "--org-button-group-button-update-hover-bg": "#862828", "--org-button-group-button-clear-bg": "#FFFFFF",
        "--org-button-group-button-clear-hover-bg": "transparent", "--org-profile-picture-border": "transparent",
        "--org-change-profile-pic-bg": "#a83232", "--org-change-profile-pic-hover-bg": "#862828",
        "--org-student-info-section-bg": "#FFFFFF", "--org-verified-bg": "#4CAF50",
        "--org-verified-text": "#FFFFFF", "--org-unverified-bg": "#FFC107",
        "--org-unverified-text": "#212121", "--org-registration-form-section-bg": "#FFFFFF",
        "--org-edit-icon-bg": "#FFFFFF", "--org-edit-icon-hover-bg": "#f5f5f5",
        "--org-read-only-input-bg": "#fdf5f5", "--org-read-only-input-text": "#757575",
        "--org-form-group-label-color": "#212121", "--org-form-group-input-border": "transparent",
        "--org-form-group-input-focus-border": "transparent"
    }
    custom_palette = base_palette.copy()
    theme_rgb = hex_to_rgb(theme_color_hex)
    dark_theme_rgb = adjust_rgb_lightness(theme_rgb, 0.7)
    darker_theme_rgb = adjust_rgb_lightness(theme_rgb, 0.5)
    light_theme_rgb = adjust_rgb_lightness(theme_rgb, 1.2)
    lighter_theme_rgb = adjust_rgb_lightness(theme_rgb, 1.6)
    mid_dark_theme_rgb = adjust_rgb_lightness(theme_rgb, 0.85) 
    mid_dark_theme_hex = rgb_to_hex(mid_dark_theme_rgb)
    dark_theme_hex = rgb_to_hex(dark_theme_rgb)
    darker_theme_hex = rgb_to_hex(darker_theme_rgb)
    light_theme_hex = rgb_to_hex(light_theme_rgb)
    lighter_theme_hex = rgb_to_hex(lighter_theme_rgb)
    whiteness_factor = .9
    very_light_bg_rgb = (
        int(theme_rgb[0] * (1 - whiteness_factor) + 255 * whiteness_factor),
        int(theme_rgb[1] * (1 - whiteness_factor) + 255 * whiteness_factor),
        int(theme_rgb[2] * (1 - whiteness_factor) + 255 * whiteness_factor)
    )
    very_light_bg_rgb = (
        max(0, min(255, very_light_bg_rgb[0])),
        max(0, min(255, very_light_bg_rgb[1])),
        max(0, min(255, very_light_bg_rgb[2]))
    )
    very_light_bg_hex = rgb_to_hex(very_light_bg_rgb)
    custom_palette["--org-bg-color"] = very_light_bg_hex
    custom_palette["--org-secondary-color"] = very_light_bg_hex
    custom_palette["--org-dashboard-bg-color"] = very_light_bg_hex
    custom_palette["--org-payments-container-bg"] = very_light_bg_hex
    custom_palette["--org-nav-hover-accent-color"] = very_light_bg_hex
    custom_palette["--org-settings-section-bg"] = very_light_bg_hex
    custom_palette["--org-read-only-input-bg"] = very_light_bg_hex
    button_text_color = get_contrast_text_color(theme_color_hex)
    custom_palette["--org-primary"] = theme_color_hex
    custom_palette["--org-button-bg"] = theme_color_hex
    custom_palette["--org-hover-effect"] = dark_theme_hex
    custom_palette["--org-accent-light"] = light_theme_hex
    custom_palette["--org-accent-dark"] = darker_theme_hex
    custom_palette["--org-hover-accent"] = dark_theme_hex
    custom_palette["--org-primary-hover"] = dark_theme_hex
    custom_palette["--org-primary-light"] = lighter_theme_hex
    custom_palette["--org-dashboard-accent-primary"] = light_theme_hex
    custom_palette["--org-login-bg"] = darker_theme_hex
    custom_palette["--org-sidebar-bg-color"] = theme_color_hex
    custom_palette["--org-nav-item-hover-bg"] = f"rgba({theme_rgb[0]}, {theme_rgb[1]}, {theme_rgb[2]}, 0.05)"
    custom_palette["--org-nav-item-selected-bg"] = mid_dark_theme_hex
    custom_palette["--org-nav-selected-border-color"] = lighter_theme_hex
    custom_palette["--org-nav-icon-color"] = button_text_color
    custom_palette["--org-button-text"] = "#FFFFFF"
    custom_palette["--org-dashboard-title-color"] = darker_theme_hex
    custom_palette["--org-text-light"] = button_text_color
    custom_palette["--org-event-tag-bg"] = lighter_theme_hex
    custom_palette["--org-event-tag-text"] = dark_theme_hex  
    custom_palette["--org-table-header-bg-payments"] = lighter_theme_hex
    custom_palette["--org-table-header-text-payments"] = get_contrast_text_color(lighter_theme_hex)
    custom_palette["--org-settings-title-color"] = darker_theme_hex
    custom_palette["--org-button-group-button-update-bg"] = theme_color_hex
    custom_palette["--org-button-group-button-update-hover-bg"] = darker_theme_hex
    custom_palette["--org-change-profile-pic-bg"] = dark_theme_hex
    custom_palette["--org-change-profile-pic-hover-bg"] = darker_theme_hex
    custom_palette["--org-highlight"] = very_light_bg_hex
    custom_palette["--org-primary"] = theme_color_hex
    return json.dumps(custom_palette, indent=2)

def verify_password(plain_password: str, hashed_password: str) -> bool:   
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:   
    return pwd_context.hash(password)

def create_password_reset_token(db: Session, user_id: int, token: str, expiration: datetime):
    db_token = models.PasswordResetToken(user_id=user_id, token=token, expiration_time=expiration)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token

def get_password_reset_token_by_token(db: Session, token: str):
    return db.query(models.PasswordResetToken).filter(models.PasswordResetToken.token == token).first()

def delete_password_reset_token(db: Session, token_id: int):
    db_token = db.query(models.PasswordResetToken).filter(models.PasswordResetToken.id == token_id).first()
    if db_token:
        db.delete(db_token)
        db.commit()
        return True
    return False

def update_user_password(db: Session, user_id: int, new_password: str):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.hashed_password = get_password_hash(new_password) 
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    return None

# Function to create an admin log entry
async def create_admin_log(
    db: Session,
    admin_id: int,
    action_type: str,
    description: str,
    request: Request,
    organization_id: Optional[int] = None,
    target_entity_type: Optional[str] = None,
    target_entity_id: Optional[int] = None,
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Calculate current time in PH timezone (UTC+8)
    utc_now = datetime.utcnow()
    ph_time = utc_now + timedelta(hours=8)

    db_admin_log = models.AdminLog(
        admin_id=admin_id,
        organization_id=organization_id,
        action_type=action_type,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        timestamp=ph_time # Assign the calculated PH time
    )
    db.add(db_admin_log)
    db.commit() # Re-added db.commit()
    db.refresh(db_admin_log) # Re-added db.refresh()
    return db_admin_log

# Function to retrieve admin logs with filtering
def get_admin_logs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    admin_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    action_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search_query: Optional[str] = None
) -> List[schemas.AdminLog]:
    query = db.query(models.AdminLog).join(models.Admin)
    if admin_id:
        query = query.filter(models.AdminLog.admin_id == admin_id)
    if organization_id:
        query = query.filter(models.AdminLog.organization_id == organization_id)
    if action_type:
        query = query.filter(models.AdminLog.action_type == action_type)
    if start_date:
        query = query.filter(models.AdminLog.timestamp >= start_date)
    if end_date:
        query = query.filter(models.AdminLog.timestamp < end_date + timedelta(days=1))
    if search_query:
        query = query.filter(models.AdminLog.description.ilike(f"%{search_query}%"))
    
    query = query.options(
        joinedload(models.AdminLog.admin),
        joinedload(models.AdminLog.organization)
    )

    logs = query.order_by(models.AdminLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    formatted_logs = []
    for log in logs:
        admin_name = f"{log.admin.first_name} {log.admin.last_name}" if log.admin and log.admin.first_name and log.admin.last_name else log.admin.email if log.admin else None
        organization_name = log.organization.name if log.organization else None
        
        log_dict = log.__dict__.copy()
        log_dict["admin_name"] = admin_name
        log_dict["organization_name"] = organization_name
        # Exclude SQLAlchemy internal state from being passed to Pydantic model
        log_dict.pop('_sa_instance_state', None) 
        formatted_logs.append(schemas.AdminLog(**log_dict))
    
    return formatted_logs
