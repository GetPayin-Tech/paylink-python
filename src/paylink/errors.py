"""Exception hierarchy for the PayLink SDK.

Every failure raised by the SDK is a subclass of :class:`PaylinkError`, so a
caller can catch that to handle any PayLink failure generically, or narrow to a
subclass for specific handling.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

__all__ = [
    "PaylinkError",
    "PaylinkConfigError",
    "PaylinkApiError",
    "PaylinkSignatureError",
    "PaylinkConnectionError",
]


class PaylinkError(Exception):
    """Base class for every error raised by the SDK."""

    def __init__(self, message: str, *, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.message = message
        if cause is not None:
            self.__cause__ = cause


class PaylinkConfigError(PaylinkError):
    """Raised when the client is constructed with missing or invalid configuration.

    For example, an empty public/hash token or a non-positive timeout.
    """


class PaylinkApiError(PaylinkError):
    """Raised when the API responds with an error.

    The API returned either a non-2xx status or a ``{"success": false}``
    envelope. Carries the HTTP ``status``, the server-provided per-field
    ``errors`` mapping, and the ``raw`` response body (parsed, or the raw text if
    it was not valid JSON) for inspection.

    Use :attr:`is_idempotency_conflict` (409), :attr:`is_rate_limited` (429), and
    :attr:`is_forbidden` (403 — e.g. card tokenization or recurring payments not
    enabled for the account) to branch on the common cases.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int,
        errors: Optional[Mapping[str, Any]] = None,
        raw: Any = None,
        retry_after_seconds: Optional[float] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.errors = errors
        self.raw = raw
        #: Seconds the server asked us to wait before retrying, parsed from the
        #: ``Retry-After`` header (present on 429s). The SDK already honors this
        #: for replay-safe requests; it is exposed so callers can schedule their
        #: own retry of a request the SDK will not replay on its own.
        self.retry_after_seconds = retry_after_seconds

    @property
    def is_idempotency_conflict(self) -> bool:
        """True when the API rejected the request as a duplicate (HTTP 409)."""
        return self.status == 409

    @property
    def is_rate_limited(self) -> bool:
        """True when the request was rate limited (HTTP 429)."""
        return self.status == 429

    @property
    def is_forbidden(self) -> bool:
        """True when the API forbade the request (HTTP 403).

        Typically because the relevant product (e.g. card tokenization or
        recurring payments) is not enabled for the integration's account.
        """
        return self.status == 403


class PaylinkSignatureError(PaylinkError):
    """Raised by :meth:`Webhooks.verify` when a webhook signature does not match."""

    def __init__(self, message: str = "Webhook signature verification failed.") -> None:
        super().__init__(message)


class PaylinkConnectionError(PaylinkError):
    """Raised when the request never produced an HTTP response.

    A network failure, DNS error, or the configured timeout elapsing before the
    server replied.
    """
