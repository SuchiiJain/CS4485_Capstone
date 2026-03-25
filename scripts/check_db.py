import sqlite3
from pathlib import Path

DB_PATH = Path("database/docrot.db")

if not DB_PATH.exists():
    print(f"DB not found: {DB_PATH}")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

def count(table: str) -> int:
    return cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

for table in ["scan_reports", "scans", "issues", "docs_to_update", "fingerprints"]:
    print(f"{table}: {count(table)}")

latest = cur.execute(
    "SELECT id, commit_hash, total_issues, created_at FROM scans ORDER BY id DESC LIMIT 5"
).fetchall()
print("latest_scans:", latest)

conn.close()
