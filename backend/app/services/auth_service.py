import uuid
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.auth_rbac import Admin, AdminSession
from backend.app.services.audit_service import log_audit_event

# In-memory brute force protection tracking: {key: [timestamp1, timestamp2, ...]}
_FAILED_ATTEMPTS: Dict[str, list] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 900  # 15 minutes


def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt with standard salt rounds."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verify plaintext password against hashed password."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.warning(f"Password verification encountered error: {e}")
        return False


def check_rate_limit(key: str) -> None:
    """
    Check if an IP or email is currently rate-limited due to excessive failed attempts.
    Raises HTTP 429 Too Many Requests if threshold is breached.
    """
    now = time.time()
    attempts = _FAILED_ATTEMPTS.get(key, [])
    # Filter attempts within window
    valid_attempts = [t for t in attempts if now - t < LOCKOUT_WINDOW_SECONDS]
    _FAILED_ATTEMPTS[key] = valid_attempts

    if len(valid_attempts) >= MAX_FAILED_ATTEMPTS:
        logger.warning(f"Rate limit triggered for key [{key}]. Too many failed login attempts.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Account temporarily locked for 15 minutes. Please try again later.",
        )


def record_failed_attempt(key: str) -> None:
    """Record a failed login attempt for rate limiting."""
    now = time.time()
    if key not in _FAILED_ATTEMPTS:
        _FAILED_ATTEMPTS[key] = []
    _FAILED_ATTEMPTS[key].append(now)


def clear_failed_attempts(key: str) -> None:
    """Clear failed attempts upon successful login."""
    if key in _FAILED_ATTEMPTS:
        del _FAILED_ATTEMPTS[key]


def create_access_token(
    admin: Admin,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, int]:
    """
    Generate a signed JWT access token for an administrator.
    Returns: (token_str, jti, expires_in_seconds)
    """
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = now + delta
    expires_in = int(delta.total_seconds())

    payload = {
        "sub": str(admin.id),
        "admin_id": str(admin.id),
        "email": admin.email,
        "is_super_admin": admin.is_super_admin,
        "jti": jti,
        "iss": "quizverse-auth",
        "aud": "quizverse-api",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(
        payload,
        settings.effective_jwt_secret,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, jti, expires_in


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token using the effective secret.
    Validates expiration, format, and cryptographic signature.
    """
    try:
        # PyJWT validates exp, iat by default
        payload = jwt.decode(
            token,
            settings.effective_jwt_secret,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},  # Allow Supabase / custom audiences flexibly
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please authenticate again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or corrupted authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_session(
    db: Session,
    admin_id: uuid.UUID,
    token_jti: str,
    expires_at: datetime,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AdminSession:
    """Store an active session entry in admin_sessions."""
    session = AdminSession(
        id=uuid.uuid4(),
        admin_id=admin_id,
        token_jti=token_jti,
        ip_address=ip_address,
        user_agent=user_agent,
        is_revoked=False,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def is_session_active(db: Session, token_jti: str) -> bool:
    """
    Verify whether a session with the given JTI is active and not revoked.
    """
    session = db.query(AdminSession).filter(AdminSession.token_jti == token_jti).first()
    if not session:
        return False
    if session.is_revoked:
        return False
    # Ensure timezone comparison works cleanly
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return False
    return True


def touch_session(db: Session, token_jti: str) -> None:
    """Update last_active_at on active session."""
    db.execute(
        update(AdminSession)
        .where(AdminSession.token_jti == token_jti)
        .values(last_active_at=datetime.now(timezone.utc))
    )
    db.commit()


def revoke_session(db: Session, token_jti: str, admin_id: Optional[uuid.UUID] = None) -> bool:
    """Revoke a single session by JTI."""
    session = db.query(AdminSession).filter(AdminSession.token_jti == token_jti).first()
    if session:
        session.is_revoked = True
        db.commit()
        log_audit_event(
            db,
            admin_id=admin_id or session.admin_id,
            action="admin.session_revoked",
            entity_type="admin_session",
            entity_id=str(session.id),
            details={"token_jti": token_jti},
        )
        return True
    return False


def revoke_all_admin_sessions(db: Session, admin_id: uuid.UUID, revoking_admin_id: Optional[uuid.UUID] = None) -> int:
    """
    Immediately invalidate all active sessions for a target admin.
    Used when an admin is disabled, privileges are revoked, or an active session is manually killed.
    """
    result = db.query(AdminSession).filter(
        AdminSession.admin_id == admin_id,
        AdminSession.is_revoked == False,
    ).all()

    count = 0
    for sess in result:
        sess.is_revoked = True
        count += 1
    db.commit()

    log_audit_event(
        db,
        admin_id=revoking_admin_id or admin_id,
        action="admin.all_sessions_revoked",
        entity_type="admin",
        entity_id=str(admin_id),
        details={"revoked_count": count},
    )
    return count
