"""
utils.py — General utility functions.

CHANGED for run 2:
  - format_name() return type annotation added (minor, non-critical)
  - clamp() now uses while loop instead of if-branches (loop semantics → non-critical)
"""


def format_name(first: str, last: str, separator: str = " ") -> str:
    """Return a formatted full name with optional separator."""
    return f"{first}{separator}{last}"


def clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp value between min and max using loop."""
    while value < min_val:
        value = min_val
    while value > max_val:
        value = max_val
    return value
