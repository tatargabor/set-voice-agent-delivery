"""Caller lookup — map incoming phone numbers to customer data."""

from pathlib import Path
import yaml

CONTACTS_FILE = Path(__file__).parent.parent / "contacts.yaml"


def lookup_caller(phone: str, contacts_path: Path = CONTACTS_FILE) -> dict:
    """Look up caller by phone number. Reloads file each call (hot reload).

    Returns dict with customer_name, company_name, script, and optional fields.
    Falls back to default section if phone not found.
    """
    if not contacts_path.exists():
        return {"customer_name": "", "company_name": "", "script": "website_followup"}

    with open(contacts_path) as f:
        data = yaml.safe_load(f)

    contacts = data.get("contacts", {})
    if phone in contacts:
        return contacts[phone]

    return data.get("default", {"customer_name": "", "company_name": "", "script": "website_followup"})
