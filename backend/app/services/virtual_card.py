"""
Stripe Issuing — creates a single-use virtual card for each booking.

Design:
  - One Stripe Cardholder per user (keyed by email), created lazily.
  - One virtual card per booking, with a spending limit equal to the booking amount.
  - The card is cancelled if the booking fails, preventing any accidental charge.

When STRIPE_SECRET_KEY is not set, all functions return realistic mock card data
so the full booking pipeline can be tested without a Stripe account.

Production notes:
  - Stripe Issuing requires a separate application approval from Stripe.
  - Card sensitive details (number, cvc) require the "issuing_card_number:read"
    permission on your restricted API key.
  - In production, consider using Stripe Issuing Elements (client-side) for PCI
    compliance instead of retrieving raw card numbers server-side.
"""

import random
import string

import stripe

from app.config import settings


def _mock_card(amount_usd: float, description: str) -> dict:
    """Return a realistic fake card for development / mock mode."""
    return {
        "card_id": "mock_card_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8)),
        "number": "4111111111111111",  # Standard Visa test number
        "exp_month": "12",
        "exp_year": "2027",
        "cvc": "123",
        "amount_usd": amount_usd,
        "currency": "usd",
        "description": description,
        "mock": True,
    }


async def create_virtual_card(amount_usd: float, description: str, user_email: str) -> dict:
    """
    Create a single-use Stripe Issuing virtual card capped at `amount_usd`.
    Returns a dict with: card_id, number, exp_month, exp_year, cvc, amount_usd.

    Falls back to mock data when STRIPE_SECRET_KEY is not configured.
    """
    if not settings.stripe_secret_key:
        return _mock_card(amount_usd, description)

    stripe.api_key = settings.stripe_secret_key

    # Find or create a cardholder for this user
    existing = stripe.issuing.Cardholder.list(email=user_email, limit=1)
    if existing.data:
        cardholder_id = existing.data[0].id
    else:
        cardholder = stripe.issuing.Cardholder.create(
            name=user_email,
            email=user_email,
            type="individual",
            billing={
                "address": {
                    "line1": "123 Travel St",
                    "city": "San Francisco",
                    "state": "CA",
                    "postal_code": "94105",
                    "country": "US",
                }
            },
        )
        cardholder_id = cardholder.id

    # Create virtual card with a per-authorization spending limit
    amount_cents = int(amount_usd * 100)
    card = stripe.issuing.Card.create(
        cardholder=cardholder_id,
        currency="usd",
        type="virtual",
        spending_controls={
            "spending_limits": [
                {"amount": amount_cents, "interval": "per_authorization"}
            ]
        },
        metadata={"description": description},
    )

    # Retrieve sensitive details (requires issuing_card_number:read permission)
    sensitive = stripe.issuing.Card.retrieve(
        card.id,
        expand=["number", "cvc"],
    )

    return {
        "card_id": card.id,
        "number": sensitive.number,
        "exp_month": str(card.exp_month).zfill(2),
        "exp_year": str(card.exp_year),
        "cvc": sensitive.cvc,
        "amount_usd": amount_usd,
        "currency": "usd",
        "description": description,
        "mock": False,
    }


async def void_virtual_card(card_id: str) -> None:
    """Cancel a virtual card — call this if a booking fails after card creation."""
    if not settings.stripe_secret_key or card_id.startswith("mock_card_"):
        return  # Nothing to cancel in mock mode

    stripe.api_key = settings.stripe_secret_key
    stripe.issuing.Card.modify(card_id, status="canceled")
