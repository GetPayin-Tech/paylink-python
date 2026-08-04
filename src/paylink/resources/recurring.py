"""Recurring mandates (subscriptions)."""

from __future__ import annotations

import urllib.parse
from typing import Any, Optional, Union

from .._field_orders import RECURRING_CREATE
from ..http import execute
from ..signature import build_signature
from ..types import CreateRecurringResult, MandateActionResult, MandateStatusResult
from ._base import Resource

__all__ = ["Recurring"]

Numeric = Union[int, float, str]


class Recurring(Resource):
    def create(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        order_title: str,
        order_amount: Numeric,
        currency: str,
        cadence_interval: str,
        cadence_count: Numeric,
        consent_text: str,
        total_cycles: Optional[Numeric] = None,
        end_date: Optional[str] = None,
        external_reference: Optional[str] = None,
        redirection_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> CreateRecurringResult:
        """Create a mandate and return a checkout URL for the first (setup) charge.

        ``POST /api/v2/integration/recurring/init``. ``cadence_interval`` is one
        of ``day``/``week``/``month``/``year``; ``end_date`` is ``YYYY-MM-DD`` and
        must be after today. Pass ``idempotency_key`` (or ``external_reference``)
        to make retries safe.
        """
        data = self._post(
            RECURRING_CREATE,
            {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "order_title": order_title,
                "order_amount": order_amount,
                "currency": currency,
                "cadence_interval": cadence_interval,
                "cadence_count": cadence_count,
                "total_cycles": total_cycles,
                "end_date": end_date,
                "consent_text": consent_text,
                "external_reference": external_reference,
                "redirection_url": redirection_url,
                "webhook_url": webhook_url,
            },
            idempotency_key=idempotency_key,
        )

        return CreateRecurringResult(
            checkout_url=data["checkout_url"],
            mandate_id=data["mandate_id"],
            invoice_id=data["invoice_id"],
            expires_at=str(data["expires_at"]),
        )

    def status(self, mandate_id: str) -> MandateStatusResult:
        """Query a mandate's status (``GET /api/v2/integration/recurring/{mandate}``)."""
        data = execute(
            self._config,
            method="GET",
            path=self._mandate_path(mandate_id),
            query={
                "token": self._config.public_token,
                "signature": self._sign_mandate(mandate_id),
            },
        )

        return MandateStatusResult(
            mandate_id=data["mandate_id"],
            status=data["status"],
            amount=data["amount"],
            completed_cycles=data["completed_cycles"],
            total_cycles=data.get("total_cycles"),
            next_charge_at=data.get("next_charge_at"),
        )

    def cancel(self, mandate_id: str) -> MandateActionResult:
        """Cancel a mandate (``POST /api/v2/integration/recurring/{mandate}/cancel``)."""
        return self._action(mandate_id, "cancel")

    def pause(self, mandate_id: str) -> MandateActionResult:
        """Pause a mandate (``POST /api/v2/integration/recurring/{mandate}/pause``)."""
        return self._action(mandate_id, "pause")

    def resume(self, mandate_id: str) -> MandateActionResult:
        """Resume a paused mandate (``POST /api/v2/integration/recurring/{mandate}/resume``)."""
        return self._action(mandate_id, "resume")

    def _action(self, mandate_id: str, action: str) -> MandateActionResult:
        data = execute(
            self._config,
            method="POST",
            path=f"{self._mandate_path(mandate_id)}/{action}",
            body={
                "token": self._config.public_token,
                "signature": self._sign_mandate(mandate_id),
            },
        )

        raw = data if isinstance(data, dict) else {}

        return MandateActionResult(status=raw.get("status"), raw=raw)

    def _mandate_path(self, mandate_id: str) -> str:
        return f"/api/v2/integration/recurring/{urllib.parse.quote(str(mandate_id), safe='')}"

    def _sign_mandate(self, mandate_id: str) -> str:
        return build_signature([str(mandate_id)], self._config.hash_token)
