# Database Layer

## fetch_user(cursor, user_id)
Fetches a single user row from the `users` table.

## insert_record(cursor, table, data)
Inserts a dict of column→value pairs into the named table. Returns the new row ID.

## delete_record(cursor, table, record_id)
Deletes a row by ID. Returns `True` if successful.
