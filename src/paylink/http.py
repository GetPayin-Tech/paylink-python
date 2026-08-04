"""Request execution: envelope handling, retries, and error mapping.

Retries transient failures (429, 5xx, connection errors, timeouts) with
exponential backoff and full jitter, honoring ``Retry-After`` when the server
sends it. A request is only ever replayed when doing so cannot double-charge:
GETs, requests carrying an ``Idempotency-Key``, and calls explicitly flagged
``replay_safe``. A bare ``vcc.charge`` or ``cards.charge`` is NEVER retried.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
from email.utils import parsedate_to_datetime
from time import time
from typing import Any, Dict, Mapping, Optional

from ._version import __version__
from .config import HttpResponse, ResolvedConfig
from .errors import PaylinkApiError, PaylinkConnectionError

__all__ = ["execute", "USER_AGENT"]

_RETRY_MAX_DELAY_SECONDS = 8.0

USER_AGENT = f"paylink-python/{__version__} python/{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def execute(
    config: ResolvedConfig,
    *,
    method: str,
    path: str,
    body: Optional[Mapping[str, str]] = None,
    query: Optional[Mapping[str, str]] = None,
    idempotency_key: Optional[str] = None,
    replay_safe: Optional[bool] = None,
) -> Any:
    """Run a request and return the ``data`` payload of the success envelope."""
    replayable = replay_safe if replay_safe is not None else (
        method == "GET" or idempotency_key is not None
    )
    max_attempts = config.max_retries + 1 if replayable else 1

    attempt = 1
    while True:
        try:
            return _attempt_request(
                config,
                method=method,
                path=path,
                body=body,
                query=query,
                idempotency_key=idempotency_key,
            )
        except (PaylinkApiError, PaylinkConnectionError) as error:
            if attempt >= max_attempts or not _is_transient(error):
                raise
            config.sleep(_backoff_seconds(config, error, attempt))
            attempt += 1


def _is_transient(error: Exception) -> bool:
    if isinstance(error, PaylinkConnectionError):
        return True
    if isinstance(error, PaylinkApiError):
        return error.status == 429 or error.status >= 500
    return False


def _backoff_seconds(config: ResolvedConfig, error: Exception, attempt: int) -> float:
    if isinstance(error, PaylinkApiError) and error.retry_after_seconds is not None:
        return min(error.retry_after_seconds, _RETRY_MAX_DELAY_SECONDS)

    ceiling = min(
        config.retry_base_delay_seconds * (2 ** (attempt - 1)),
        _RETRY_MAX_DELAY_SECONDS,
    )

    return config.rng() * ceiling


def _attempt_request(
    config: ResolvedConfig,
    *,
    method: str,
    path: str,
    body: Optional[Mapping[str, str]],
    query: Optional[Mapping[str, str]],
    idempotency_key: Optional[str],
) -> Any:
    url = _build_url(config.base_url, path, query)

    headers: Dict[str, str] = {"Accept": "application/json", "User-Agent": USER_AGENT}
    encoded_body: Optional[bytes] = None

    if method != "GET":
        headers["Content-Type"] = "application/json"
        encoded_body = json.dumps(body or {}).encode("utf-8")

    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    try:
        response = config.transport(method, url, headers, encoded_body, config.timeout)
    except Exception as error:  # noqa: BLE001 - any transport failure is a connection error
        raise PaylinkConnectionError(f"Request to {path} failed.", cause=error) from error

    return _handle_response(response, path)


def _handle_response(response: HttpResponse, path: str) -> Any:
    parsed = _safe_json_parse(response.text)
    ok = 200 <= response.status < 300

    if not ok or _is_failure_envelope(parsed):
        raise _to_api_error(
            response.status,
            parsed,
            response.text,
            _parse_retry_after(response.get_header("Retry-After")),
        )

    if isinstance(parsed, dict) and "data" in parsed:
        return parsed["data"]

    return parsed


def _build_url(base_url: str, path: str, query: Optional[Mapping[str, str]]) -> str:
    url = f"{base_url}{path}"
    if not query:
        return url
    return f"{url}?{urllib.parse.urlencode(dict(query))}"


def _safe_json_parse(text: str) -> Any:
    if text is None or text.strip() == "":
        return None
    try:
        return json.loads(text)
    except ValueError:
        return text


def _is_failure_envelope(parsed: Any) -> bool:
    return isinstance(parsed, dict) and parsed.get("success") is False


def _to_api_error(
    status: int,
    parsed: Any,
    raw_text: str,
    retry_after_seconds: Optional[float],
) -> PaylinkApiError:
    envelope = parsed if isinstance(parsed, dict) else {}
    nested = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
    message = _first_string(envelope.get("message"), nested.get("message")) or (
        f"PayLink API request failed with status {status}."
    )
    errors = envelope.get("errors") if isinstance(envelope.get("errors"), dict) else None

    return PaylinkApiError(
        message,
        status=status,
        errors=errors,
        raw=parsed if parsed is not None else raw_text,
        retry_after_seconds=retry_after_seconds,
    )


def _first_string(*values: Any) -> Optional[str]:
    for value in values:
        if isinstance(value, str) and value.strip() != "":
            return value
    return None


def _parse_retry_after(value: Optional[str]) -> Optional[float]:
    """``Retry-After`` is delta-seconds or an HTTP date. Returns seconds."""
    if value is None or value.strip() == "":
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None

    if parsed is None:
        return None

    return max(0.0, parsed.timestamp() - time())
