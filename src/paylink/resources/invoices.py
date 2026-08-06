"""Checkout invoices."""

from __future__ import annotations

from typing import Optional, Union

from .._field_orders import INVOICE_CREATE
from ..types import CreateInvoiceResult
from ._base import Resource

__all__ = ["Invoices"]

Numeric = Union[int, float, str]


class Invoices(Resource):
    def create(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        order_title: str,
        order_amount: Numeric,
        currency: str,
        address: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        state: Optional[str] = None,
        redirection_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        order_details: Optional[str] = None,
        payment_mode: Optional[str] = None,
        iframe: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
    ) -> CreateInvoiceResult:
        """Create an invoice and return a temporary signed checkout URL.

        ``POST /api/v2/integration/init``. Redirect the payer to ``checkout_url``.
        ``redirection_url``/``webhook_url`` must be HTTPS URLs on the
        integration's registered domain; ``payment_mode`` (``capture`` or
        ``authorize``) is sent but excluded from the signature. ``iframe``
        (``True`` to enable embedded/iframe checkout) is likewise sent but
        excluded from the signature.
        """
        data = self._post(
            INVOICE_CREATE,
            {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "order_title": order_title,
                "order_amount": order_amount,
                "currency": currency,
                "address": address,
                "city": city,
                "country": country,
                "state": state,
                "redirection_url": redirection_url,
                "webhook_url": webhook_url,
                "order_details": order_details,
                "payment_mode": payment_mode,
                "iframe": iframe,
            },
            idempotency_key=idempotency_key,
        )

        return CreateInvoiceResult(
            checkout_url=data["checkout_url"],
            invoice_id=data["invoice_id"],
            expires_at=str(data["expires_at"]),
        )
