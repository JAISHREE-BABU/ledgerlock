from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal[
    "MATCHED",
    "FUZZY_MATCHED",
    "AMOUNT_MISMATCH",
    "DUPLICATE",
    "MISSING_IN_BANK",
    "MISSING_IN_GATEWAY",
]


class UploadResponse(BaseModel):
    batch_id: str
    bank_rows: int
    gateway_rows: int


class ReconcileResponse(BaseModel):
    run_id: str
    batch_id: str
    total: int
    summary: dict[str, int]


class ResultOut(BaseModel):
    id: int
    run_id: str
    status: str
    reason: str | None
    resolved: bool
    created_at: datetime
    bank_txn_id: int | None
    bank_reference: str | None
    bank_amount: Decimal | None
    bank_date: date | None
    gateway_txn_id: int | None
    gateway_reference: str | None
    gateway_amount: Decimal | None
    gateway_date: date | None


class ResultsPage(BaseModel):
    run_id: str | None
    total: int
    limit: int
    offset: int
    items: list[ResultOut]


class ResultUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status | None = None
    resolved: bool | None = None
    note: str | None = Field(default=None, max_length=500)
    actor: str = Field(default="analyst", min_length=1, max_length=64)


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    result_id: int
    action: str
    old_value: dict | None
    new_value: dict | None
    actor: str
    created_at: datetime


class AuditPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuditOut]