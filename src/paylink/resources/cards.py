"""Card tokenization and stored-card charges."""

from __future__ import annotations

from typing import Optional, Union

from .._field_orders import CARD_CHARGE, CARD_REVOKE, CARD_TOKENIZE
from ..types import CardInfo, ChargeTokenResult, RevokeTokenResult, TokenizeCardResult
from ._base import Resource

__all__ = ["Cards"]

Numeric = Union[int, float, str]


class Cards(Resource):
    def tokenize(
        self,
        *,
        first_name: str,
        last_name: str,
        card_number: str,
        card_expiry_month: Numeric,
        card_expiry_year: Numeric,
        country: str,
        address: str,
        city: str,
        email: Optional[str] = None,
        customer_reference: Optional[str] = None,
        external_reference: Optional[str] = None,
        card_cvv: Optional[str] = None,
        us_state: Optional[str] = None,
        canada_state: Optional[str] = None,
        postal_code: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> TokenizeCardResult:
        """Vault a card and return a reusable token (``POST /api/v2/integration/tokens/card``)."""
        data = self._post(
            CARD_TOKENIZE,
            {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "customer_reference": customer_reference,
                "external_reference": external_reference,
                "card_number": card_number,
                "card_expiry_month": card_expiry_month,
                "card_expiry_year": card_expiry_year,
                "card_cvv": card_cvv,
                "country": country,
                "address": address,
                "city": city,
                "us_state": us_state,
                "canada_state": canada_state,
                "postal_code": postal_code,
            },
            idempotency_key=idempotency_key,
        )

        card = data.get("card") or {}

        return TokenizeCardResult(
            token=data["token"],
            card=CardInfo(
                brand=card.get("brand"),
                last4=card.get("last4"),
                exp_month=card.get("exp_month"),
                exp_year=card.get("exp_year"),
            ),
            status=data["status"],
        )

    def charge(
        self,
        *,
        card_token: str,
        initiator: str,
        first_name: str,
        last_name: str,
        currency: str,
        price: Numeric,
        product: str,
        country: str,
        address: str,
        city: str,
        email: Optional[str] = None,
        reference_number: Optional[str] = None,
        us_state: Optional[str] = None,
        canada_state: Optional[str] = None,
        postal_code: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> ChargeTokenResult:
        """Charge a previously vaulted card (``POST /api/v2/integration/tokens/charge``).

        ``initiator`` is ``"merchant"`` or ``"customer"``.
        """
        data = self._post(
            CARD_CHARGE,
            {
                "card_token": card_token,
                "initiator": initiator,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "currency": currency,
                "price": price,
                "product": product,
                "reference_number": reference_number,
                "country": country,
                "address": address,
                "city": city,
                "us_state": us_state,
                "canada_state": canada_state,
                "postal_code": postal_code,
            },
            idempotency_key=idempotency_key,
        )

        return ChargeTokenResult(
            invoice_id=data["invoice_id"],
            invoice_number=data["invoice_number"],
            amount=data["amount"],
            currency=data["currency"],
            paid_status=data["paid_status"],
            card_token=data["card_token"],
        )

    def revoke(self, *, card_token: str) -> RevokeTokenResult:
        """Revoke a vaulted card token (``POST /api/v2/integration/tokens/revoke``)."""
        data = self._post(CARD_REVOKE, {"card_token": card_token})

        return RevokeTokenResult(message=data.get("message") or "Token revoked.")
