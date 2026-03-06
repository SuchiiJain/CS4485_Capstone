"""
auth.py — User authentication helpers.
"""


def login(username: str, password: str) -> bool:
    """Log in a user by checking credentials."""
    if not username or not password:
        return False
    return username == "admin" and password == "secret"


def logout(user_id: int) -> None:
    """Log out a user by clearing their session."""
    print(f"User {user_id} logged out.")


def get_user(user_id: int) -> dict:
    """Return a user record by ID."""
    return {"id": user_id, "name": "Alice"}
