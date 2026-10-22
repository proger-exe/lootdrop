"""Async CryptAPI HTTP client."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.integrations.cryptapi.dto import (
    CryptAPIConvertResult,
    CryptAPICreateAddress,
    event_from_log,
)


class CryptAPIError(RuntimeError):
    """Raised when CryptAPI returns an unusable response."""


@dataclass(slots=True)
class CryptAPIClient:
    """Small wrapper around CryptAPI endpoints."""

    base_url: str
    session: Any
    timeout_seconds: int

    @retry(
        retry=retry_if_exception_type((TimeoutError, ConnectionError, CryptAPIError)),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(3),
    )
    async def convert(self, ticker: str, amount_minor: int, currency: str) -> CryptAPIConvertResult:
        """Convert a base currency amount into a coin amount."""

        amount = Decimal(amount_minor) / Decimal("100")
        payload = await self._get_json(
            f"/{ticker}/convert/",
            {"value": str(amount), "from": currency},
        )
        return CryptAPIConvertResult.from_payload(payload)

    @retry(
        retry=retry_if_exception_type((TimeoutError, ConnectionError, CryptAPIError)),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(3),
    )
    async def create_address(
        self,
        ticker: str,
        callback_url: str,
        destination_address: str,
        confirmations: int,
    ) -> CryptAPICreateAddress:
        """Create an incoming payment address."""

        payload = await self._get_json(
            f"/{ticker}/create/",
            {
                "callback": callback_url,
                "address": destination_address,
                "pending": "1",
                "confirmations": str(confirmations),
                "post": "1",
                "convert": "1",
            },
        )
        return CryptAPICreateAddress.from_payload(payload, callback_url)

    async def logs(self, ticker: str, callback_url: str) -> list[dict[str, Any]]:
        """Read CryptAPI callback logs for one invoice callback URL."""

        payload = await self._get_json(f"/{ticker}/logs/", {"callback": callback_url})
        callbacks = payload.get("callbacks") or payload.get("logs") or []
        if not isinstance(callbacks, list):
            raise CryptAPIError("CryptAPI logs response is not a list")
        return [item for item in callbacks if isinstance(item, dict)]

    async def poll_events(self, ticker: str, callback_url: str) -> list[Any]:
        """Return normalized payment events from logs."""

        return [event_from_log(item, ticker) for item in await self.logs(ticker, callback_url)]

    async def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        """Perform a GET request and decode JSON."""

        url = f"{self.base_url.rstrip('/')}{path}"
        query = "&".join(f"{quote(key)}={quote(value)}" for key, value in params.items())
        async with self.session.get(f"{url}?{query}", timeout=self.timeout_seconds) as response:
            if response.status >= 500:
                raise CryptAPIError(f"CryptAPI server error: {response.status}")
            if response.status >= 400:
                text = await response.text()
                raise CryptAPIError(f"CryptAPI request rejected: {response.status} {text[:120]}")
            payload = await response.json()
        if not isinstance(payload, dict):
            raise CryptAPIError("CryptAPI response is not an object")
        return payload
