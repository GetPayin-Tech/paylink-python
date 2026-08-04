# paylink

[![PyPI](https://img.shields.io/pypi/v/paylink.svg)](https://pypi.org/project/paylink/)
[![Python](https://img.shields.io/pypi/pyversions/paylink.svg)](https://pypi.org/project/paylink/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Official **server-side** Python SDK for the PayLink payment integration API. It
wraps every integration endpoint with an idiomatic, typed API and computes the
order-sensitive HMAC-SHA256 signatures for you, so you never have to build them
by hand.

- Checkouts (`invoices.create`)
- Payment operations (`payments.void` / `refund` / `settle` / `reverse_authorization` / `check_status`)
- Server-to-server card charges (`vcc.charge`)
- Card tokenization (`cards.tokenize` / `charge` / `revoke`)
- Recurring mandates (`recurring.create` / `status` / `cancel` / `pause` / `resume`)
- Webhook signature verification (`webhooks.verify`)

> **Server-side only.** Signing uses your secret `hash_token`. Never ship it to a
> browser or mobile client.

## Requirements

- Python **3.8+**
- **Zero runtime dependencies** — the default transport is built on the standard library

## Install

```bash
pip install paylink
```

## Quick start

```python
import os
from paylink import PaylinkClient

paylink = PaylinkClient(
    public_token=os.environ["PAYLINK_PUBLIC_TOKEN"],
    hash_token=os.environ["PAYLINK_HASH_TOKEN"],  # secret — server-side only
    # base_url defaults to https://pay.getpayin.com
    # timeout defaults to 30.0 seconds (per attempt)
    # max_retries defaults to 2 (set 0 to disable retries)
)

checkout = paylink.invoices.create(
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    order_title="Gold Plan",
    order_amount="250.00",  # pass amounts as strings to control the exact wire form
    currency="USD",
    redirection_url="https://shop.example.com/return",
    webhook_url="https://shop.example.com/webhooks/paylink",
)

# Redirect the payer to the hosted checkout:
print(checkout.checkout_url, checkout.invoice_id, checkout.expires_at)
```

Both credentials are issued in the PayLink dashboard under **Settings → Payment
Integrations**. `public_token` is sent on every request; `hash_token` is the
secret used only to sign — it never leaves your server.

## Payment operations

```python
paylink.payments.void(invoice_id=123)
paylink.payments.settle(invoice_id=123, amount="50.00")
paylink.payments.reverse_authorization(invoice_id=123)

status = paylink.payments.check_status(invoice_id=123)
# PaymentResult(invoice_id=123, paid_status='PAID', auth_code='...')

# Refunds are idempotent when you pass an idempotency key — safe to retry:
refund = paylink.payments.refund(
    invoice_id=123, amount="10.50", idempotency_key="refund-order-1234"
)
# RefundResult(..., refund_amount=10.5)
```

## Card tokenization

```python
result = paylink.cards.tokenize(
    first_name="Jane", last_name="Doe",
    card_number="4111111111111111",
    card_expiry_month="12", card_expiry_year="2030", card_cvv="123",
    country="EG", address="1 Main St", city="Cairo",
)

paylink.cards.charge(
    card_token=result.token,
    initiator="merchant",
    first_name="Jane", last_name="Doe",
    currency="USD", price="100.00", product="Monthly rebill",
    country="EG", address="1 Main St", city="Cairo",
)

paylink.cards.revoke(card_token=result.token)
```

For `US` and `CA` billing addresses, also pass the state fields the API requires:
`us_state` + `postal_code` (US) or `canada_state` + `postal_code` (CA).

## Recurring mandates

```python
mandate = paylink.recurring.create(
    first_name="Sam", last_name="Doe", email="sam@example.com",
    order_title="Gold subscription",
    order_amount="250.00", currency="USD",
    cadence_interval="month", cadence_count=1, total_cycles=12,
    consent_text="I authorise recurring monthly charges.",
    idempotency_key="sub-signup-42",
)

paylink.recurring.status(mandate.mandate_id)
paylink.recurring.pause(mandate.mandate_id)
paylink.recurring.resume(mandate.mandate_id)
paylink.recurring.cancel(mandate.mandate_id)
```

## Idempotency

Retrying a write after a network error or timeout risks performing it twice. To
make that safe, pass an `idempotency_key` — the SDK sends it as the
`Idempotency-Key` header and the server returns the original result instead of
charging, refunding, or creating a second time. Keys are scoped per integration
and capped at 64 characters.

| Method              | A replay with the same key returns       |
| ------------------- | ---------------------------------------- |
| `invoices.create`   | the original invoice and `checkout_url`  |
| `vcc.charge`        | the original charge                      |
| `cards.charge`      | the original charge                      |
| `payments.refund`   | the original refund                      |
| `recurring.create`  | the original mandate                     |

Reusing a key with a _different_ request — for example `recurring.create` with
changed terms, or `payments.refund` for a different amount — is rejected as a
conflict: a `PaylinkApiError` with `is_idempotency_conflict` set (HTTP 409). Only
the methods above honor the header.

## Verifying webhooks

Pass the parsed body (a dict) or the raw JSON string/bytes to `verify`. It
recomputes the signature with your `hash_token` and compares in constant time.

```python
from flask import Flask, request, abort
from paylink import PaylinkClient, PaylinkSignatureError

paylink = PaylinkClient(public_token=..., hash_token=...)
app = Flask(__name__)

@app.post("/webhooks/paylink")
def webhook():
    try:
        event = paylink.webhooks.verify(request.get_data(as_text=True))
    except PaylinkSignatureError:
        abort(400)
    # event.event, event.invoice_id, event.success, event.raw, ...
    return "", 200
```

> PayLink webhook signatures carry no timestamp, so verification does not protect
> against replay. Pair it with your own idempotency keyed on `invoice_id`.

## Error handling

Every failure is a subclass of `PaylinkError`:

| Error                    | When                                                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `PaylinkConfigError`     | Invalid client configuration (missing tokens, non-positive timeout).                                                                        |
| `PaylinkApiError`        | The API returned an error. Carries `status`, `errors`, `raw`, `retry_after_seconds`, and the `is_idempotency_conflict` / `is_rate_limited` / `is_forbidden` flags. |
| `PaylinkSignatureError`  | A webhook signature did not verify.                                                                                                          |
| `PaylinkConnectionError` | Network failure or timeout (no HTTP response).                                                                                               |

```python
from paylink import PaylinkApiError

try:
    paylink.payments.refund(invoice_id=123, amount="10.00")
except PaylinkApiError as error:
    if error.is_idempotency_conflict:
        ...  # a refund with this idempotency key already exists
```

## Retries and rate limiting

Every integration endpoint is rate limited server-side, so 429s are an expected
condition under burst traffic. The SDK retries transient failures — **429, 5xx,
connection errors, and timeouts** — with exponential backoff and full jitter,
honoring the server's `Retry-After` header when present.

**A request is only ever replayed when replaying it cannot double-charge:**

| Replayed                                    | Not replayed                                          |
| ------------------------------------------- | ----------------------------------------------------- |
| All GETs (`recurring.status`)               | `vcc.charge`, `cards.charge`, `cards.tokenize`        |
| Any call you pass an `idempotency_key` to   | `invoices.create`, `recurring.create` without a key   |
| `payments.check_status` (a pure read)       | `recurring.cancel` / `pause` / `resume`               |

So to make a refund safely retryable, pass an idempotency key — otherwise a
failed refund surfaces immediately and is yours to handle. Tune or disable
retries per client with `max_retries` (set `0` to turn them off). `timeout`
applies to **each attempt**, so worst-case wall time is roughly
`(max_retries + 1) × timeout` plus backoff. For requests the SDK will not replay,
`PaylinkApiError.retry_after_seconds` exposes the server's backoff hint.

## Amounts and precision

Signatures are computed over the exact bytes sent on the wire. To avoid any
floating-point ambiguity, **pass monetary amounts as strings** (e.g. `"10.50"`).
Numbers are accepted and stringified, but strings give you full control.

## Custom transport

The default transport uses the standard library. Inject any callable matching
`paylink.Transport` — for a proxy-aware or connection-pooled HTTP client, or a
mock in tests:

```python
def transport(method, url, headers, body, timeout):
    resp = requests.request(method, url, headers=headers, data=body, timeout=timeout)
    return paylink.HttpResponse(status=resp.status_code, text=resp.text, headers=dict(resp.headers))

paylink = PaylinkClient(public_token=..., hash_token=..., transport=transport)
```

## API reference

The full HTTP API — endpoints, fields, error codes, and test cards — is
documented in the PayLink API reference:
<https://pay.getpayin.com/docs/payment_integration/index.html>

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — in particular the note on signed-field
ordering, which is the one thing that must stay in lockstep with the server.

Security issues: see [SECURITY.md](SECURITY.md). Please do not open a public issue
for a vulnerability.

## License

MIT
