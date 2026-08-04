"""Public result types and the webhook event catalogue.

Resource methods accept snake_case keyword arguments and return the dataclasses
below (snake_case attributes). ``raw`` on a webhook event holds the full decoded
payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

__all__ = [
    "WebhookEventType",
    "CreateInvoiceResult",
    "PaymentResult",
    "RefundResult",
    "VccChargeResult",
    "CardInfo",
    "TokenizeCardResult",
    "ChargeTokenResult",
    "RevokeTokenResult",
    "CreateRecurringResult",
    "MandateStatusResult",
    "MandateActionResult",
    "WebhookEvent",
]


class WebhookEventType:
    """Every webhook event type PayLink can deliver."""

    INVOICE_PAID = "invoice.paid"
    INVOICE_NOT_PAID = "invoice.not_paid"
    INVOICE_VOIDED = "invoice.voided"
    INVOICE_REFUNDED = "invoice.refunded"
    INVOICE_AUTHORIZATION_REVERSED = "invoice.authorization_reversed"
    INVOICE_AUTHORIZED = "invoice.authorized"
    SUBSCRIPTION_ACTIVATED = "subscription.activated"
    SUBSCRIPTION_CHARGED = "subscription.charged"
    SUBSCRIPTION_PAYMENT_FAILED = "subscription.payment_failed"
    SUBSCRIPTION_SUSPENDED = "subscription.suspended"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    SUBSCRIPTION_COMPLETED = "subscription.completed"
    INSTALLMENT_PLAN_ACTIVATED = "installment.plan_activated"
    INSTALLMENT_CHARGED = "installment.charged"
    INSTALLMENT_PAYMENT_FAILED = "installment.payment_failed"
    INSTALLMENT_PLAN_SUSPENDED = "installment.plan_suspended"
    INSTALLMENT_PLAN_COMPLETED = "installment.plan_completed"
    VCC_PAYMENT_SUCCESS = "vcc.payment_success"
    VCC_PAYMENT_FAILED = "vcc.payment_failed"
    CARD_TOKEN_CHARGE_SUCCEEDED = "card_token.charge_succeeded"
    CARD_TOKEN_CHARGE_FAILED = "card_token.charge_failed"


@dataclass(frozen=True)
class CreateInvoiceResult:
    checkout_url: str
    invoice_id: int
    expires_at: str


@dataclass(frozen=True)
class PaymentResult:
    invoice_id: int
    paid_status: str
    auth_code: Optional[str] = None


@dataclass(frozen=True)
class RefundResult:
    invoice_id: int
    paid_status: str
    auth_code: Optional[str] = None
    refund_amount: Optional[float] = None


@dataclass(frozen=True)
class VccChargeResult:
    invoice_id: int
    invoice_number: str
    amount: float
    currency: str
    paid_status: str


@dataclass(frozen=True)
class CardInfo:
    brand: Optional[str] = None
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None


@dataclass(frozen=True)
class TokenizeCardResult:
    token: str
    card: CardInfo
    status: str


@dataclass(frozen=True)
class ChargeTokenResult:
    invoice_id: int
    invoice_number: str
    amount: float
    currency: str
    paid_status: str
    card_token: str


@dataclass(frozen=True)
class RevokeTokenResult:
    message: str


@dataclass(frozen=True)
class CreateRecurringResult:
    checkout_url: str
    mandate_id: str
    invoice_id: int
    expires_at: str


@dataclass(frozen=True)
class MandateStatusResult:
    mandate_id: str
    status: str
    amount: int
    completed_cycles: int
    total_cycles: Optional[int] = None
    next_charge_at: Optional[str] = None


@dataclass(frozen=True)
class MandateActionResult:
    """Result of cancel/pause/resume — the new mandate status plus the raw body."""

    status: Optional[str]
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookEvent:
    """A verified webhook event with snake_case fields; ``raw`` holds the body."""

    event: str
    success: bool
    raw: Dict[str, Any]
    invoice_id: Optional[int] = None
    invoice_status: Optional[str] = None
    message: Optional[str] = None
    auth_code: Optional[str] = None
    mandate_id: Optional[str] = None
    external_reference: Optional[str] = None
    subscription_status: Optional[str] = None
    event_triggered_at: Optional[str] = None
    timezone: Optional[str] = None
