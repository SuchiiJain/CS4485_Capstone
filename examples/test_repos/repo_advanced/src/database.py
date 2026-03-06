"""
database.py — Database access layer.
"""


def fetch_user(cursor, user_id: int) -> dict:
    """Fetch a user record from the database."""
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()


def insert_record(cursor, table: str, data: dict) -> int:
    """Insert a record into the given table and return the new row ID."""
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", list(data.values()))
    return cursor.lastrowid


def delete_record(cursor, table: str, record_id: int) -> bool:
    """Delete a record by ID. Returns True if a row was deleted."""
    cursor.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
    return cursor.rowcount > 0
