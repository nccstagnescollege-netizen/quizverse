import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.auth_rbac import Admin, Role, AdminRole
from backend.app.schemas.auth import LoginRequest, TokenResponse, AdminProfileResponse
from backend.app.services.auth_service import (
    verify_password,
    create_access_token,
    create_session,
    revoke_session,
    check_rate_limit,
    record_failed_attempt,
    clear_failed_attempts,
    decode_token,
)
from backend.app.services.rbac_service import get_current_admin, get_admin_effective_permissions
from backend.app.services.audit_service import log_audit_event
from backend.app.core.config import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="Administrator authentication")
async def login(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate an administrator with email and password.
    Enforces brute-force rate-limiting, session tracking, and audit logging.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{payload.email.lower()}"

    # 1. Rate Limiting Check
    check_rate_limit(rate_limit_key)

    # 2. Admin Lookup
    admin = db.query(Admin).filter(Admin.email == payload.email.lower()).first()
    if not admin or not admin.password_hash or not verify_password(payload.password, admin.password_hash):
        record_failed_attempt(rate_limit_key)
        # Log security audit for failed login attempt
        log_audit_event(
            db,
            admin_id=admin.id if admin else None,
            action="admin.login_failed",
            entity_type="admin",
            entity_id=str(admin.id) if admin else payload.email,
            details={"ip_address": client_ip, "reason": "Invalid credentials"},
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Check Account Status
    if admin.status != "active":
        log_audit_event(
            db,
            admin_id=admin.id,
            action="admin.login_rejected_disabled",
            entity_type="admin",
            entity_id=str(admin.id),
            details={"ip_address": client_ip, "status": admin.status},
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Administrator account is {admin.status}. Please contact the Super Administrator.",
        )

    # 4. Successful Authentication: clear rate limit counter
    clear_failed_attempts(rate_limit_key)

    # 5. Create JWT Access Token and Server-Side Session
    user_agent = request.headers.get("user-agent")
    token_str, jti, expires_in = create_access_token(admin)
    expires_at = datetime.now(timezone.utc) + (
        settings.ACCESS_TOKEN_EXPIRE_MINUTES and __import__("datetime").timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    create_session(
        db,
        admin_id=admin.id,
        token_jti=jti,
        expires_at=expires_at,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    # 6. Update last_login_at
    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # 7. Audit log
    log_audit_event(
        db,
        admin_id=admin.id,
        action="admin.login_success",
        entity_type="admin",
        entity_id=str(admin.id),
        details={"ip_address": client_ip, "token_jti": jti},
        ip_address=client_ip,
    )

    # 8. Resolve roles & permissions
    roles = [r.role_name for r in admin.roles] if admin.roles else []
    permissions = sorted(list(get_admin_effective_permissions(db, admin)))

    user_profile = AdminProfileResponse(
        id=admin.id,
        email=admin.email,
        full_name=admin.full_name,
        status=admin.status,
        is_super_admin=admin.is_super_admin,
        roles=roles,
        permissions=permissions,
        last_login_at=admin.last_login_at,
        created_at=admin.created_at,
    )

    return TokenResponse(
        access_token=token_str,
        token_type="bearer",
        expires_in=expires_in,
        jti=jti,
        user=user_profile,
    )


@router.post("/logout", summary="Administrator logout & session invalidation")
async def logout(
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Log out the current administrator, revoking their active session token immediately.
    """
    auth_header = request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    client_ip = request.client.host if request.client else "unknown"

    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        if jti:
            revoke_session(db, jti, current_admin.id)
    except Exception:
        pass

    log_audit_event(
        db,
        admin_id=current_admin.id,
        action="admin.logout",
        entity_type="admin",
        entity_id=str(current_admin.id),
        details={"ip_address": client_ip},
        ip_address=client_ip,
    )

    return {"success": True, "message": "Successfully logged out and session revoked."}


@router.get("/me", response_model=AdminProfileResponse, summary="Get current administrator profile")
async def get_me(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Retrieve authenticated administrator details, including roles and resolved permissions.
    """
    roles = [r.role_name for r in current_admin.roles] if current_admin.roles else []
    permissions = sorted(list(get_admin_effective_permissions(db, current_admin)))

    return AdminProfileResponse(
        id=current_admin.id,
        email=current_admin.email,
        full_name=current_admin.full_name,
        status=current_admin.status,
        is_super_admin=current_admin.is_super_admin,
        roles=roles,
        permissions=permissions,
        last_login_at=current_admin.last_login_at,
        created_at=current_admin.created_at,
    )
