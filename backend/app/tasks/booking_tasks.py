"""
Celery tasks for async booking execution.

The primary task is execute_trip_bookings(trip_id), which:
  1. Retrieves the approved itinerary and all pending bookings for the trip.
  2. Builds the traveler context from the user's profile.
  3. For each booking, in sequence:
       a. Creates a Stripe Issuing virtual card capped at the booking amount.
       b. Runs the BookingAgent (mock or Playwright + Claude vision).
       c. Records confirmation_number on success, or marks the booking failed.
  4. Sets the trip status to "confirmed" or "booking_failed" when finished.

Start the worker alongside uvicorn:
    celery -A app.worker worker --loglevel=info
"""

import asyncio

from app.tasks import celery_app


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def execute_trip_bookings(self, trip_id: str) -> None:
    """Celery entry point — delegates to the async implementation."""
    try:
        asyncio.run(_async_execute_trip_bookings(trip_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _async_execute_trip_bookings(trip_id: str) -> None:
    from app.database import SessionLocal
    from app.encryption import decrypt
    from app.models import Booking, Trip, User
    from app.services.booking_agent import BookingAgent, BookingNotSupported
    from app.services.virtual_card import create_virtual_card, void_virtual_card

    db = SessionLocal()
    try:
        trip = db.query(Trip).filter(Trip.id == trip_id).first()
        if not trip:
            return

        user = db.query(User).filter(User.id == trip.user_id).first()
        if not user:
            trip.status = "booking_failed"
            db.commit()
            return

        bookings = (
            db.query(Booking)
            .filter(Booking.trip_id == trip_id, Booking.status == "pending")
            .all()
        )
        if not bookings:
            return

        # Build the traveler context once — used by every booking agent call
        loyalty_list = user.loyalty_numbers or []
        traveler = {
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "date_of_birth": user.date_of_birth or "",
            "phone": user.phone or "",
            "email": user.email,
            "seat_preference": user.seat_preference or "No preference",
            "meal_preference": user.meal_preference or "No preference",
            "loyalty_numbers": loyalty_list,
            "passport_number": decrypt(user.passport_number_enc) if user.passport_number_enc else "",
            "tsa_number": decrypt(user.tsa_known_traveler_enc) if user.tsa_known_traveler_enc else "",
        }

        approved = trip.approved_itinerary or {}
        all_confirmed = True

        activity_bookings_count = sum(1 for b in bookings if b.type == "activity")

        for booking in bookings:
            booking.status = "in_progress"
            db.commit()

            virtual_card = None
            try:
                # Determine the amount for this booking's virtual card
                if booking.type == "flight":
                    amount = approved.get("flight", {}).get("price_usd", approved.get("total_usd", 0))
                elif booking.type == "hotel":
                    amount = approved.get("hotel", {}).get("price_total_usd", approved.get("total_usd", 0))
                elif booking.type == "activity":
                    activities_total = approved.get("activities_total_usd", 0)
                    amount = (
                        activities_total / activity_bookings_count
                        if activity_bookings_count > 0
                        else 0
                    )
                else:
                    amount = approved.get("total_usd", 0)

                virtual_card = await create_virtual_card(
                    amount_usd=float(amount),
                    description=f"Trip {trip_id} — {booking.type}",
                    user_email=user.email,
                )
                booking.virtual_card_id = virtual_card["card_id"]
                db.commit()

                # For activity bookings, inject the specific activity into
                # the itinerary so the agent knows which one to simulate.
                if booking.type == "activity":
                    itinerary_for_agent = {
                        **approved,
                        "activity": (booking.details or {}).get("activity", {}),
                    }
                else:
                    itinerary_for_agent = approved

                agent = BookingAgent(booking_id=str(booking.id), db=db)
                confirmation = await agent.run(
                    booking_type=booking.type,
                    itinerary=itinerary_for_agent,
                    traveler=traveler,
                    virtual_card=virtual_card,
                )

                booking.status = "confirmed"
                booking.confirmation_number = confirmation
                db.commit()

            except BookingNotSupported as exc:
                booking.status = "unsupported"
                booking.details = {**(booking.details or {}), "error": str(exc)}
                db.commit()
                all_confirmed = False
                # Void the card if one was created
                if virtual_card:
                    await void_virtual_card(virtual_card["card_id"])

            except Exception as exc:
                booking.status = "failed"
                booking.details = {**(booking.details or {}), "error": str(exc)}
                db.commit()
                all_confirmed = False
                if virtual_card:
                    await void_virtual_card(virtual_card["card_id"])

        trip.status = "confirmed" if all_confirmed else "booking_failed"
        db.commit()

        if all_confirmed:
            try:
                from app.models import Booking as BookingModel
                from app.services.confirmation import build_confirmation
                from app.services.email import send_booking_confirmation

                all_bookings = db.query(BookingModel).filter(BookingModel.trip_id == trip_id).all()
                confirmation = build_confirmation(trip, all_bookings)
                user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
                await send_booking_confirmation(
                    user_email=user.email,
                    user_name=user_name,
                    confirmation=confirmation,
                )
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("[booking_tasks] email step failed: %s", exc)

    finally:
        db.close()
