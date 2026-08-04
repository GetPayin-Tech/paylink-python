"""Payment operations on an existing invoice."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Union

from .._field_orders import (
    PAYMENT_CHECK_STATUS,
    PAYMENT_REFUND,
    PAYMENT_REVERSE_AUTHORIZATION,
    PAYMENT_SETTLE,
    PAYMENT_VOID,
)
from ..types import PaymentResult, RefundResult
from ._base import Resource

__all__ = ["Payments"]

Numeric = Union[int, float, str]


class Payments(Resource):
    def void(self, *, invoice_id: Numeric, idempotency_key: Optional[str] = None) -> PaymentResult:
        """Void a paid invoice (``POST /api/integration/void``)."""
        return _payment(
            self._post(PAYMENT_VOID, {"invoice_id": invoice_id}, idempotency_key=idempotency_key)
        )

    def refund(
        self,
        *,
        invoice_id: Numeric,
        amount: Numeric,
        idempotency_key: Optional[str] = None,
    ) -> RefundResult:
        """Refund a paid invoice, full or partial (``POST /api/integration/refund``).

        Pass ``idempotency_key`` to make retries safe.
        """
        data = self._post(
            PAYMENT_REFUND,
            {"invoice_id": invoice_id, "amount": amount},
            idempotency_key=idempotency_key,
        )

        return RefundResult(
            invoice_id=data["invoice_id"],
            paid_status=data["paid_status"],
            auth_code=data.get("auth_code"),
            refund_amount=data.get("refund_amount"),
        )

    def settle(
        self,
        *,
        invoice_id: Numeric,
        amount: Numeric,
        idempotency_key: Optional[str] = None,
    ) -> PaymentResult:
        """Capture an authorized invoice (``POST /api/integration/settle``)."""
        return _payment(
            self._post(
                PAYMENT_SETTLE,
                {"invoice_id": invoice_id, "amount": amount},
                idempotency_key=idempotency_key,
            )
        )

    def reverse_authorization(
        self, *, invoice_id: Numeric, idempotency_key: Optional[str] = None
    ) -> PaymentResult:
        """Reverse an authorization hold (``POST /api/integration/reverse-authorization``)."""
        return _payment(
            self._post(
                PAYMENT_REVERSE_AUTHORIZATION,
                {"invoice_id": invoice_id},
                idempotency_key=idempotency_key,
            )
        )

    def check_status(self, *, invoice_id: Numeric) -> PaymentResult:
        """Query the current gateway status of an invoice.

        ``POST /api/integration/check-status``. A pure read despite being a POST,
        so it is retried on transient failures.
        """
        return _payment(
            self._post(PAYMENT_CHECK_STATUS, {"invoice_id": invoice_id}, replay_safe=True)
        )


def _payment(data: Mapping[str, Any]) -> PaymentResult:
    return PaymentResult(
        invoice_id=data["invoice_id"],
        paid_status=data["paid_status"],
        auth_code=data.get("auth_code"),
    )
