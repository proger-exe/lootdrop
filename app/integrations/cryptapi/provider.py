"""CryptAPI PaymentProvider implementation."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.config.models import CryptAPISettings, PaymentSettings
from app.data.enums import PaymentStatus
from app.domain.payments.entities import PaymentInvoice, PaymentMethod, ProviderPaymentEvent
from app.integrations.cryptapi.client import CryptAPIClient


@dataclass(slots=True)
class CryptAPIPaymentProvider:
    """Polling-based CryptAPI provider implementation."""

    client: CryptAPIClient
    cryptapi_settings: CryptAPISettings
    payment_settings: PaymentSettings
    base_currency: str

    async def create_invoice(
        self,
        method: PaymentMethod,
        order_id: int,
        amount_minor: int,
    ) -> PaymentInvoice:
        """Create an invoice and unique CryptAPI callback identifier."""

        nonce = secrets.token_urlsafe(32)
        public_id = f"pay_{secrets.token_urlsafe(12)}"
        callback_url = (
            f"{self.cryptapi_settings.callback_base_url.rstrip('/')}/cryptapi/poll-marker"
            f"?payment_id={public_id}&nonce={nonce}"
        )
        conversion = await self.client.convert(method.ticker, amount_minor, self.base_currency)
        created = await self.client.create_address(
            method.ticker,
            callback_url,
            method.destination_address,
            method.confirmations_required,
        )
        now = datetime.now(UTC)
        return PaymentInvoice(
            id=None,
            public_id=public_id,
            order_id=order_id,
            provider="cryptapi",
            ticker=method.ticker,
            network=method.network,
            asset=method.asset,
            base_amount_minor=amount_minor,
            base_currency=self.base_currency,
            expected_coin_amount=conversion.value_coin,
            received_coin_amount=Decimal("0"),
            forwarded_coin_amount=None,
            exchange_rate=conversion.rate,
            destination_address=method.destination_address,
            payment_address=created.address_in,
            callback_url=callback_url,
            callback_nonce_hash=hashlib.sha256(nonce.encode()).hexdigest(),
            provider_payload={"convert": conversion.raw, "create": created.raw},
            minimum_transaction_coin=Decimal("0"),
            expires_at=now + timedelta(minutes=self.payment_settings.invoice_ttl_minutes),
            status=PaymentStatus.CREATED,
            created_at=now,
            updated_at=now,
            next_poll_at=now,
        )

    async def poll_invoice(self, invoice: PaymentInvoice) -> list[ProviderPaymentEvent]:
        """Poll CryptAPI logs for an invoice."""

        return await self.client.poll_events(invoice.ticker, invoice.callback_url)

    async def reconcile_invoice(self, invoice: PaymentInvoice) -> list[ProviderPaymentEvent]:
        """Run a full reconciliation using the same logs source."""

        return await self.poll_invoice(invoice)
