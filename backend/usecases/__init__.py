"""Usecases: one function per user action (F §2.2; slice 1 creates the package).

Layer rules:
- A usecase takes church_id and user_id as uuid.UUID (coerced with
  db.ids.as_uuid by the caller or the usecase itself).
- It owns the transaction: `with session_scope() as s:` around every write
  that must be atomic, passing `session=s` to the repo functions it calls.
- It raises domain_errors.DomainError subclasses with the exact user-facing
  messages; routes never catch them (api/errors.py maps them).
- It never imports fastapi, starlette or streamlit
  (test_no_streamlit_in_core.py checks this).
"""
