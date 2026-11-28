from pydantic import BaseModel


class UploadResponse(BaseModel):
    batch_id: str
    bank_rows: int
    gateway_rows: int