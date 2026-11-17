import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.security_audit import AuditLog
from backend.app.core.logging import logger


def log_audit_event(
    db: Session,
    admin_id: Optional[uuid.UUID] = None,
    action: str = "general.action",
    entity_type: Optional[str] = None,
    entity_id: Optional[Any] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    **kwargs: Any,
) -> AuditLog:
    """
    Creates an immutable administrative audit log record in PostgreSQL.
    Audit records capture security events, access changes, configuration edits, and administrative actions.
    Supports keyword aliases: actor_id -> admin_id, entity_name -> entity_type.
    """
    effective_admin_id = admin_id or kwargs.get("actor_id")
    effective_entity_type = entity_type or kwargs.get("entity_name") or "system"
    effective_details = details or {}
    if "actor_email" in kwargs and "actor_email" not in effective_details:
        effective_details["actor_email"] = kwargs["actor_email"]

    try:
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            admin_id=effective_admin_id,
            action=action,
            entity_type=effective_entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=effective_details,
            ip_address=ip_address,
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        logger.info(
            f"Audit Log Recorded: [{action}] on [{effective_entity_type}:{entity_id}] by admin [{effective_admin_id}]",
            extra={"action": action, "entity_type": effective_entity_type, "admin_id": str(effective_admin_id) if effective_admin_id else None},
        )
        return audit_entry
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}", exc_info=True)
        db.rollback()
        raise e
