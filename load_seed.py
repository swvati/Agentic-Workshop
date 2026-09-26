"""Load seed/tickets.csv and seed/customers.csv into app.db (Epic 1, story 2).

Usage: uv run python load_seed.py
Running it again rebuilds the same database.
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED_DIR = ROOT / "seed"
DB_PATH = ROOT / "app.db"

TABLES = {
    "tickets": {"ticket_id": "TEXT PRIMARY KEY", "customer_id": "TEXT NOT NULL", "created_at": "TEXT", "text": "TEXT"},
    "customers": {"customer_id": "TEXT PRIMARY KEY", "name": "TEXT", "plan": "TEXT", "open_tickets": "INTEGER"},
}


def _read_rows(csv_path: Path, columns: list[str]) -> list[tuple]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != columns:
            raise ValueError(f"{csv_path.name} has columns {reader.fieldnames}, expected {columns}")
        return [tuple(row[column] for column in columns) for row in reader]


def load(db_path: Path = DB_PATH, seed_dir: Path = SEED_DIR) -> dict[str, int]:
    """Rebuild every table from its CSV and return the row count per table."""
    counts = {}
    with sqlite3.connect(db_path) as conn:
        for table, schema in TABLES.items():
            columns = list(schema)
            rows = _read_rows(seed_dir / f"{table}.csv", columns)
            conn.execute(f"DROP TABLE IF EXISTS {table}")
            conn.execute(f"CREATE TABLE {table} ({', '.join(f'{name} {kind}' for name, kind in schema.items())})")
            conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' for _ in columns)})", rows)
            counts[table] = len(rows)
    return counts


if __name__ == "__main__":
    for table, count in load().items():
        print(f"{table}: {count} rows")
    print(f"Wrote {DB_PATH.name}")
