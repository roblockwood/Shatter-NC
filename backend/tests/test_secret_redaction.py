"""Tests for secret redaction helpers."""
from app.utils.secret_redaction import (
    MASKED_SECRET,
    merge_channel_config_update,
    sanitize_channel_config,
)


def test_sanitize_channel_config_masks_secrets():
    config = {"to": "ops@example.com", "password": "secret123", "smtp_host": "smtp.example.com"}
    sanitized = sanitize_channel_config(config)
    assert sanitized["password"] == MASKED_SECRET
    assert sanitized["to"] == "ops@example.com"
    assert sanitized["smtp_host"] == "smtp.example.com"


def test_merge_channel_config_update_preserves_existing_secret():
    existing = {"to": "ops@example.com", "password": "secret123"}
    incoming = {"to": "other@example.com", "password": ""}
    merged = merge_channel_config_update(existing, incoming)
    assert merged["to"] == "other@example.com"
    assert merged["password"] == "secret123"


def test_merge_channel_config_update_ignores_masked_secret():
    existing = {"to": "ops@example.com", "password": "secret123"}
    incoming = {"password": MASKED_SECRET}
    merged = merge_channel_config_update(existing, incoming)
    assert merged["password"] == "secret123"
