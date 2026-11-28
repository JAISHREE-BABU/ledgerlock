from pydantic import BaseModel


class UploadResponse(BaseModel):
    batch_id: str
    bank_rows: int
    gateway_rows: int


class ReconcileResponse(BaseModel):
    run_id: str
    batch_id: str
    total: int
    summary: dict[str, int]