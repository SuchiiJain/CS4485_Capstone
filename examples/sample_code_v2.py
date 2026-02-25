"""
Sample code AFTER changes — used as the "new" version for testing.

Changes from v1 (what Docrot should detect):

1. authenticate_user: signature changed (added mfa_code param),
   new auth logic, new side effect (audit_log) → CRITICAL

2. get_user_profile: only comment/formatting changed → score 0

3. calculate_shipping: condition changed (> 50 → >= 50), new branch
   for "express", literal change (2.5 → 3.0) → medium-high score

4. _format_currency: unchanged

5. delete_user: NEW function (added) → flagged as addition
"""


def authenticate_user(username, password, mfa_code=None):
    """Authenticate a user with username, password, and optional MFA."""
    user = db.find_user(username)
    if user is None:
        raise ValueError("User not found")

    if not verify_password(password, user.password_hash):
        audit_log.record("failed_login", username)
        raise ValueError("Invalid password")

    if mfa_code is not None:
        if not verify_mfa(user.id, mfa_code):
            raise PermissionError("Invalid MFA code")

    token = generate_token(user.id)
    audit_log.record("successful_login", username)
    return token


def get_user_profile(user_id):
    """
    Fetch a user's profile from the database.
    Returns None if not found.
    """
    # Retrieve the profile
    profile = db.get_profile(user_id)
    if profile is None:
        return None
    return profile


def calculate_shipping(weight, destination):
    """Calculate shipping cost based on weight and destination."""
    base_rate = 5.0

    if weight >= 50:
        rate = base_rate * 3
    elif weight > 20:
        rate = base_rate * 2
    else:
        rate = base_rate

    if destination == "international":
        rate = rate * 3.0
    elif destination == "express":
        rate = rate * 1.5

    return round(rate, 2)


def _format_currency(amount):
    """Internal helper to format a number as currency."""
    return f"${amount:.2f}"


def delete_user(user_id, hard_delete=False):
    """Delete a user from the system."""
    user = db.find_user_by_id(user_id)
    if user is None:
        raise ValueError("User not found")

    if hard_delete:
        db.hard_delete("users", user_id)
    else:
        db.soft_delete("users", user_id)

    audit_log.record("user_deleted", user_id)
    return True
