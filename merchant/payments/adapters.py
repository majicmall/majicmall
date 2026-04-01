"""
Payment adapter pattern.

Stripe is wired to real Stripe Checkout.
PayPal remains a demo stub for now until live PayPal API wiring is added.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Protocol

import stripe
from django.conf import settings


class PaymentAdapter(Protocol):
    """
    Minimal interface for a payment adapter.
    Return a dict with:
      - redirect_url: URL the shopper should be sent to
      - session_id: opaque gateway session/intent id (string)
    """

    def start_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, str]:
        ...


@dataclass
class StripeAdapterImpl:
    api_key: str | None = None
    success_url: str | None = None
    cancel_url: str | None = None

    def start_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, str]:
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY

            order_id = str(metadata.get("order_id", "")).strip()

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {
                                "name": "Majic Mall Order",
                            },
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=f"{self.success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=self.cancel_url,
                metadata=metadata,
                client_reference_id=order_id or None,
            )

            return {
                "redirect_url": session.url,
                "session_id": session.id,
            }
        except Exception as e:
            print("STRIPE CHECKOUT ERROR:", repr(e))
            raise


@dataclass
class PayPalAdapterImpl:
    client_id: str | None = None
    client_secret: str | None = None
    success_url: str | None = None
    cancel_url: str | None = None

    def start_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, str]:
        # Demo stub for now
        session_id = f"pp_sess_{metadata.get('order_id', 'demo')}"
        redirect_url = f"{self.success_url or '/merchant/checkout/success/'}?session_id={session_id}&gateway=paypal"
        return {"redirect_url": redirect_url, "session_id": session_id}


def build_adapter(
    provider: str,
    *,
    credentials: dict,
    success_url: str,
    cancel_url: str,
) -> PaymentAdapter:
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

    return StripeAdapterImpl(
        success_url=success_url,
        cancel_url=cancel_url,
    )