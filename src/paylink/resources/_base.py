"""Shared plumbing for the resource namespaces."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from .._field_orders import EndpointSpec
from .._sign_request import build_signed_body
from ..config import ResolvedConfig
from ..http import execute

__all__ = ["Resource"]


class Resource:
    def __init__(self, config: ResolvedConfig) -> None:
        self._config = config

    def _post(
        self,
        spec: EndpointSpec,
        params: Mapping[str, Any],
        *,
        idempotency_key: Optional[str] = None,
        replay_safe: Optional[bool] = None,
    ) -> Any:
        body = build_signed_body(
            spec, params, self._config.public_token, self._config.hash_token
        )

        return execute(
            self._config,
            method="POST",
            path=spec.path,
            body=body,
            idempotency_key=idempotency_key,
            replay_safe=replay_safe,
        )
