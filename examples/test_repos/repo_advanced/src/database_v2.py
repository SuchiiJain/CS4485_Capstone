"""
database.py — Database access layer.

CHANGED for run 2:
  - fetch_user() gains `include_deleted` param (signature change → CRITICAL)
  - insert_record() now commits the transaction (side-effect change → CRITICAL)
  - delete_record() logic unchanged (no event expected)
"""


def fetch_user(cursor, user_id: int, include_deleted: bool = False) -> dict:
    """Fetch a user record, optionally including soft-deleted rows."""
    if include_deleted:
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    else:
        cursor.execute("SELECT * FROM users WHERE id = ? AND deleted_at IS NULL", (user_id,))
    return cursor.fetchone()


def insert_record(cursor, table: str, data: dict) -> int:
    """Insert a record and commit the transaction immediately."""
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", list(data.values()))
    cursor.connection.commit()
    return cursor.lastrowid


def delete_record(cursor, table: str, record_id: int) -> bool:
    """Delete a record by ID. Returns True if a row was deleted."""
    cursor.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
    return cursor.rowcount > 0
