"""HMAC-SHA256 signing primitive, byte-compatible with the server.

Mirrors ``ExternalPaymentIntegration::buildSignatureString()`` on the server:
``base64_encode(hash_hmac('sha256', implode('', $data), $hashToken, true))``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Sequence

__all__ = ["build_signature", "signatures_equal"]


def build_signature(ordered_values: Sequence[str], hash_token: str) -> str:
    """HMAC-SHA256 over the empty-string join of the already-ordered values.

    Callers are responsible for supplying values in the exact wire order and
    coercing them with :func:`paylink.coerce.coerce_to_string`.
    """
    concatenated = "".join(ordered_values)
    digest = hmac.new(
        hash_token.encode("utf-8"),
        concatenated.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return base64.b64encode(digest).decode("ascii")


def signatures_equal(a: str, b: str) -> bool:
    """Constant-time comparison, equivalent to PHP's ``hash_equals``."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
