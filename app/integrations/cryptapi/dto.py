"""CryptAPI DTO parsing."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.payments.entities import ProviderPaymentEvent


@dataclass(frozen=True, slots=True)
class CryptAPICreateAddress:
    """Response from CryptAPI create endpoint."""

    address_in: str
    callback_url: str
    raw: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any], callback_url: str) -> "CryptAPICreateAddress":
        """Parse a create-address response."""

        address = payload.get("address_in") or payload.get("address")
        if not isinstance(address, str) or not address:
            raise ValueError("CryptAPI create response has no address_in")
        return cls(address_in=address, callback_url=callback_url, raw=payload)


@dataclass(frozen=True, slots=True)
class CryptAPIConvertResult:
    """Response from CryptAPI convert endpoint."""

    value_coin: Decimal
    rate: Decimal
    raw: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "CryptAPIConvertResult":
        """Parse a conversion response."""

        value = payload.get("value_coin") or payload.get("value")
        rate = payload.get("exchange_rate") or payload.get("rate") or "0"
        if value is None:
            raise ValueError("CryptAPI convert response has no value")
        return cls(value_coin=Decimal(str(value)), rate=Decimal(str(rate)), raw=payload)


def event_from_log(payload: dict[str, Any], ticker: str) -> ProviderPaymentEvent:
    """Normalize one CryptAPI log callback payload."""

    uuid = str(payload.get("uuid") or payload.get("payment_id") or payload.get("txid_in") or "")
    txid_in = str(payload.get("txid_in") or payload.get("txid") or "")
    if not uuid or not txid_in:
        raise ValueError("CryptAPI log event has no stable identity")
    pending_value = payload.get("pending")
    pending = str(pending_value).lower() in {"1", "true", "yes"}
    return ProviderPaymentEvent(
        provider_uuid=uuid,
        ticker=ticker,
        address_in=str(payload.get("address_in") or payload.get("address") or ""),
        address_out=str(payload.get("address_out") or payload.get("address_forwarded") or ""),
        txid_in=txid_in,
        txid_out=str(payload.get("txid_out") or "") or None,
        pending=pending,
        received_amount=Decimal(str(payload.get("value_coin") or payload.get("value") or "0")),
        forwarded_amount=(
            Decimal(str(payload["value_forwarded_coin"]))
            if payload.get("value_forwarded_coin") is not None
            else None
        ),
        confirmations=int(payload.get("confirmations") or 0),
        raw_payload=payload,
    )
