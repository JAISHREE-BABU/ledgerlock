from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import audit, reconcile, results, upload

app = FastAPI(title="LedgerLock", version="0.7.0")
app.include_router(upload.router)
app.include_router(reconcile.router)
app.include_router(results.router)
app.include_router(audit.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}