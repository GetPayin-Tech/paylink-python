"""Turn a snake_case params mapping into the signed wire body for an endpoint.

The returned dict is ready to POST as JSON: it holds the endpoint's fields, the
public ``token``, and the computed ``signature``. The signature is built from the
same coerced strings that go into the body, in the spec's order, skipping fields
the caller did not provide — exactly how the server reconstructs it from
``Arr::except($request->validated(), ...)``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from ._field_orders import EndpointSpec
from .coerce import coerce_to_string
from .signature import build_signature

__all__ = ["build_signed_body"]


def build_signed_body(
    spec: EndpointSpec,
    params: Mapping[str, Any],
    public_token: str,
    hash_token: str,
) -> Dict[str, str]:
    signed_values: List[str] = []
    body: Dict[str, str] = {}

    def append(value: Any, wire_key: str, signed: bool) -> None:
        if value is None:
            return
        string_value = coerce_to_string(value)
        body[wire_key] = string_value
        if signed:
            signed_values.append(string_value)

    for spec_field in spec.fields:
        append(params.get(spec_field.name), spec_field.name, spec_field.signed)

    if spec.country_state_block:
        _append_country_state_block(params, append)

    signature = build_signature(signed_values, hash_token)

    return {**body, "token": public_token, "signature": signature}


def _append_country_state_block(params: Mapping[str, Any], append: Any) -> None:
    country = params.get("country")

    if country == "US":
        append(params.get("us_state"), "us_state", True)
        append(params.get("postal_code"), "postal_code", True)
        return

    if country == "CA":
        append(params.get("canada_state"), "canada_state", True)
        append(params.get("postal_code"), "postal_code", True)
