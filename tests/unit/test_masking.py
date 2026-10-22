"""Tests for sensitive value masking."""

from app.utils.masking import mask_sensitive


def test_masks_email_local_part() -> None:
    """Email masking keeps domain and hides most of the name."""

    assert mask_sensitive("gambito@mail.test") == "ga***@mail.test"


def test_masks_short_value() -> None:
    """Short values are fully hidden."""

    assert mask_sensitive("abc") == "***"
