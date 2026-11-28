"""Write audit log entries. The caller commits, so the audit row and the
change it describes are saved together."""
from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    result_id: int,
    action: str,
    old_value: dict | None,
    new_value: dict | None,
    actor: str,
) -> None:
    db.add(
        AuditLog(
            result_id=result_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            actor=actor,
        )
    )