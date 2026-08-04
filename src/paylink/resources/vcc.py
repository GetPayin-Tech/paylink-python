"""Server-to-server raw-card charges."""

from __future__ import annotations

from typing import Optional, Union

from .._field_orders import VCC_CHARGE
from ..types import VccChargeResult
from ._base import Resource

__all__ = ["Vcc"]

Numeric = Union[int, float, str]


class Vcc(Resource):
    def charge(
        self,
        *,
        first_name: str,
        last_name: str,
        currency_id: Numeric,
        price: Numeric,
        product: str,
        card_number: str,
        card_expiry_month: Numeric,
        card_expiry_year: Numeric,
        country: str,
        address: str,
        city: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        reference_number: Optional[str] = None,
        card_cvv: Optional[str] = None,
        us_state: Optional[str] = None,
        canada_state: Optional[str] = None,
        postal_code: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> VccChargeResult:
        """Charge raw card data directly (``POST /api/v2/integration/vcc/charge``).

        Sending PAN/CVV through your server puts it in PCI scope — prefer the
        hosted checkout or card tokens where possible. For ``country="US"`` pass
        ``us_state`` + ``postal_code``; for ``"CA"`` pass ``canada_state`` +
        ``postal_code``.
        """
        data = self._post(
            VCC_CHARGE,
            {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "currency_id": currency_id,
                "price": price,
                "product": product,
                "reference_number": reference_number,
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

        return VccChargeResult(
            invoice_id=data["invoice_id"],
            invoice_number=data["invoice_number"],
            amount=data["amount"],
            currency=data["currency"],
            paid_status=data["paid_status"],
        )
