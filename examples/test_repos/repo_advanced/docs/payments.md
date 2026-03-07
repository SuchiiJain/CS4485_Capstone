# Payments API

## charge_card(user_id, amount, card_token)
Charges a user's saved card. Raises `ValueError` if amount is not positive.

## refund(transaction_id)
Issues a full refund for the given transaction. Returns `True` on success.

## get_balance(user_id)
Returns the current wallet balance for a user as a float.
