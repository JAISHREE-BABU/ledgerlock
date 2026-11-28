from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BankTransaction, GatewayTransaction, ReconciliationResult
from app.schemas import ResultOut, ResultsPage, ResultUpdate, Status
from app.services.audit import write_audit

router = APIRouter(tags=["results"])


def _base_query():
    return (
        select(ReconciliationResult, BankTransaction, GatewayTransaction)
        .outerjoin(
            BankTransaction, ReconciliationResult.bank_txn_id == BankTransaction.id
        )
        .outerjoin(
            GatewayTransaction,
            ReconciliationResult.gateway_txn_id == GatewayTransaction.id,
        )
    )


def _to_out(res, bank, gw) -> ResultOut:
    return ResultOut(
        id=res.id,
        run_id=res.run_id,
        status=res.status,
        reason=res.reason,
        resolved=res.resolved,
        created_at=res.created_at,
        bank_txn_id=res.bank_txn_id,
        bank_reference=bank.reference if bank else None,
        bank_amount=bank.amount if bank else None,
        bank_date=bank.txn_date if bank else None,
        gateway_txn_id=res.gateway_txn_id,
        gateway_reference=gw.reference if gw else None,
        gateway_amount=gw.amount if gw else None,
        gateway_date=gw.txn_date if gw else None,
    )


@router.get("/results", response_model=ResultsPage)
def list_results(
    status: Status | None = None,
    resolved: bool | None = None,
    run_id: str | None = Query(default=None, max_length=36),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    if run_id is None:  # default: the latest run
        run_id = db.scalar(
            select(ReconciliationResult.run_id)
            .order_by(ReconciliationResult.id.desc())
            .limit(1)
        )
    if run_id is None:
        return ResultsPage(run_id=None, total=0, limit=limit, offset=offset, items=[])

    filters = [ReconciliationResult.run_id == run_id]
    if status is not None:
        filters.append(ReconciliationResult.status == status)
    if resolved is not None:
        filters.append(ReconciliationResult.resolved == resolved)

    total = db.scalar(
        select(func.count()).select_from(ReconciliationResult).where(*filters)
    )
    rows = db.execute(
        _base_query()
        .where(*filters)
        .order_by(ReconciliationResult.id)
        .limit(limit)
        .offset(offset)
    ).all()

    return ResultsPage(
        run_id=run_id,
        total=total or 0,
        limit=limit,
        offset=offset,
        items=[_to_out(r, b, g) for r, b, g in rows],
    )


@router.patch("/results/{result_id}", response_model=ResultOut)
def update_result(
    result_id: int, body: ResultUpdate, db: Session = Depends(get_db)
):
    result = db.get(ReconciliationResult, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")

    note = body.note.strip() if body.note else None
    if body.status is None and body.resolved is None and not note:
        raise HTTPException(
            status_code=422, detail="Send at least one of: status, resolved, note"
        )

    status_changes = body.status is not None and body.status != result.status
    if status_changes and not note:
        raise HTTPException(
            status_code=422, detail="A note is required when changing the status"
        )

    old: dict = {}
    new: dict = {}
    if status_changes:
        old["status"], new["status"] = result.status, body.status
        result.status = body.status
    if body.resolved is not None and body.resolved != result.resolved:
        old["resolved"], new["resolved"] = result.resolved, body.resolved
        result.resolved = body.resolved
    if note:
        new["note"] = note

    if new:  # something real changed: write the audit row in the same commit
        if "status" in new:
            action = "STATUS_CHANGED"
        elif "resolved" in new:
            action = "RESOLVED" if new["resolved"] else "REOPENED"
        else:
            action = "NOTE_ADDED"
        write_audit(db, result.id, action, old or None, new, body.actor)
        db.commit()

    res, bank, gw = db.execute(
        _base_query().where(ReconciliationResult.id == result_id)
    ).one()
    return _to_out(res, bank, gw)