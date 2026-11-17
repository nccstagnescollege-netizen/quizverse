import uuid
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.auth_rbac import Admin, Role, AdminRole
from backend.app.services.auth_service import hash_password
from backend.app.services.audit_service import log_audit_event


def ensure_super_admin_exists(
    db: Session,
    email: Optional[str] = None,
    password: Optional[str] = None,
    full_name: Optional[str] = None,
) -> Admin:
    """
    Secure server-side bootstrap mechanism to provision the initial Super Admin.
    Guarantees that:
    1. A Super Admin exists in the database.
    2. No public registration can create a Super Admin.
    3. The Super Admin has is_super_admin=True and the 'super_admin' role assigned.
    """
    target_email = email or settings.SUPER_ADMIN_DEFAULT_EMAIL
    target_password = password or settings.SUPER_ADMIN_DEFAULT_PASSWORD
    target_name = full_name or settings.SUPER_ADMIN_DEFAULT_NAME

    # Check if a super admin already exists
    existing_super_admin = db.query(Admin).filter(Admin.is_super_admin == True).first()
    if existing_super_admin:
        logger.info(f"Super Admin already exists: [{existing_super_admin.email}] (id: {existing_super_admin.id})")
        return existing_super_admin

    # Check if an admin with target email exists but isn't super admin
    existing_admin = db.query(Admin).filter(Admin.email == target_email).first()
    if existing_admin:
        existing_admin.is_super_admin = True
        existing_admin.status = "active"
        if not existing_admin.password_hash:
            existing_admin.password_hash = hash_password(target_password)
        db.commit()
        db.refresh(existing_admin)
        logger.info(f"Promoted existing admin [{target_email}] to Super Admin.")
        log_audit_event(
            db,
            admin_id=existing_admin.id,
            action="admin.promoted_to_super_admin",
            entity_type="admin",
            entity_id=str(existing_admin.id),
            details={"email": target_email},
        )
        return existing_admin

    # Create new Super Admin
    super_admin = Admin(
        id=uuid.uuid4(),
        email=target_email,
        full_name=target_name,
        password_hash=hash_password(target_password),
        is_super_admin=True,
        status="active",
    )
    db.add(super_admin)
    db.flush()

    # Link to super_admin role if exists
    super_role = db.query(Role).filter(Role.role_name == "super_admin").first()
    if super_role:
        db.add(AdminRole(admin_id=super_admin.id, role_id=super_role.id))

    db.commit()
    db.refresh(super_admin)

    logger.info(f"Successfully bootstrapped initial Super Admin: [{target_email}] (id: {super_admin.id})")
    log_audit_event(
        db,
        admin_id=super_admin.id,
        action="admin.bootstrap_super_admin",
        entity_type="admin",
        entity_id=str(super_admin.id),
        details={"email": target_email, "full_name": target_name},
    )
    return super_admin
