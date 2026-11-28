import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BankTransaction, GatewayTransaction
from app.schemas import UploadResponse
from app.services.csv_parser import CSVParseError, parse_bank_csv, parse_gateway_csv

router = APIRouter(tags=["upload"])

MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file


def _read_limited(upload: UploadFile) -> bytes:
    if not (upload.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")
    data = upload.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 5 MB")
    return data


@router.post("/upload", response_model=UploadResponse, status_code=201)
def upload_files(
    bank_file: UploadFile = File(...),
    gateway_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    bank_raw = _read_limited(bank_file)
    gateway_raw = _read_limited(gateway_file)

    try:
        bank_rows = parse_bank_csv(bank_raw)
        gateway_rows = parse_gateway_csv(gateway_raw)
    except CSVParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    batch_id = str(uuid.uuid4())
    db.add_all(BankTransaction(batch_id=batch_id, **r) for r in bank_rows)
    db.add_all(GatewayTransaction(batch_id=batch_id, **r) for r in gateway_rows)
    db.commit()  # one commit: both files are saved, or neither

    return UploadResponse(
        batch_id=batch_id,
        bank_rows=len(bank_rows),
        gateway_rows=len(gateway_rows),
    )