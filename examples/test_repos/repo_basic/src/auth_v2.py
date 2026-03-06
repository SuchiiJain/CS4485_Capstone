"""
auth.py — User authentication helpers.

CHANGED for run 2:
  - login() gains a new `remember_me` param (signature change → CRITICAL)
  - logout() now raises ValueError for invalid IDs (exception behavior → CRITICAL)
  - get_user() removed entirely (symbol removed → CRITICAL)
  - hash_password() added as new public function
"""


def login(username: str, password: str, remember_me: bool = False) -> bool:
    """Log in a user by checking credentials, optionally persisting session."""
    if not username or not password:
        return False
    authenticated = username == "admin" and password == "secret"
    if authenticated and remember_me:
        print("Persistent session created.")
    return authenticated


def logout(user_id: int) -> None:
    """Log out a user by clearing their session."""
    if user_id <= 0:
        raise ValueError(f"Invalid user_id: {user_id}")
    print(f"User {user_id} logged out.")


def hash_password(password: str) -> str:
    """Hash a password for secure storage."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
