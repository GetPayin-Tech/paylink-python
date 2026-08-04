"""Default HTTP transport, built on the standard library (no dependencies).

Any object matching the :data:`paylink.config.Transport` signature can be passed
to :class:`~paylink.client.PaylinkClient` instead — for a proxy-aware client, a
connection-pooled session, or a mock in tests.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Mapping, Optional

from .config import HttpResponse

__all__ = ["default_transport"]


def default_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: Optional[bytes],
    timeout: float,
) -> HttpResponse:
    """Send one request via :mod:`urllib.request` and return an HttpResponse.

    Raises on connection/timeout failures; HTTP error statuses (4xx/5xx) are
    returned as an :class:`HttpResponse` so the caller can read the error body.
    """
    request = urllib.request.Request(url, data=body, method=method)
    for name, value in headers.items():
        request.add_header(name, value)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _to_response(response.status, response.headers, response.read())
    except urllib.error.HTTPError as error:
        # A 4xx/5xx is a real HTTP response — surface it, don't treat it as a
        # connection failure. Reading the body gives the caller the error detail.
        return _to_response(error.code, error.headers, error.read())


def _to_response(status: int, headers: Mapping[str, str], raw: bytes) -> HttpResponse:
    text = raw.decode("utf-8", errors="replace") if raw else ""
    header_map = {key: value for key, value in headers.items()} if headers else {}

    return HttpResponse(status=status, text=text, headers=header_map)
