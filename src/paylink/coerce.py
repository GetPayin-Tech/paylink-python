"""Canonical value → string coercion.

Used for BOTH the signature concatenation and the JSON request body. Deriving
both from this single function guarantees the bytes we sign are exactly the bytes
we send, so the server (which re-stringifies the decoded JSON when it rebuilds
the signature) always agrees.

``None`` becomes an empty string — matching PHP's ``implode``, which renders null
as ``''`` (relevant for webhook fields such as a null ``message``). For request
bodies, absent optional fields are dropped *before* reaching this function, so
they never contribute an empty string.
"""

from __future__ import annotations

import math
from typing import Any

from .errors import PaylinkError

__all__ = ["coerce_to_string"]


def coerce_to_string(value: Any) -> str:
    """Coerce a scalar to the exact string sent on the wire and signed."""
    if value is None:
        return ""

    # bool is a subclass of int, so it must be checked first.
    if isinstance(value, bool):
        return "1" if value else "0"

    if isinstance(value, str):
        return value

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if not math.isfinite(value):
            raise PaylinkError(f"Cannot serialize non-finite number: {value}")
        # Render an integer-valued float without a trailing ".0" so it matches a
        # plain integer amount on the wire (and the JS/PHP SDKs).
        if value.is_integer():
            return str(int(value))
        return repr(value)

    raise PaylinkError(f"Cannot serialize value of type {type(value).__name__}.")
