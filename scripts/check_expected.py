"""Compare the latest reconciliation run with data/expected_summary.json."""
import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import BankTransaction, GatewayTransaction, ReconciliationResult

EXPECTED = Path(__file__).resolve().parent.parent / "data" / "expected_summary.json"


def main() -> None:
    expected = json.loads(EXPECTED.read_text())["references"]

    with SessionLocal() as db:
        run_id = db.scalar(
            select(ReconciliationResult.run_id)
            .order_by(ReconciliationResult.id.desc())
            .limit(1)
        )
        if run_id is None:
            raise SystemExit("No reconciliation run found. Call POST /reconcile first.")

        rows = db.execute(
            select(
                ReconciliationResult.status,
                BankTransaction.reference.label("bank_ref"),
                GatewayTransaction.reference.label("gateway_ref"),
            )
            .outerjoin(
                BankTransaction, ReconciliationResult.bank_txn_id == BankTransaction.id
            )
            .outerjoin(
                GatewayTransaction,
                ReconciliationResult.gateway_txn_id == GatewayTransaction.id,
            )
            .where(ReconciliationResult.run_id == run_id)
        ).all()

    found: dict[str, set[str]] = defaultdict(set)
    for status, bank_ref, gateway_ref in rows:
        found[status].add(bank_ref or gateway_ref)

    checks = {
        "MISSING_IN_GATEWAY": expected["missing_in_gateway"],
        "MISSING_IN_BANK": expected["missing_in_bank"],
        "AMOUNT_MISMATCH": expected["amount_mismatch"],
        "FUZZY_MATCHED": expected["fuzzy"],
        "DUPLICATE": expected["duplicate_gateway"] + expected["duplicate_bank"],
    }

    all_ok = True
    for status, refs in checks.items():
        want, got = set(refs), found.get(status, set())
        ok = want == got
        all_ok = all_ok and ok
        print(f"{'PASS' if ok else 'FAIL'}  {status}: expected {len(want)}, found {len(got)}")
        if not ok:
            print("      not found:", sorted(want - got))
            print("      unexpected:", sorted(got - want))

    if all_ok:
        print("All planted issues were found.")
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()