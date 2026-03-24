"""Tests for caller lookup."""

from src.caller_lookup import lookup_caller


def test_known_number(tmp_path):
    contacts = tmp_path / "contacts.yaml"
    contacts.write_text("""
contacts:
  "+36301234567":
    customer_name: "Test User"
    company_name: "Test Co"
    script: "website_followup"

default:
  customer_name: ""
  company_name: "Default Co"
  script: "website_followup"
""")
    result = lookup_caller("+36301234567", contacts)
    assert result["customer_name"] == "Test User"
    assert result["company_name"] == "Test Co"


def test_unknown_number(tmp_path):
    contacts = tmp_path / "contacts.yaml"
    contacts.write_text("""
contacts:
  "+36301234567":
    customer_name: "Test User"
    company_name: "Test Co"
    script: "website_followup"

default:
  customer_name: ""
  company_name: "Default Co"
  script: "website_followup"
""")
    result = lookup_caller("+36999999999", contacts)
    assert result["customer_name"] == ""
    assert result["company_name"] == "Default Co"


def test_missing_file(tmp_path):
    result = lookup_caller("+36301234567", tmp_path / "nonexistent.yaml")
    assert result["customer_name"] == ""
