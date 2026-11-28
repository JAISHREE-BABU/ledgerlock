from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    txn_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class GatewayTransaction(Base):
    __tablename__ = "gateway_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    txn_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS")
    batch_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ReconciliationResult(Base):
    __tablename__ = "reconciliation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_txn_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_transactions.id"), nullable=True
    )
    gateway_txn_id: Mapped[int | None] = mapped_column(
        ForeignKey("gateway_transactions.id"), nullable=True
    )
    # MATCHED, FUZZY_MATCHED, AMOUNT_MISMATCH, DUPLICATE,
    # MISSING_IN_BANK, MISSING_IN_GATEWAY
    status: Mapped[str] = mapped_column(String(30), index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(
        ForeignKey("reconciliation_results.id"), index=True
    )
    action: Mapped[str] = mapped_column(String(50))
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )