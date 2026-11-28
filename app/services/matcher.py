"""Matching engine: pure Python, no database access."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

FUZZY_DAYS = 1


@dataclass(frozen=True)
class Txn:
    id: int
    reference: str
    amount: Decimal
    txn_date: date


@dataclass
class Draft:
    status: str
    reason: str
    bank_id: int | None = None
    gateway_id: int | None = None


def _group(rows: list[Txn]) -> dict[str, list[Txn]]:
    groups: dict[str, list[Txn]] = defaultdict(list)
    for row in sorted(rows, key=lambda t: t.id):
        groups[row.reference].append(row)
    return groups


def reconcile(bank: list[Txn], gateway: list[Txn]) -> list[Draft]:
    results: list[Draft] = []
    bank_by_ref = _group(bank)
    gw_by_ref = _group(gateway)

    unmatched_bank: list[Txn] = []
    unmatched_gw: list[Txn] = []

    # Step 1: exact match on reference (first row of each reference)
    for ref, b_rows in bank_by_ref.items():
        b = b_rows[0]
        g_rows = gw_by_ref.get(ref)
        if g_rows is None:
            unmatched_bank.append(b)
            continue
        g = g_rows[0]
        if b.amount == g.amount:
            results.append(
                Draft("MATCHED", "Reference and amount match", b.id, g.id)
            )
        else:
            results.append(
                Draft(
                    "AMOUNT_MISMATCH",
                    f"Same reference {ref}: bank amount {b.amount}, "
                    f"gateway amount {g.amount}",
                    b.id,
                    g.id,
                )
            )
    for ref, g_rows in gw_by_ref.items():
        if ref not in bank_by_ref:
            unmatched_gw.append(g_rows[0])

    # Step 2: duplicate detection (extra rows with the same reference)
    for side, groups in (("bank", bank_by_ref), ("gateway", gw_by_ref)):
        for ref, rows in groups.items():
            for extra in rows[1:]:
                results.append(
                    Draft(
                        "DUPLICATE",
                        f"Reference {ref} appears {len(rows)} times in the "
                        f"{side} file; row {rows[0].id} was kept, this is an extra copy",
                        bank_id=extra.id if side == "bank" else None,
                        gateway_id=extra.id if side == "gateway" else None,
                    )
                )

    # Step 3: fuzzy match leftovers on amount + date (within FUZZY_DAYS)
    gw_by_amount: dict[Decimal, list[Txn]] = defaultdict(list)
    for g in unmatched_gw:
        gw_by_amount[g.amount].append(g)
    used_gw: set[int] = set()

    for b in sorted(unmatched_bank, key=lambda t: t.id):
        candidates = [
            g
            for g in gw_by_amount.get(b.amount, [])
            if abs((g.txn_date - b.txn_date).days) <= FUZZY_DAYS
        ]
        if not candidates:
            results.append(
                Draft(
                    "MISSING_IN_GATEWAY",
                    f"Bank reference {b.reference} has no gateway record",
                    bank_id=b.id,
                )
            )
            continue
        best = min(
            candidates,
            key=lambda g: (abs((g.txn_date - b.txn_date).days), g.id),
        )
        gw_by_amount[b.amount].remove(best)
        used_gw.add(best.id)
        results.append(
            Draft(
                "FUZZY_MATCHED",
                f"References differ ({b.reference} vs {best.reference}) but amount "
                f"{b.amount} is equal and dates {b.txn_date} / {best.txn_date} "
                f"are within {FUZZY_DAYS} day",
                b.id,
                best.id,
            )
        )

    # Step 4: gateway rows nobody claimed
    for g in unmatched_gw:
        if g.id not in used_gw:
            results.append(
                Draft(
                    "MISSING_IN_BANK",
                    f"Gateway reference {g.reference} has no bank record",
                    gateway_id=g.id,
                )
            )

    return results