"""
payments.py — Payment processing logic.

CHANGED for run 2:
  - charge_card() gains `currency` param + new auth check (signature + auth → CRITICAL)
  - refund() now raises RuntimeError on failure instead of returning bool (exception → CRITICAL)
  - get_balance() removed entirely (symbol removed → CRITICAL)
  - apply_discount() added as new public function
"""
import requests


def charge_card(user_id: int, amount: float, card_token: str, currency: str = "USD") -> dict:
    """Charge a user's card via the payment gateway with currency support."""
    if amount <= 0:
        raise ValueError("Amount must be positive.")
    if not card_token:
        raise PermissionError("Invalid card token.")
    response = requests.post("https://payments.example.com/charge", json={
        "user": user_id,
        "amount": amount,
        "token": card_token,
        "currency": currency,
    })
    return response.json()


def refund(transaction_id: str, reason: str = "") -> None:
    """Issue a refund for a transaction. Raises RuntimeError on failure."""
    response = requests.post("https://payments.example.com/refund", json={
        "transaction_id": transaction_id,
        "reason": reason,
    })
    if response.status_code != 200:
        raise RuntimeError(f"Refund failed for {transaction_id}")


def apply_discount(user_id: int, discount_pct: float) -> float:
    """Apply a discount to a user's next charge. Returns new discounted amount."""
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("Discount must be between 0 and 100.")
    response = requests.post("https://payments.example.com/discount", json={
        "user": user_id,
        "discount": discount_pct,
    })
    return response.json().get("discounted_amount", 0.0)
