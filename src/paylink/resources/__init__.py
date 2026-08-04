"""Resource namespaces exposed on :class:`~paylink.client.PaylinkClient`."""

from .cards import Cards
from .invoices import Invoices
from .payments import Payments
from .recurring import Recurring
from .vcc import Vcc

__all__ = ["Invoices", "Payments", "Vcc", "Cards", "Recurring"]
