#!/usr/bin/env python3
"""
Saved email contacts for worship bulletin distribution.
Stored in data/email_contacts.json.
"""

import json
import os
from typing import Dict, List

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CONTACTS_FILE = os.path.join(DATA_DIR, "email_contacts.json")

DEFAULT_CONTACTS = [
    {"name": "Mary Swope", "email": "swopemom@gmail.com"},
    {"name": "Marilyn Stevens", "email": "office@connerpres.org"},
]


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_contacts() -> List[Dict[str, str]]:
    """Load saved contacts. Returns list of {name, email}. Seeds defaults if file missing."""
    _ensure_data_dir()
    if not os.path.isfile(CONTACTS_FILE):
        save_contacts(DEFAULT_CONTACTS)
        return DEFAULT_CONTACTS
    try:
        with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        contacts = data.get("contacts", [])
        return contacts if isinstance(contacts, list) else []
    except Exception:
        return DEFAULT_CONTACTS.copy()


def save_contacts(contacts: List[Dict[str, str]]) -> None:
    """Save contacts to JSON."""
    _ensure_data_dir()
    with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"contacts": contacts}, f, indent=2)


def get_contacts_for_display() -> List[Dict[str, str]]:
    """Return contacts for UI display. Ensures defaults exist if file is empty."""
    contacts = load_contacts()
    if not contacts:
        save_contacts(DEFAULT_CONTACTS)
        return DEFAULT_CONTACTS
    return contacts
