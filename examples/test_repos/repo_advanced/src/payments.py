"""
payments.py — Payment processing logic.
"""
import requests


def charge_card(user_id: int, amount: float, card_token: str) -> dict:
    """Charge a user's card via the payment gateway."""
    if amount <= 0:
        raise ValueError("Amount must be positive.")
    response = requests.post("https://payments.example.com/charge", json={
        "user": user_id,
        "amount": amount,
        "token": card_token,
    })
    return response.json()


def refund(transaction_id: str) -> bool:
    """Issue a refund for a transaction."""
    response = requests.post("https://payments.example.com/refund", json={
        "transaction_id": transaction_id,
    })
    return response.status_code == 200


def get_balance(user_id: int) -> float:
    """Return the current balance for a user."""
    response = requests.get(f"https://payments.example.com/balance/{user_id}")
    data = response.json()
    return data.get("balance", 0.0)
