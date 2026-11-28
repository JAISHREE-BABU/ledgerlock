from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog
from app.schemas import AuditPage

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=AuditPage)
def list_audit(
    result_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    filters = []
    if result_id is not None:
        filters.append(AuditLog.result_id == result_id)

    total = db.scalar(select(func.count()).select_from(AuditLog).where(*filters))
    items = db.scalars(
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.id.desc())  # newest first
        .limit(limit)
        .offset(offset)
    ).all()
    return AuditPage(total=total or 0, limit=limit, offset=offset, items=items)