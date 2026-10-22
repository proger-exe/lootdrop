"""QR payload helpers."""

from decimal import Decimal


def build_payment_uri(asset: str, address: str, amount: Decimal | None = None) -> str:
    """Build a conservative URI for QR display."""

    normalized = asset.lower()
    if amount is None:
        return address
    if normalized in {"btc", "bitcoin"}:
        return f"bitcoin:{address}?amount={amount}"
    if normalized in {"ltc", "litecoin"}:
        return f"litecoin:{address}?amount={amount}"
    return address
