"""
Sample code BEFORE changes — used as the "old" version for testing.

This simulates what a codebase looks like at the stored baseline.
Compare with sample_code_v2.py to see what Docrot would detect.
"""


def authenticate_user(username, password):
    """Authenticate a user with username and password."""
    user = db.find_user(username)
    if user is None:
        raise ValueError("User not found")

    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid password")

    token = generate_token(user.id)
    return token


def get_user_profile(user_id):
    """Fetch a user's profile from the database."""
    profile = db.get_profile(user_id)
    if profile is None:
        return None
    return profile


def calculate_shipping(weight, destination):
    """Calculate shipping cost based on weight and destination."""
    base_rate = 5.0

    if weight > 50:
        rate = base_rate * 3
    elif weight > 20:
        rate = base_rate * 2
    else:
        rate = base_rate

    if destination == "international":
        rate = rate * 2.5

    return round(rate, 2)


def _format_currency(amount):
    """Internal helper to format a number as currency."""
    return f"${amount:.2f}"
