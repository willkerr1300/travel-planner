"""
Confirmation parser — builds a structured confirmation dict from DB records.

No email ingestion; this reads trip and booking data already stored in the DB
and returns a clean structure suitable for display or email delivery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Booking, Trip


def build_confirmation(trip: "Trip", bookings: list["Booking"]) -> dict:
    """
    Build a structured confirmation dict from a confirmed trip and its bookings.

    Returns:
        {
          "trip_id": str,
          "destination": str,
          "travel_dates": {"depart": str, "return": str | None},
          "bookings": [...],
          "total_charged_usd": float,
        }
    """
    parsed = trip.parsed_spec or {}
    approved = trip.approved_itinerary or {}

    booking_items = []
    total_charged = 0.0

    for booking in bookings:
        details = booking.details or {}

        if booking.type == "flight":
            flight = details.get("flight", {})
            segments = flight.get("segments", [])
            first_seg = segments[0] if segments else {}
            booking_items.append({
                "type": "flight",
                "confirmation_number": booking.confirmation_number,
                "carrier": flight.get("carrier", ""),
                "flight_number": first_seg.get("flight", ""),
                "origin": first_seg.get("from", ""),
                "destination": first_seg.get("to", ""),
                "depart_datetime": first_seg.get("departs", ""),
                "cabin": flight.get("cabin", ""),
            })
            if booking.status == "confirmed":
                total_charged += flight.get("price_usd", 0.0)

        elif booking.type == "hotel":
            hotel = details.get("hotel", {})
            booking_items.append({
                "type": "hotel",
                "confirmation_number": booking.confirmation_number,
                "hotel_name": hotel.get("name", ""),
                "check_in": hotel.get("check_in", ""),
                "check_out": hotel.get("check_out", ""),
                "room_type": hotel.get("room_type", ""),
            })
            if booking.status == "confirmed":
                total_charged += hotel.get("price_total_usd", 0.0)

        elif booking.type == "activity":
            activity = details.get("activity", {})
            booking_items.append({
                "type": "activity",
                "confirmation_number": booking.confirmation_number,
                "activity_name": activity.get("name", ""),
                "date": activity.get("date", ""),
                "category": activity.get("category", ""),
                "duration_hours": activity.get("duration_hours"),
            })
            if booking.status == "confirmed":
                total_charged += activity.get("price_usd", 0.0)

    return {
        "trip_id": str(trip.id),
        "destination": parsed.get("destination_city") or parsed.get("destination", ""),
        "travel_dates": {
            "depart": parsed.get("depart_date", ""),
            "return": parsed.get("return_date"),
        },
        "bookings": booking_items,
        "total_charged_usd": round(total_charged, 2),
    }
