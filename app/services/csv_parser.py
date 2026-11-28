"""Read and validate the bank and gateway CSV files."""
import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

BANK_COLUMNS = {"reference", "amount", "txn_date", "description"}
GATEWAY_COLUMNS = {"reference", "amount", "txn_date", "status"}
MAX_ROWS = 50_000
MAX_AMOUNT = Decimal("9999999999.99")


class CSVParseError(ValueError):
    """Raised when a file is not a valid bank/gateway CSV."""


def _parse(raw: bytes, required: set[str], kind: str) -> list[dict]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CSVParseError(f"{kind}: file is not valid UTF-8 text")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CSVParseError(f"{kind}: file is empty")

    missing = required - set(reader.fieldnames)
    if missing:
        raise CSVParseError(f"{kind}: missing column(s): {', '.join(sorted(missing))}")

    rows: list[dict] = []
    for line_no, row in enumerate(reader, start=2):  # line 1 is the header
        if len(rows) >= MAX_ROWS:
            raise CSVParseError(f"{kind}: more than {MAX_ROWS} rows")

        where = f"{kind} line {line_no}"

        reference = (row.get("reference") or "").strip()
        if not reference or len(reference) > 64:
            raise CSVParseError(f"{where}: reference is empty or longer than 64 characters")

        try:
            amount = Decimal((row.get("amount") or "").strip())
        except InvalidOperation:
            raise CSVParseError(f"{where}: amount is not a number")
        if not amount.is_finite() or abs(amount) > MAX_AMOUNT:
            raise CSVParseError(f"{where}: amount is out of range")
        amount = amount.quantize(Decimal("0.01"))

        try:
            txn_date = date.fromisoformat((row.get("txn_date") or "").strip())
        except ValueError:
            raise CSVParseError(f"{where}: txn_date must look like 2026-11-28")

        clean = {"reference": reference, "amount": amount, "txn_date": txn_date}
        if "description" in required:
            clean["description"] = (row.get("description") or "").strip()[:255] or None
        if "status" in required:
            clean["status"] = (row.get("status") or "SUCCESS").strip().upper()[:20]
        rows.append(clean)

    if not rows:
        raise CSVParseError(f"{kind}: file has a header but no rows")
    return rows


def parse_bank_csv(raw: bytes) -> list[dict]:
    return _parse(raw, BANK_COLUMNS, "bank file")


def parse_gateway_csv(raw: bytes) -> list[dict]:
    return _parse(raw, GATEWAY_COLUMNS, "gateway file")