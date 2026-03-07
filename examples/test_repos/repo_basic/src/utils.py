"""
utils.py — General utility functions.
"""


def format_name(first: str, last: str) -> str:
    """Return a formatted full name."""
    return f"{first} {last}"


def clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp value between min and max."""
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value
