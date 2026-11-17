import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.core.database import get_db
from backend.app.models.auth_rbac import (
    Admin,
    Role,
    Permission,
    AdminRole,
    RolePermission,
    AdminQuizAssignment,
    AdminPermissionOverride,
)
from backend.app.models.security_audit import AuditLog
from backend.app.models.quiz import Quiz
from backend.app.schemas.admin_management import (
    CreateAdminRequest,
    UpdateAdminRequest,
    AdminDetailResponse,
    AdminListResponse,
    BatchPermissionOverridesRequest,
    QuizAssignmentRequest,
    RoleResponse,
    CreateRoleRequest,
    PermissionResponse,
    AuditLogResponse,
)
from backend.app.services.auth_service import (
    hash_password,
    revoke_all_admin_sessions,
)
from backend.app.services.rbac_service import (
    require_super_admin,
    get_admin_effective_permissions,
)
from backend.app.services.audit_service import log_audit_event

router = APIRouter()


def _format_admin_detail(db: Session, admin: Admin) -> AdminDetailResponse:
    roles = [r.role_name for r in admin.roles] if admin.roles else []
    permissions = sorted(list(get_admin_effective_permissions(db, admin)))

    overrides = [
        {
            "permission_name": o.permission.permission_name if o.permission else str(o.permission_id),
            "is_granted": o.is_granted,
        }
        for o in (admin.permission_overrides or [])
    ]

    assignments = [
        {
            "quiz_id": str(a.quiz_id),
            "access_level": a.access_level,
        }
        for a in (admin.quiz_assignments or [])
    ]

    return AdminDetailResponse(
        id=admin.id,
        email=admin.email,
        full_name=admin.full_name,
        status=admin.status,
        is_super_admin=admin.is_super_admin,
        roles=roles,
        permissions=permissions,
        overrides=overrides,
        quiz_assignments=assignments,
        created_at=admin.created_at,
        last_login_at=admin.last_login_at,
    )


@router.get("/admins", response_model=AdminListResponse, summary="List administrators")
async def list_admins(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    List all platform administrators (Super Admin restricted).
    """
    admins = db.query(Admin).order_by(Admin.created_at.desc()).all()
    formatted = [_format_admin_detail(db, a) for a in admins]
    return AdminListResponse(admins=formatted, total=len(formatted))


@router.post("/admins", response_model=AdminDetailResponse, status_code=status.HTTP_201_CREATED, summary="Create User Admin")
async def create_admin(
    payload: CreateAdminRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Super Admin endpoint to provision a new User Admin.
    Strictly forbids creating additional Super Admins via the API.
    """
    # Check for existing email
    existing = db.query(Admin).filter(Admin.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Administrator with email '{payload.email}' already exists.",
        )

    # Forbid assigning super_admin role through this endpoint
    if "super_admin" in payload.role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot provision Super Admin accounts via the user management API.",
        )

    new_admin = Admin(
        id=uuid.uuid4(),
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_super_admin=False,  # strictly False
        status="active",
    )
    db.add(new_admin)
    db.flush()

    # Assign roles
    for r_name in payload.role_names:
        role = db.query(Role).filter(Role.role_name == r_name).first()
        if role:
            db.add(AdminRole(admin_id=new_admin.id, role_id=role.id))

    db.commit()
    db.refresh(new_admin)

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="admin.create_user_admin",
        entity_type="admin",
        entity_id=str(new_admin.id),
        details={"email": new_admin.email, "roles": payload.role_names},
    )

    return _format_admin_detail(db, new_admin)


@router.get("/admins/{admin_id}", response_model=AdminDetailResponse, summary="Get administrator details")
async def get_admin_detail(
    admin_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found.")
    return _format_admin_detail(db, admin)


@router.put("/admins/{admin_id}", response_model=AdminDetailResponse, summary="Update administrator")
async def update_admin(
    admin_id: uuid.UUID,
    payload: UpdateAdminRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found.")

    if admin.is_super_admin and admin.id == current_admin.id and payload.status == "disabled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own active Super Administrator account.",
        )

    if payload.full_name is not None:
        admin.full_name = payload.full_name
    if payload.status is not None:
        admin.status = payload.status
        if payload.status == "disabled":
            revoke_all_admin_sessions(db, admin.id, current_admin.id)

    if payload.role_names is not None:
        # Clear existing non-super roles and reassign
        db.query(AdminRole).filter(AdminRole.admin_id == admin.id).delete()
        for r_name in payload.role_names:
            if r_name == "super_admin" and not admin.is_super_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot elevate to super_admin role via standard role update.",
                )
            role = db.query(Role).filter(Role.role_name == r_name).first()
            if role:
                db.add(AdminRole(admin_id=admin.id, role_id=role.id))

    db.commit()
    db.refresh(admin)

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="admin.updated",
        entity_type="admin",
        entity_id=str(admin.id),
        details={"status": admin.status, "roles": payload.role_names},
    )

    return _format_admin_detail(db, admin)


@router.post("/admins/{admin_id}/disable", summary="Disable administrator account")
async def disable_admin(
    admin_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Disable an administrator account and immediately revoke all active sessions.
    """
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found.")

    if admin.id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable yourself.")

    admin.status = "disabled"
    revoked_count = revoke_all_admin_sessions(db, admin.id, current_admin.id)
    db.commit()

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="admin.account_disabled",
        entity_type="admin",
        entity_id=str(admin.id),
        details={"revoked_sessions": revoked_count},
    )

    return {
        "success": True,
        "message": f"Administrator '{admin.email}' disabled and {revoked_count} active sessions terminated.",
    }


@router.post("/admins/{admin_id}/reactivate", summary="Reactivate administrator account")
async def reactivate_admin(
    admin_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found.")

    admin.status = "active"
    db.commit()

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="admin.account_reactivated",
        entity_type="admin",
        entity_id=str(admin.id),
        details={"email": admin.email},
    )

    return {"success": True, "message": f"Administrator '{admin.email}' successfully reactivated."}


@router.post("/admins/{admin_id}/revoke-sessions", summary="Revoke all active sessions for admin")
async def revoke_sessions(
    admin_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    count = revoke_all_admin_sessions(db, admin_id, current_admin.id)
    return {"success": True, "message": f"Successfully revoked {count} active sessions."}


@router.put("/admins/{admin_id}/permissions", summary="Configure granular permission overrides")
async def set_permission_overrides(
    admin_id: uuid.UUID,
    payload: BatchPermissionOverridesRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Set specific permission overrides (explicit grants or revocations) for a User Admin.
    Explicit revocations override role-level grants.
    """
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found.")

    # Remove existing overrides for permissions mentioned
    for item in payload.overrides:
        perm = db.query(Permission).filter(Permission.permission_name == item.permission_name).first()
        if not perm:
            continue
        db.query(AdminPermissionOverride).filter(
            AdminPermissionOverride.admin_id == admin_id,
            AdminPermissionOverride.permission_id == perm.id,
        ).delete()

        override = AdminPermissionOverride(
            id=uuid.uuid4(),
            admin_id=admin_id,
            permission_id=perm.id,
            is_granted=item.is_granted,
        )
        db.add(override)

    db.commit()

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="admin.permission_overrides_updated",
        entity_type="admin",
        entity_id=str(admin.id),
        details={"overrides": [o.model_dump() for o in payload.overrides]},
    )

    return _format_admin_detail(db, admin)


@router.put("/admins/{admin_id}/quiz-assignments", summary="Assign or update quiz scope for admin")
async def set_quiz_assignment(
    admin_id: uuid.UUID,
    payload: QuizAssignmentRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    """
    Assign a specific quiz to a User Admin with an access level (owner, editor, viewer).
    """
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found.")

    quiz = db.query(Quiz).filter(Quiz.id == payload.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target quiz not found.")

    assignment = (
        db.query(AdminQuizAssignment)
        .filter(
            AdminQuizAssignment.admin_id == admin_id,
            AdminQuizAssignment.quiz_id == payload.quiz_id,
        )
        .first()
    )

    if assignment:
        assignment.access_level = payload.access_level
    else:
        assignment = AdminQuizAssignment(
            id=uuid.uuid4(),
            admin_id=admin_id,
            quiz_id=payload.quiz_id,
            access_level=payload.access_level,
        )
        db.add(assignment)

    db.commit()

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="admin.quiz_assigned",
        entity_type="admin_quiz_assignment",
        entity_id=str(assignment.id),
        details={"admin_id": str(admin_id), "quiz_id": str(payload.quiz_id), "access_level": payload.access_level},
    )

    return {"success": True, "message": f"Quiz successfully assigned with '{payload.access_level}' privileges."}


@router.get("/roles", response_model=List[RoleResponse], summary="List available roles")
async def list_roles(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    roles = db.query(Role).all()
    result = []
    for r in roles:
        perms = [p.permission_name for p in r.permissions] if r.permissions else []
        result.append(RoleResponse(id=r.id, role_name=r.role_name, description=r.description, permissions=perms))
    return result


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED, summary="Create custom role")
async def create_custom_role(
    payload: CreateRoleRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    existing = db.query(Role).filter(Role.role_name == payload.role_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{payload.role_name}' already exists.",
        )

    new_role = Role(id=uuid.uuid4(), role_name=payload.role_name, description=payload.description)
    db.add(new_role)
    db.flush()

    for p_name in payload.permission_names:
        perm = db.query(Permission).filter(Permission.permission_name == p_name).first()
        if perm:
            db.add(RolePermission(role_id=new_role.id, permission_id=perm.id))

    db.commit()
    db.refresh(new_role)

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="admin.role_created",
        entity_type="role",
        entity_id=str(new_role.id),
        details={"role_name": payload.role_name, "permissions": payload.permission_names},
    )

    perms = [p.permission_name for p in new_role.permissions] if new_role.permissions else []
    return RoleResponse(id=new_role.id, role_name=new_role.role_name, description=new_role.description, permissions=perms)


@router.get("/permissions", response_model=List[PermissionResponse], summary="List platform permissions")
async def list_permissions(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    perms = db.query(Permission).order_by(Permission.permission_name.asc()).all()
    return [PermissionResponse(id=p.id, permission_name=p.permission_name, description=p.description) for p in perms]


@router.get("/audit-logs", response_model=List[AuditLogResponse], summary="Inspect immutable audit logs")
async def get_audit_logs(
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_super_admin),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    logs = query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    return [
        AuditLogResponse(
            id=log.id,
            admin_id=log.admin_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log in logs
    ]
