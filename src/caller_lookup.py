"""Caller lookup — map incoming phone numbers to customer data."""

from pathlib import Path
import yaml

CONTACTS_FILE = Path(__file__).parent.parent / "contacts.yaml"


def lookup_caller(phone: str, contacts_path: Path = CONTACTS_FILE) -> dict:
    """Look up caller by phone number or browser identity. Reloads file each call (hot reload).

    Handles both phone numbers (+36...) and browser identities (client:gabor).
    Returns dict with customer_name, company_name, script, and optional fields.
    Falls back to default section if not found.
    """
    if not contacts_path.exists():
        return {"customer_name": "", "company_name": "", "script": "website_followup"}

    with open(contacts_path) as f:
        data = yaml.safe_load(f)

    contacts = data.get("contacts", {})

    # Direct phone match
    if phone in contacts:
        return contacts[phone]

    # Browser client identity: "client:gabor" → look up by name
    if phone.startswith("client:"):
        identity = phone.split(":", 1)[1]
        # Search contacts by customer_name (case-insensitive)
        for _phone, info in contacts.items():
            if info.get("customer_name", "").lower() == identity.lower():
                return info

    return data.get("default", {"customer_name": "", "company_name": "", "script": "website_followup"})
