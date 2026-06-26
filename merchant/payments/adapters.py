import requests
import stripe
from django.conf import settings


class PaymentAdapterError(Exception):
    pass


class BasePaymentAdapter:
    def __init__(self, credentials=None, success_url=None, cancel_url=None):
        self.credentials = credentials or {}
        self.success_url = success_url
        self.cancel_url = cancel_url

    def start_checkout(self, amount_cents, currency="usd", metadata=None):
        raise NotImplementedError


class StripeCheckoutAdapter(BasePaymentAdapter):
    def start_checkout(self, amount_cents, currency="usd", metadata=None):
        metadata = metadata or {}

        api_key = (
            self.credentials.get("secret_key")
            or getattr(settings, "STRIPE_SECRET_KEY", "")
        )

        if not api_key:
            raise PaymentAdapterError("Stripe secret key is missing.")

        stripe.api_key = api_key

        success_url = self.success_url
        if success_url and "session_id=" not in success_url:
            separator = "&" if "?" in success_url else "?"
            success_url = f"{success_url}{separator}session_id={{CHECKOUT_SESSION_ID}}"

        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {
                                "name": "MajicMall Megaverse Order",
                            },
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=self.cancel_url,
                metadata=metadata,
                client_reference_id=metadata.get("order_id", ""),
            )
        except Exception as exc:
            print("STRIPE CHECKOUT ERROR:", repr(exc))
            raise

        return {
            "provider": "stripe",
            "redirect_url": session.url,
            "session_id": session.id,
        }


class PayPalCheckoutAdapter(BasePaymentAdapter):
    def _mode(self):
        return (
            self.credentials.get("mode")
            or getattr(settings, "PAYPAL_MODE", "sandbox")
            or "sandbox"
        ).lower()

    def _base_url(self):
        if self._mode() == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    def _client_id(self):
        return (
            self.credentials.get("client_id")
            or getattr(settings, "PAYPAL_CLIENT_ID", "")
        )

    def _client_secret(self):
        return (
            self.credentials.get("client_secret")
            or getattr(settings, "PAYPAL_CLIENT_SECRET", "")
        )

    def _access_token(self):
        client_id = self._client_id()
        client_secret = self._client_secret()

        if not client_id or not client_secret:
            raise PaymentAdapterError("PayPal client ID or secret is missing.")

        response = requests.post(
            f"{self._base_url()}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            timeout=30,
        )

        if response.status_code >= 400:
            print("PAYPAL TOKEN ERROR:", response.status_code, response.text)
            raise PaymentAdapterError("Could not authenticate with PayPal.")

        return response.json()["access_token"]

    def start_checkout(self, amount_cents, currency="usd", metadata=None):
        metadata = metadata or {}
        access_token = self._access_token()

        amount = f"{amount_cents / 100:.2f}"
        order_id = str(metadata.get("order_id", ""))

        success_url = self.success_url
        if success_url:
            separator = "&" if "?" in success_url else "?"
            success_url = f"{success_url}{separator}gateway=paypal"

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "custom_id": order_id,
                    "invoice_id": f"MM-{order_id}" if order_id else None,
                    "amount": {
                        "currency_code": currency.upper(),
                        "value": amount,
                    },
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "brand_name": "MajicMall Megaverse",
                        "landing_page": "LOGIN",
                        "user_action": "PAY_NOW",
                        "return_url": success_url,
                        "cancel_url": self.cancel_url,
                    }
                }
            },
        }

        response = requests.post(
            f"{self._base_url()}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        if response.status_code >= 400:
            print("PAYPAL CREATE ORDER ERROR:", response.status_code, response.text)
            raise PaymentAdapterError("Could not create PayPal checkout order.")

        data = response.json()

        approval_url = None
        for link in data.get("links", []):
            if link.get("rel") == "payer-action":
                approval_url = link.get("href")
                break
            if link.get("rel") == "approve":
                approval_url = link.get("href")

        if not approval_url:
            raise PaymentAdapterError("PayPal approval URL was not returned.")

        return {
            "provider": "paypal",
            "redirect_url": approval_url,
            "session_id": data.get("id"),
        }

    def capture_checkout(self, paypal_order_id):
        access_token = self._access_token()

        response = requests.post(
            f"{self._base_url()}/v2/checkout/orders/{paypal_order_id}/capture",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if response.status_code >= 400:
            print("PAYPAL CAPTURE ERROR:", response.status_code, response.text)
            raise PaymentAdapterError("Could not capture PayPal payment.")

        return response.json()



class CoinbaseCommerceAdapter(BasePaymentAdapter):
    def _api_key(self):
        return (
            self.credentials.get("api_key")
            or getattr(settings, "COINBASE_COMMERCE_API_KEY", "")
        )

    def start_checkout(self, amount_cents, currency="usd", metadata=None):
        metadata = metadata or {}
        api_key = self._api_key()

        if not api_key:
            raise PaymentAdapterError("Coinbase Commerce API key is missing.")

        amount = f"{amount_cents / 100:.2f}"

        success_url = self.success_url
        if success_url:
            separator = "&" if "?" in success_url else "?"
            success_url = f"{success_url}{separator}gateway=coinbase"

        payload = {
            "name": "MajicMall Megaverse Order",
            "description": "MajicMall Megaverse storefront purchase",
            "pricing_type": "fixed_price",
            "local_price": {
                "amount": amount,
                "currency": currency.upper(),
            },
            "metadata": metadata,
            "redirect_url": success_url,
            "cancel_url": self.cancel_url,
        }

        response = requests.post(
            "https://api.commerce.coinbase.com/charges",
            headers={
                "X-CC-Api-Key": api_key,
                "X-CC-Version": "2018-03-22",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        if response.status_code >= 400:
            print("COINBASE CREATE CHARGE ERROR:", response.status_code, response.text)
            raise PaymentAdapterError("Could not create Coinbase checkout charge.")

        data = response.json().get("data", {})
        hosted_url = data.get("hosted_url")

        if not hosted_url:
            raise PaymentAdapterError("Coinbase hosted checkout URL was not returned.")

        return {
            "provider": "coinbase",
            "redirect_url": hosted_url,
            "session_id": data.get("id") or data.get("code"),
        }


class CardDemoAdapter(BasePaymentAdapter):
    def start_checkout(self, amount_cents, currency="usd", metadata=None):
        success_url = self.success_url or "/merchant/checkout/success/"
        separator = "&" if "?" in success_url else "?"
        return {
            "provider": "card",
            "redirect_url": f"{success_url}{separator}gateway=card&demo=1",
            "session_id": "demo",
        }


def build_adapter(provider, credentials=None, success_url=None, cancel_url=None):
    provider = (provider or "").lower()

    if provider == "stripe":
        return StripeCheckoutAdapter(credentials, success_url, cancel_url)

    if provider == "paypal":
        return PayPalCheckoutAdapter(credentials, success_url, cancel_url)

    if provider in {"coinbase", "coinbase_commerce"}:
        return CoinbaseCommerceAdapter(credentials, success_url, cancel_url)

    if provider == "card":
        return CardDemoAdapter(credentials, success_url, cancel_url)

    raise PaymentAdapterError(f"Unsupported payment provider: {provider}")
