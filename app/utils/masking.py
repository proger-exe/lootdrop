"""Helpers for masking sensitive values."""


def mask_sensitive(value: str) -> str:
    """Mask a value for logs and broad notifications."""

    if "@" in value:
        name, domain = value.split("@", 1)
        return f"{name[:2]}***@{domain}"
    if len(value) <= 4:
        return "***"
    return f"{value[:4]}***"
