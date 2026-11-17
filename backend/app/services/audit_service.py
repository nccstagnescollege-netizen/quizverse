import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.security_audit import AuditLog
from backend.app.core.logging import logger


def log_audit_event(
    db: Session,
    admin_id: Optional[uuid.UUID],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Creates an immutable administrative audit log record in PostgreSQL.
    Audit records capture security events, access changes, configuration edits, and administrative actions.
    """
    try:
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details or {},
            ip_address=ip_address,
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        logger.info(
            f"Audit Log Recorded: [{action}] on [{entity_type}:{entity_id}] by admin [{admin_id}]",
            extra={"action": action, "entity_type": entity_type, "admin_id": str(admin_id) if admin_id else None},
        )
        return audit_entry
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}", exc_info=True)
        db.rollback()
        raise e
