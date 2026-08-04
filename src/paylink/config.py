"""Client configuration, the transport contract, and config resolution."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional

from .errors import PaylinkConfigError

__all__ = ["HttpResponse", "Transport", "ResolvedConfig", "resolve_config"]

DEFAULT_BASE_URL = "https://pay.getpayin.com"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BASE_DELAY_SECONDS = 0.25


@dataclass(frozen=True)
class HttpResponse:
    """The minimal response the SDK relies on.

    A custom :data:`Transport` returns this. ``headers`` is looked up
    case-insensitively via :meth:`get_header`.
    """

    status: int
    text: str
    headers: Mapping[str, str] = field(default_factory=dict)

    def get_header(self, name: str) -> Optional[str]:
        lowered = name.lower()
        for key, value in self.headers.items():
            if key.lower() == lowered:
                return value
        return None


#: A transport sends one request and returns an :class:`HttpResponse`. It must
#: raise on a network failure or timeout (the SDK wraps that in a
#: ``PaylinkConnectionError``). Inject one to mock the network in tests or to use
#: a proxy-aware HTTP client.
Transport = Callable[[str, str, Mapping[str, str], Optional[bytes], float], HttpResponse]


@dataclass
class ResolvedConfig:
    """Validated, internal configuration passed to every resource."""

    public_token: str
    hash_token: str
    base_url: str
    timeout: float
    max_retries: int
    transport: Transport
    retry_base_delay_seconds: float = DEFAULT_RETRY_BASE_DELAY_SECONDS
    #: Injectable sleep/rng so retry backoff is deterministic under test.
    sleep: Callable[[float], None] = time.sleep
    rng: Callable[[], float] = random.random

    def __repr__(self) -> str:  # keep the signing secret out of logs/tracebacks
        return (
            f"ResolvedConfig(public_token={self.public_token!r}, hash_token='***', "
            f"base_url={self.base_url!r}, timeout={self.timeout!r}, "
            f"max_retries={self.max_retries!r})"
        )


def resolve_config(
    public_token: str,
    hash_token: str,
    *,
    base_url: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    transport: Optional[Transport] = None,
) -> ResolvedConfig:
    public = _require_non_empty(public_token, "public_token")
    secret = _require_non_empty(hash_token, "hash_token")

    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        raise PaylinkConfigError("timeout must be a positive number of seconds.")

    if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries < 0:
        raise PaylinkConfigError("max_retries must be a non-negative integer.")

    resolved_transport = transport
    if resolved_transport is None:
        from ._transport import default_transport

        resolved_transport = default_transport

    return ResolvedConfig(
        public_token=public,
        hash_token=secret,
        base_url=(base_url or DEFAULT_BASE_URL).rstrip("/"),
        timeout=float(timeout),
        max_retries=max_retries,
        transport=resolved_transport,
    )


def _require_non_empty(value: Optional[str], name: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise PaylinkConfigError(f"{name} is required and must be a non-empty string.")
    return value
