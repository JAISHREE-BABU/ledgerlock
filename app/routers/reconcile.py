import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BankTransaction, GatewayTransaction, ReconciliationResult
from app.schemas import ReconcileResponse
from app.services.matcher import Txn, reconcile

router = APIRouter(tags=["reconcile"])


@router.post("/reconcile", response_model=ReconcileResponse)
def run_reconcile(
    batch_id: str | None = Query(default=None, max_length=36),
    db: Session = Depends(get_db),
):
    if batch_id is None:
        batch_id = db.scalar(
            select(BankTransaction.batch_id)
            .order_by(BankTransaction.id.desc())
            .limit(1)
        )
        if batch_id is None:
            raise HTTPException(
                status_code=404, detail="No uploaded data found. Call POST /upload first."
            )

    bank = [
        Txn(r.id, r.reference, r.amount, r.txn_date)
        for r in db.scalars(
            select(BankTransaction).where(BankTransaction.batch_id == batch_id)
        )
    ]
    gateway = [
        Txn(r.id, r.reference, r.amount, r.txn_date)
        for r in db.scalars(
            select(GatewayTransaction).where(GatewayTransaction.batch_id == batch_id)
        )
    ]
    if not bank and not gateway:
        raise HTTPException(status_code=404, detail="Batch not found")

    drafts = reconcile(bank, gateway)

    run_id = str(uuid.uuid4())
    db.add_all(
        ReconciliationResult(
            bank_txn_id=d.bank_id,
            gateway_txn_id=d.gateway_id,
            status=d.status,
            reason=d.reason,
            run_id=run_id,
        )
        for d in drafts
    )
    db.commit()

    return ReconcileResponse(
        run_id=run_id,
        batch_id=batch_id,
        total=len(drafts),
        summary=dict(Counter(d.status for d in drafts)),
    )