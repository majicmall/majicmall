"""
Lightweight payment adapter pattern.

These are *demo* adapters — they DO NOT call real gateways. They build a
fake "checkout URL" and return it so you can wire up the flow end-to-end.
Replace the start_checkout() logic with real Stripe/PayPal SDK calls later.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Protocol


class PaymentAdapter(Protocol):
    """
    Minimal interface for a payment adapter.
    Return a dict with:
      - redirect_url: URL the shopper should be sent to
      - session_id: opaque gateway session/intent id (string)
    """

    def start_checkout(self, *, amount_cents: int, currency: str, metadata: Dict[str, Any]) -> Dict[str, str]:
        ...


@dataclass
class StripeAdapterImpl:
    api_key: str | None = None
    success_url: str | None = None
    cancel_url: str | None = None

    def start_checkout(self, *, amount_cents: int, currency: str, metadata: Dict[str, Any]) -> Dict[str, str]:
        # TODO: replace this with stripe.checkout.Session.create(...)
        session_id = f"cs_test_{metadata.get('order_id','demo')}"
        redirect_url = f"{self.success_url or '/merchant/checkout/success/'}?session_id={session_id}&gateway=stripe"
        return {"redirect_url": redirect_url, "session_id": session_id}


@dataclass
class PayPalAdapterImpl:
    client_id: str | None = None
    client_secret: str | None = None
    success_url: str | None = None
    cancel_url: str | None = None

    def start_checkout(self, *, amount_cents: int, currency: str, metadata: Dict[str, Any]) -> Dict[str, str]:
        # TODO: replace with PayPal Orders API create+approve URLs
        session_id = f"pp_sess_{metadata.get('order_id','demo')}"
        redirect_url = f"{self.success_url or '/merchant/checkout/success/'}?session_id={session_id}&gateway=paypal"
        return {"redirect_url": redirect_url, "session_id": session_id}


# Registry of provider -> adapter factory (so you can plug in new providers later)
def build_adapter(provider: str, *, credentials: dict, success_url: str, cancel_url: str) -> PaymentAdapter:
    provider = (provider or "").lower()
    if provider == "stripe":
        return StripeAdapterImpl(
            api_key=credentials.get("api_key"),
            success_url=success_url,
            cancel_url=cancel_url,
        )
    if provider == "paypal":
        return PayPalAdapterImpl(
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            success_url=success_url,
            cancel_url=cancel_url,
        )
    # Fallback "credit/debit" placeholder (as if it were an on-site gateway)
    return StripeAdapterImpl(success_url=success_url, cancel_url=cancel_url)  # reuse stub
