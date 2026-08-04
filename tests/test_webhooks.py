import json
import unittest

from paylink import PaylinkClient
from paylink.errors import PaylinkError, PaylinkSignatureError
from paylink.signature import build_signature

HASH = "test_hash_token_abc123"


def _signed(payload: dict, hash_token: str = HASH) -> dict:
    values = [
        str(payload.get("success", "")),
        str(payload.get("invoice_id", "")),
        str(payload.get("invoice_status", "")),
        "" if payload.get("message") is None else str(payload.get("message")),
    ]
    for key in ("mandate_id", "external_reference", "subscription_status"):
        if key in payload:
            values.append("" if payload[key] is None else str(payload[key]))
    return dict(payload, signature=build_signature(values, hash_token))


class WebhooksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = PaylinkClient(public_token="p", hash_token=HASH)

    def test_verify_valid_invoice_paid(self) -> None:
        payload = _signed(
            {"event": "invoice.paid", "success": 1, "invoice_id": 123, "invoice_status": "PAID", "message": None}
        )
        event = self.client.webhooks.verify(payload)
        self.assertEqual(event.event, "invoice.paid")
        self.assertTrue(event.success)
        self.assertEqual(event.invoice_id, 123)
        self.assertIsNone(event.message)

    def test_verify_accepts_json_string_and_bytes(self) -> None:
        payload = _signed(
            {"event": "invoice.paid", "success": 1, "invoice_id": 1, "invoice_status": "PAID", "message": "ok"}
        )
        self.assertTrue(self.client.webhooks.is_valid(json.dumps(payload)))
        self.assertTrue(self.client.webhooks.is_valid(json.dumps(payload).encode()))

    def test_subscription_optional_fields_are_signed(self) -> None:
        payload = _signed(
            {
                "event": "subscription.charged",
                "success": 1,
                "invoice_id": 555,
                "invoice_status": "PAID",
                "message": "ok",
                "auth_code": "A1",
                "mandate_id": "M-1",
                "external_reference": "sub_1",
                "subscription_status": "active",
            }
        )
        event = self.client.webhooks.verify(payload)
        self.assertEqual(event.mandate_id, "M-1")
        self.assertEqual(event.subscription_status, "active")
        self.assertEqual(event.auth_code, "A1")

    def test_tampered_payload_rejected(self) -> None:
        payload = _signed(
            {"event": "invoice.paid", "success": 1, "invoice_id": 1, "invoice_status": "PAID", "message": "ok"}
        )
        tampered = dict(payload, invoice_status="UNPAID")
        self.assertFalse(self.client.webhooks.is_valid(tampered))
        with self.assertRaises(PaylinkSignatureError):
            self.client.webhooks.verify(tampered)

    def test_missing_signature_raises(self) -> None:
        with self.assertRaises(PaylinkSignatureError):
            self.client.webhooks.verify(
                {"event": "invoice.paid", "success": 1, "invoice_id": 1, "invoice_status": "PAID"}
            )

    def test_hash_token_override(self) -> None:
        payload = _signed(
            {"event": "invoice.paid", "success": 1, "invoice_id": 9, "invoice_status": "PAID", "message": "ok"},
            hash_token="other_secret",
        )
        # Default client hashToken does not match.
        self.assertFalse(self.client.webhooks.is_valid(payload))
        # Overriding with the correct secret verifies.
        self.assertTrue(self.client.webhooks.is_valid(payload, hash_token="other_secret"))

    def test_invalid_json_raises_paylink_error(self) -> None:
        with self.assertRaises(PaylinkError):
            self.client.webhooks.verify("{not json")


if __name__ == "__main__":
    unittest.main()
