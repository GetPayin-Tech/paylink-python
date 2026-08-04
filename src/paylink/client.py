"""The PayLink integration client."""

from __future__ import annotations

from typing import Optional

from .config import Transport, resolve_config
from .resources import Cards, Invoices, Payments, Recurring, Vcc
from .webhooks import Webhooks

__all__ = ["PaylinkClient"]


class PaylinkClient:
    """Entry point to the PayLink integration API.

    Construct once with your integration's ``public_token`` and secret
    ``hash_token``, then use the resource namespaces:

    * ``invoices`` — create checkouts.
    * ``payments`` — void, refund, settle, reverse authorization, check status.
    * ``vcc`` — server-to-server raw-card charges.
    * ``cards`` — tokenize, charge, and revoke stored cards.
    * ``recurring`` — create and manage recurring mandates.
    * ``webhooks`` — verify inbound webhook signatures.

    Example::

        from paylink import PaylinkClient

        paylink = PaylinkClient(public_token=..., hash_token=...)
        checkout = paylink.invoices.create(
            first_name="John", last_name="Doe", email="john@example.com",
            order_title="Gold Plan", order_amount="250.00", currency="USD",
        )
        # redirect the payer to checkout.checkout_url

    :param public_token: identifies the integration; sent as ``token`` on every request.
    :param hash_token: secret signing key; server-side only, never expose to a client.
    :param base_url: API base URL; defaults to ``https://pay.getpayin.com``.
    :param timeout: per-attempt timeout in seconds (default 30). With retries,
        total wall time can exceed this.
    :param max_retries: how many times to RETRY a failed replay-safe request
        (default 2; ``0`` disables retries).
    :param transport: custom transport matching :data:`paylink.config.Transport`;
        defaults to a standard-library ``urllib`` transport.
    """

    def __init__(
        self,
        *,
        public_token: str,
        hash_token: str,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        transport: Optional[Transport] = None,
    ) -> None:
        config = resolve_config(
            public_token,
            hash_token,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            transport=transport,
        )

        self._config = config
        self.invoices = Invoices(config)
        self.payments = Payments(config)
        self.vcc = Vcc(config)
        self.cards = Cards(config)
        self.recurring = Recurring(config)
        self.webhooks = Webhooks(config)

    def __repr__(self) -> str:  # never surface the signing secret
        return (
            f"PaylinkClient(public_token={self._config.public_token!r}, "
            f"base_url={self._config.base_url!r})"
        )
