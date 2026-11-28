"""Generate fake bank and gateway CSV files with deliberate errors."""
import argparse
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

OUT_DIR = Path(__file__).resolve().parent.parent / "data"

# How many of each deliberate error to plant
PLAN = {
    "missing_in_gateway": 8,   # in bank only
    "missing_in_bank": 8,      # in gateway only
    "amount_mismatch": 8,      # same reference, different amount
    "fuzzy": 6,                # different reference, same amount, date +/- 1 day
    "duplicate_gateway": 4,    # gateway lists the payment twice
    "duplicate_bank": 3,       # bank lists the payment twice
}


def cents_to_str(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    planted = sum(PLAN.values())
    if args.count <= planted:
        raise SystemExit(f"--count must be larger than {planted}")

    random.seed(args.seed)
    Faker.seed(args.seed)
    fake = Faker()

    # 1. Build the base list of "true" payments
    today = date.today()
    base = []
    for i in range(1, args.count + 1):
        base.append(
            {
                "reference": f"TXN{i:06d}",
                "cents": random.randint(1000, 500000),
                "date": today - timedelta(days=random.randint(1, 30)),
                "description": fake.company(),
            }
        )

    # 2. Randomly choose which payments get which error
    indices = list(range(args.count))
    random.shuffle(indices)
    label: dict[int, str] = {}
    pos = 0
    for name, n in PLAN.items():
        for idx in indices[pos : pos + n]:
            label[idx] = name
        pos += n

    # 3. Build bank and gateway rows
    bank_rows, gateway_rows = [], []
    refs: dict[str, list[str]] = {name: [] for name in PLAN}

    for idx, t in enumerate(base):
        kind = label.get(idx, "normal")
        if kind != "normal":
            refs[kind].append(t["reference"])

        bank = {
            "reference": t["reference"],
            "amount": cents_to_str(t["cents"]),
            "txn_date": t["date"].isoformat(),
            "description": t["description"],
        }
        gw = {
            "reference": t["reference"],
            "amount": cents_to_str(t["cents"]),
            "txn_date": t["date"].isoformat(),
            "status": "SUCCESS",
        }

        if kind == "missing_in_gateway":
            bank_rows.append(bank)
        elif kind == "missing_in_bank":
            gateway_rows.append(gw)
        elif kind == "amount_mismatch":
            gw["amount"] = cents_to_str(t["cents"] + random.randint(100, 5000))
            bank_rows.append(bank)
            gateway_rows.append(gw)
        elif kind == "fuzzy":
            gw["reference"] = f"PAY-{t['reference'][3:]}"
            shifted = t["date"] + timedelta(days=random.choice([-1, 1]))
            gw["txn_date"] = shifted.isoformat()
            bank_rows.append(bank)
            gateway_rows.append(gw)
        elif kind == "duplicate_gateway":
            bank_rows.append(bank)
            gateway_rows.extend([gw, dict(gw)])
        elif kind == "duplicate_bank":
            bank_rows.extend([bank, dict(bank)])
            gateway_rows.append(gw)
        else:
            bank_rows.append(bank)
            gateway_rows.append(gw)

    random.shuffle(bank_rows)
    random.shuffle(gateway_rows)

    # 4. Write files
    OUT_DIR.mkdir(exist_ok=True)
    write_csv(
        OUT_DIR / "bank.csv",
        ["reference", "amount", "txn_date", "description"],
        bank_rows,
    )
    write_csv(
        OUT_DIR / "gateway.csv",
        ["reference", "amount", "txn_date", "status"],
        gateway_rows,
    )
    with open(OUT_DIR / "expected_summary.json", "w", encoding="utf-8") as f:
        json.dump({"counts": PLAN, "references": refs}, f, indent=2)

    print(f"Generated {args.count} base transactions (seed {args.seed})")
    print(f"data/bank.csv:    {len(bank_rows)} rows")
    print(f"data/gateway.csv: {len(gateway_rows)} rows")
    print("Planted issues:")
    for name, n in PLAN.items():
        print(f"  {name}: {n}")


if __name__ == "__main__":
    main()