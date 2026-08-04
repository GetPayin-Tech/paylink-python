from __future__ import annotations

import json
import unittest

from paylink import PaylinkApiError, PaylinkClient, PaylinkConnectionError
from paylink.config import HttpResponse

CHECKOUT_OK = HttpResponse(
    status=200,
    text=json.dumps(
        {"success": True, "data": {"checkout_url": "https://x/y", "invoice_id": 1, "expires_at": "t"}}
    ),
)
PAYMENT_OK = HttpResponse(
    status=200,
    text=json.dumps({"success": True, "data": {"invoice_id": 1, "paid_status": "PAID", "auth_code": "A"}}),
)


def _err(status: int, headers: dict | None = None, **envelope) -> HttpResponse:
    body = {"success": False, **envelope}
    return HttpResponse(status=status, text=json.dumps(body), headers=headers or {})


class FakeTransport:
    def __init__(self, *responses) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, method, url, headers, body, timeout):  # noqa: ANN001
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _client(transport: FakeTransport, max_retries: int = 2) -> PaylinkClient:
    client = PaylinkClient(
        public_token="p", hash_token="s", max_retries=max_retries, transport=transport
    )
    # Deterministic, instant backoff for tests.
    client._config.sleep = lambda _seconds: None
    client._config.rng = lambda: 0.0
    return client


def _invoice(client: PaylinkClient, **overrides):
    return client.invoices.create(
        first_name="J", last_name="D", email="j@e.com",
        order_title="X", order_amount="10.00", currency="USD", **overrides,
    )


class RetryTest(unittest.TestCase):
    def test_success_envelope_is_unwrapped(self) -> None:
        transport = FakeTransport(CHECKOUT_OK)
        result = _invoice(_client(transport))
        self.assertEqual(result.invoice_id, 1)
        self.assertEqual(result.checkout_url, "https://x/y")

    def test_retries_429_when_idempotency_key_present(self) -> None:
        transport = FakeTransport(_err(429, {"Retry-After": "0"}, message="rate"), CHECKOUT_OK)
        result = _invoice(_client(transport), idempotency_key="k")
        self.assertEqual(result.invoice_id, 1)
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(transport.calls[0]["headers"]["Idempotency-Key"], "k")

    def test_bare_charge_is_not_retried(self) -> None:
        transport = FakeTransport(_err(500, message="boom"))
        client = _client(transport)
        with self.assertRaises(PaylinkApiError) as ctx:
            client.vcc.charge(
                first_name="S", last_name="S", currency_id=1, price="10", product="W",
                card_number="4111111111111111", card_expiry_month="12", card_expiry_year="2030",
                country="EG", address="A", city="C",
            )
        self.assertEqual(ctx.exception.status, 500)
        self.assertEqual(len(transport.calls), 1)  # never replayed

    def test_check_status_is_replay_safe(self) -> None:
        transport = FakeTransport(_err(503, message="down"), PAYMENT_OK)
        result = _client(transport).payments.check_status(invoice_id=1)
        self.assertEqual(result.paid_status, "PAID")
        self.assertEqual(len(transport.calls), 2)

    def test_max_retries_zero_disables(self) -> None:
        transport = FakeTransport(_err(429, message="rate"), CHECKOUT_OK)
        with self.assertRaises(PaylinkApiError):
            _invoice(_client(transport, max_retries=0), idempotency_key="k")
        self.assertEqual(len(transport.calls), 1)

    def test_non_transient_error_not_retried(self) -> None:
        transport = FakeTransport(_err(422, message="Invalid signature.", errors={"signature": ["bad"]}))
        client = _client(transport)
        with self.assertRaises(PaylinkApiError) as ctx:
            _invoice(client, idempotency_key="k")
        self.assertEqual(ctx.exception.status, 422)
        self.assertEqual(ctx.exception.errors, {"signature": ["bad"]})
        self.assertEqual(len(transport.calls), 1)

    def test_connection_error_wrapped_and_retried(self) -> None:
        transport = FakeTransport(ConnectionError("dns"), CHECKOUT_OK)
        result = _invoice(_client(transport), idempotency_key="k")
        self.assertEqual(result.invoice_id, 1)
        self.assertEqual(len(transport.calls), 2)

    def test_connection_error_surfaces_when_exhausted(self) -> None:
        transport = FakeTransport(ConnectionError("dns"))
        with self.assertRaises(PaylinkConnectionError):
            _invoice(_client(transport, max_retries=0), idempotency_key="k")

    def test_error_flags(self) -> None:
        self.assertTrue(_err_obj(409).is_idempotency_conflict)
        self.assertTrue(_err_obj(429).is_rate_limited)
        self.assertTrue(_err_obj(403).is_forbidden)


def _err_obj(status: int) -> PaylinkApiError:
    transport = FakeTransport(_err(status, message="x"))
    try:
        _invoice(_client(transport, max_retries=0), idempotency_key="k")
    except PaylinkApiError as error:
        return error
    raise AssertionError("expected PaylinkApiError")


if __name__ == "__main__":
    unittest.main()
