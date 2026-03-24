"""Tests for call script loader."""

import pytest
from src.script_loader import load_script
from src.agent import CallContext


def test_load_website_followup():
    """Load website_followup.yaml with all variables."""
    ctx = load_script("website_followup", {
        "customer_name": "Kovács János",
        "company_name": "WebBuilder Kft.",
        "website_url": "https://kovacs.hu",
    })
    assert isinstance(ctx, CallContext)
    assert ctx.customer_name == "Kovács János"
    assert ctx.company_name == "WebBuilder Kft."
    assert ctx.website_url == "https://kovacs.hu"
    assert len(ctx.purpose) > 0


def test_missing_variable_raises():
    """Missing required variable should raise ValueError."""
    with pytest.raises(ValueError, match="Missing required variables"):
        load_script("website_followup", {
            "customer_name": "Test",
            # missing company_name and website_url
        })


def test_nonexistent_script_raises():
    """Loading a script that doesn't exist should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Call script not found"):
        load_script("nonexistent_script", {})
