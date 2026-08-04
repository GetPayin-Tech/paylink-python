"""Inbound webhook signature verification."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional, Union

from .coerce import coerce_to_string
from .config import ResolvedConfig
from .errors import PaylinkError, PaylinkSignatureError
from .signature import build_signature, signatures_equal
from .types import WebhookEvent

__all__ = ["Webhooks"]

#: Always-signed webhook fields, in concatenation order (``None`` renders as '').
_ALWAYS_SIGNED = ("success", "invoice_id", "invoice_status", "message")

# Optionally-signed fields, appended in this order only when the payload carries
# them.
#
# Membership here is an EITHER/OR, not an additive safety net. The server signs
# by opt-OUT: ``PaymentIntegrationWebhookJob`` copies the whole payload and
# ``unset()``s a fixed exclusion list before hashing. So a new webhook field is
# signed if it is added before that ``unset()``, and unsigned if it is added
# after — which is exactly what ``auth_code`` does, and why ``auth_code`` is
# deliberately absent here. For any new field: if the server signs it, it MUST be
# listed here in the server's order; if the server sends it unsigned, it MUST NOT
# be listed. See CONTRIBUTING.md.
_OPTIONAL_SIGNED = ("mandate_id", "external_reference", "subscription_status")

WebhookInput = Union[Mapping[str, Any], str, bytes]


class Webhooks:
    """Verify inbound webhook signatures against the integration ``hash_token``."""

    def __init__(self, config: ResolvedConfig) -> None:
        self._config = config

    def verify(self, payload: WebhookInput, *, hash_token: Optional[str] = None) -> WebhookEvent:
        """Verify a webhook and return the parsed event.

        Accepts the decoded mapping, or the raw JSON string/bytes. Raises
        :class:`PaylinkSignatureError` if the signature is missing or does not
        match.

        Note: PayLink webhook signatures carry no timestamp, so this does not
        protect against replay — pair it with your own idempotency on
        ``invoice_id``.
        """
        parsed = self._parse(payload)
        secret = hash_token if hash_token is not None else self._config.hash_token

        provided = parsed.get("signature")
        if not isinstance(provided, str) or provided == "":
            raise PaylinkSignatureError("Webhook payload is missing a signature.")

        if not signatures_equal(self._compute_signature(parsed, secret), provided):
            raise PaylinkSignatureError()

        return self._to_event(parsed)

    def is_valid(self, payload: WebhookInput, *, hash_token: Optional[str] = None) -> bool:
        """Non-throwing variant of :meth:`verify`."""
        try:
            self.verify(payload, hash_token=hash_token)
            return True
        except PaylinkSignatureError:
            return False

    def _compute_signature(self, payload: Mapping[str, Any], hash_token: str) -> str:
        values = [coerce_to_string(payload.get(key)) for key in _ALWAYS_SIGNED]

        for key in _OPTIONAL_SIGNED:
            if key in payload:
                values.append(coerce_to_string(payload.get(key)))

        return build_signature(values, hash_token)

    def _parse(self, payload: WebhookInput) -> Dict[str, Any]:
        if isinstance(payload, Mapping):
            return dict(payload)

        raw = payload.decode("utf-8") if isinstance(payload, bytes) else payload

        try:
            decoded = json.loads(raw)
        except ValueError as error:
            raise PaylinkError("Webhook payload is not valid JSON.", cause=error) from error

        if not isinstance(decoded, dict):
            raise PaylinkError("Webhook payload must decode to a JSON object.")

        return decoded

    def _to_event(self, payload: Mapping[str, Any]) -> WebhookEvent:
        return WebhookEvent(
            event=payload.get("event"),
            event_triggered_at=payload.get("event_triggered_at"),
            timezone=payload.get("timezone"),
            success=_as_int(payload.get("success")) == 1,
            invoice_id=payload.get("invoice_id"),
            invoice_status=payload.get("invoice_status"),
            message=payload.get("message"),
            auth_code=payload.get("auth_code"),
            mandate_id=payload.get("mandate_id"),
            external_reference=payload.get("external_reference"),
            subscription_status=payload.get("subscription_status"),
            raw=dict(payload),
        )


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
