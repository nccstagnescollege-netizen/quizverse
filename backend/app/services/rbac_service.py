import uuid
from typing import Set, List, Optional, Callable
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.auth_rbac import (
    Admin,
    Role,
    Permission,
    AdminRole,
    RolePermission,
    AdminQuizAssignment,
    AdminAcademicScope,
    AdminPermissionOverride,
)
from backend.app.models.quiz import Quiz
from backend.app.services.auth_service import decode_token, is_session_active, touch_session

security_bearer = HTTPBearer(auto_error=False)


def get_admin_effective_permissions(db: Session, admin: Admin) -> Set[str]:
    """
    Resolve the effective permissions for an administrator.
    Follows a strict default-deny model:
    1. If is_super_admin is True, all permissions are granted.
    2. Otherwise, starts with empty set.
    3. Adds all permissions granted through assigned roles.
    4. Adds explicitly granted permission overrides.
    5. Subtracts explicitly revoked permission overrides (revocations take absolute precedence).
    """
    if admin.is_super_admin:
        # Super admin receives all known platform permissions
        all_perms = db.query(Permission.permission_name).all()
        return {p[0] for p in all_perms}.union({"*"})

    # 1. Fetch permissions from assigned roles
    role_perms = (
        db.query(Permission.permission_name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(AdminRole, AdminRole.role_id == RolePermission.role_id)
        .filter(AdminRole.admin_id == admin.id)
        .all()
    )
    effective_permissions: Set[str] = {p[0] for p in role_perms}

    # 2. Fetch specific overrides for this admin
    overrides = (
        db.query(Permission.permission_name, AdminPermissionOverride.is_granted)
        .join(Permission, Permission.id == AdminPermissionOverride.permission_id)
        .filter(AdminPermissionOverride.admin_id == admin.id)
        .all()
    )

    # 3. Apply overrides
    for perm_name, is_granted in overrides:
        if is_granted:
            effective_permissions.add(perm_name)
        else:
            effective_permissions.discard(perm_name)

    return effective_permissions


def check_quiz_access(
    db: Session,
    admin: Admin,
    quiz_id: uuid.UUID,
    required_level: str = "viewer",
) -> bool:
    """
    Validates whether an administrator is authorized to access a specific quiz.
    - Super Admins have unrestricted access to all quizzes.
    - Quiz owners (created_by == admin.id) have unrestricted access to their own quizzes.
    - Assigned admins have access according to their access_level:
        - 'owner' grants full control.
        - 'editor' grants edit/view permissions.
        - 'viewer' grants view-only permissions.
    - Unassigned User Admins receive HTTP 403 Forbidden (Data isolation).
    """
    if admin.is_super_admin:
        return True

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return False

    # Owner has complete access
    if quiz.created_by == admin.id:
        return True

    # Check assignment
    assignment = (
        db.query(AdminQuizAssignment)
        .filter(
            AdminQuizAssignment.admin_id == admin.id,
            AdminQuizAssignment.quiz_id == quiz_id,
        )
        .first()
    )
    if not assignment:
        return False

    level_hierarchy = {"viewer": 1, "editor": 2, "owner": 3}
    assigned_rank = level_hierarchy.get(assignment.access_level, 0)
    required_rank = level_hierarchy.get(required_level, 1)

    return assigned_rank >= required_rank


def enforce_quiz_access(
    db: Session,
    admin: Admin,
    quiz_id: uuid.UUID,
    required_level: str = "viewer",
    required_permission: Optional[str] = None,
) -> Quiz:
    """
    Enforces authorization using database relationships and granular permissions.
    - Verifies quiz existence (HTTP 404 if not found).
    - Enforces permission checks (e.g. quiz.publish, examination.monitor, analytics.export).
    - Enforces database relationship: quiz ownership (quiz.created_by == admin.id) or assignment in admin_quiz_assignments.
    - Super Admins bypass ordinary restrictions.
    Raises HTTPException(403) if permission or ownership/assignment is missing.
    Returns the loaded Quiz entity.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz '{quiz_id}' not found.",
        )

    if admin.is_super_admin:
        return quiz

    # 1. Verify granular permission
    if required_permission:
        effective_perms = getattr(admin, "_effective_permissions", None)
        if effective_perms is None:
            effective_perms = get_admin_effective_permissions(db, admin)
            admin._effective_permissions = effective_perms

        if required_permission not in effective_perms and "*" not in effective_perms:
            logger.warning(
                f"Permission denied: Admin [{admin.email}] lacks required permission [{required_permission}] for quiz [{quiz_id}]"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Missing required permission '{required_permission}'.",
            )

    # 2. Verify ownership or database assignment
    if not check_quiz_access(db, admin, quiz_id, required_level=required_level):
        logger.warning(
            f"Scope denied: Admin [{admin.email}] does not possess [{required_level}] access for quiz [{quiz_id}]"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden: You do not have '{required_level}' access to this quiz.",
        )

    return quiz


def check_academic_scope(
    db: Session,
    admin: Admin,
    unit_id: Optional[uuid.UUID] = None,
    topic_id: Optional[uuid.UUID] = None,
) -> bool:
    """
    Validates whether an administrator is authorized for questions within an academic unit/topic.
    Super Admins are unrestricted.
    If scopes are configured for the admin, they must encompass the target unit or topic.
    """
    if admin.is_super_admin:
        return True

    scopes = db.query(AdminAcademicScope).filter(AdminAcademicScope.admin_id == admin.id).all()
    if not scopes:
        # If no explicit academic restrictions exist, allow access by default
        return True

    for scope in scopes:
        if unit_id and scope.unit_id == unit_id:
            return True
        if topic_id and scope.topic_id == topic_id:
            return True

    return False


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> Admin:
    """
    FastAPI dependency that extracts, verifies, and authenticates the current administrator.
    - Verifies Bearer token presence and JWT cryptographic signature.
    - Verifies session is tracked in admin_sessions and is not revoked.
    - Verifies admin account is active (rejects disabled/suspended admins).
    - Attaches effective permissions to admin._effective_permissions.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)

    admin_id_str = payload.get("sub") or payload.get("admin_id")
    token_jti = payload.get("jti")

    if not admin_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        admin_id = uuid.UUID(admin_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator ID format in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Enforce Server-Side Session Tracking & Revocation Check
    if token_jti:
        if not is_session_active(db, token_jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Administrative session has been revoked or has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        touch_session(db, token_jti)

    # 2. Retrieve Admin from database
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Enforce Account Status Check (Disabled/Suspended accounts cannot act)
    if admin.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Administrator account is {admin.status}. Access denied.",
        )

    # 4. Compute and cache effective permissions on the model instance
    admin._effective_permissions = get_admin_effective_permissions(db, admin)
    return admin


async def require_super_admin(
    current_admin: Admin = Depends(get_current_admin),
) -> Admin:
    """
    FastAPI dependency requiring the current administrator to be a Super Admin.
    Rejects ordinary User Admins with HTTP 403 Forbidden.
    """
    if not current_admin.is_super_admin:
        logger.warning(
            f"Unauthorized Super Admin access attempt by admin [{current_admin.email}] (id: {current_admin.id})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Super Administrator privilege required.",
        )
    return current_admin


def require_permission(permission_name: str) -> Callable:
    """
    FastAPI dependency factory enforcing that the authenticated administrator possesses
    the specified granular permission.
    Super Admins always pass.
    """
    async def _permission_dependency(
        current_admin: Admin = Depends(get_current_admin),
    ) -> Admin:
        if current_admin.is_super_admin:
            return current_admin

        effective_perms = getattr(current_admin, "_effective_permissions", set())
        if permission_name not in effective_perms and "*" not in effective_perms:
            logger.warning(
                f"Permission denied: Admin [{current_admin.email}] lacks required permission [{permission_name}]"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Missing required permission '{permission_name}'.",
            )
        return current_admin

    return _permission_dependency
