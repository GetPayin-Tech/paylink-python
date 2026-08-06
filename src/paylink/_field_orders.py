"""The signed-field registry.

Each :class:`EndpointSpec` lists the request fields for one endpoint in the EXACT
order the server concatenates them when it rebuilds the HMAC signature (the
FormRequest ``rules()`` order, minus ``token``/``signature``, and minus
``payment_mode`` which is sent but not signed). Getting this order right is the
whole job of the SDK — see the source FormRequests under
``app/Http/Requests/Application/ExternalPaymentIntegration``.

Rules encoded here, mirroring the server:

* Absent optional fields (``None`` at call time) are skipped entirely,
  contributing nothing to the body or the signature.
* ``signed=False`` fields (``payment_mode``, ``iframe``) are sent in the body but
  excluded from the signature.
* ``country_state_block`` appends the per-country state fields after the listed
  fields: US -> ``us_state``, ``postal_code``; CA -> ``canada_state``,
  ``postal_code``.

Because the SDK uses snake_case parameters that match the wire names, each field
is a single name that is both the keyword argument and the wire key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

__all__ = [
    "FieldSpec",
    "EndpointSpec",
    "INVOICE_CREATE",
    "PAYMENT_VOID",
    "PAYMENT_REFUND",
    "PAYMENT_SETTLE",
    "PAYMENT_REVERSE_AUTHORIZATION",
    "PAYMENT_CHECK_STATUS",
    "VCC_CHARGE",
    "CARD_TOKENIZE",
    "CARD_CHARGE",
    "CARD_REVOKE",
    "RECURRING_CREATE",
]


@dataclass(frozen=True)
class FieldSpec:
    """One request field: its snake_case wire name and whether it is signed."""

    name: str
    signed: bool = True


@dataclass(frozen=True)
class EndpointSpec:
    """One endpoint's signing contract: path, ordered fields, and state block."""

    path: str
    fields: Tuple[FieldSpec, ...]
    country_state_block: bool = field(default=False)


def _f(*names: str) -> Tuple[FieldSpec, ...]:
    return tuple(FieldSpec(name) for name in names)


INVOICE_CREATE = EndpointSpec(
    path="/api/v2/integration/init",
    fields=(
        *_f(
            "first_name",
            "last_name",
            "email",
            "order_title",
            "order_amount",
            "address",
            "city",
            "country",
            "state",
            "currency",
            "redirection_url",
            "webhook_url",
            "order_details",
        ),
        FieldSpec("payment_mode", signed=False),
        FieldSpec("iframe", signed=False),
    ),
)

_INVOICE_ID = FieldSpec("invoice_id")

PAYMENT_VOID = EndpointSpec(path="/api/integration/void", fields=(_INVOICE_ID,))

PAYMENT_REFUND = EndpointSpec(
    path="/api/integration/refund",
    fields=(_INVOICE_ID, FieldSpec("amount")),
)

PAYMENT_SETTLE = EndpointSpec(
    path="/api/integration/settle",
    fields=(_INVOICE_ID, FieldSpec("amount")),
)

PAYMENT_REVERSE_AUTHORIZATION = EndpointSpec(
    path="/api/integration/reverse-authorization",
    fields=(_INVOICE_ID,),
)

PAYMENT_CHECK_STATUS = EndpointSpec(
    path="/api/integration/check-status",
    fields=(_INVOICE_ID,),
)

VCC_CHARGE = EndpointSpec(
    path="/api/v2/integration/vcc/charge",
    country_state_block=True,
    fields=_f(
        "first_name",
        "last_name",
        "email",
        "phone",
        "currency_id",
        "price",
        "product",
        "reference_number",
        "card_number",
        "card_expiry_month",
        "card_expiry_year",
        "card_cvv",
        "country",
        "address",
        "city",
    ),
)

CARD_TOKENIZE = EndpointSpec(
    path="/api/v2/integration/tokens/card",
    country_state_block=True,
    fields=_f(
        "first_name",
        "last_name",
        "email",
        "customer_reference",
        "external_reference",
        "card_number",
        "card_expiry_month",
        "card_expiry_year",
        "card_cvv",
        "country",
        "address",
        "city",
    ),
)

CARD_CHARGE = EndpointSpec(
    path="/api/v2/integration/tokens/charge",
    country_state_block=True,
    fields=_f(
        "card_token",
        "initiator",
        "first_name",
        "last_name",
        "email",
        "currency",
        "price",
        "product",
        "reference_number",
        "country",
        "address",
        "city",
    ),
)

CARD_REVOKE = EndpointSpec(
    path="/api/v2/integration/tokens/revoke",
    fields=(FieldSpec("card_token"),),
)

RECURRING_CREATE = EndpointSpec(
    path="/api/v2/integration/recurring/init",
    fields=_f(
        "first_name",
        "last_name",
        "email",
        "order_title",
        "order_amount",
        "currency",
        "cadence_interval",
        "cadence_count",
        "total_cycles",
        "end_date",
        "consent_text",
        "external_reference",
        "redirection_url",
        "webhook_url",
    ),
)
