"""
SendGrid email delivery for booking confirmations.

If SENDGRID_API_KEY is empty, the function logs a warning and returns without
raising — email is best-effort and should not block the booking pipeline.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


async def send_booking_confirmation(
    user_email: str,
    user_name: str,
    confirmation: dict,
) -> None:
    """
    Send a consolidated booking confirmation email via SendGrid.

    Args:
        user_email: Recipient email address.
        user_name: Recipient display name.
        confirmation: Structured confirmation dict from build_confirmation().
    """
    if not settings.sendgrid_api_key:
        logger.warning(
            "[email] SENDGRID_API_KEY not configured — skipping confirmation email "
            "for trip %s",
            confirmation.get("trip_id"),
        )
        return

    try:
        import sendgrid  # type: ignore
        from sendgrid.helpers.mail import Mail  # type: ignore

        html_body = _build_html(user_name, confirmation)

        message = Mail(
            from_email=settings.sendgrid_from_email,
            to_emails=user_email,
            subject=f"Your trip to {confirmation.get('destination', 'your destination')} is confirmed!",
            html_content=html_body,
        )

        sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
        response = sg.send(message)
        logger.info(
            "[email] Confirmation sent to %s — status %s",
            user_email,
            response.status_code,
        )
    except Exception as exc:
        logger.warning("[email] Failed to send confirmation email: %s", exc)


def _build_html(user_name: str, confirmation: dict) -> str:
    destination = confirmation.get("destination", "your destination")
    dates = confirmation.get("travel_dates", {})
    depart = dates.get("depart", "")
    ret = dates.get("return", "")
    total = confirmation.get("total_charged_usd", 0.0)
    bookings = confirmation.get("bookings", [])

    booking_rows = []
    for b in bookings:
        btype = b.get("type", "")
        conf_num = b.get("confirmation_number") or "—"

        if btype == "flight":
            detail = (
                f"{b.get('carrier', '')} {b.get('flight_number', '')} &mdash; "
                f"{b.get('origin', '')} &rarr; {b.get('destination', '')} "
                f"departing {b.get('depart_datetime', '')[:16].replace('T', ' ')} "
                f"({b.get('cabin', '')})"
            )
        elif btype == "hotel":
            detail = (
                f"{b.get('hotel_name', '')} &mdash; "
                f"Check-in: {b.get('check_in', '')} &bull; Check-out: {b.get('check_out', '')} "
                f"({b.get('room_type', '')})"
            )
        else:
            detail = (
                f"{b.get('activity_name', '')} &mdash; {b.get('date', '')} "
                f"({b.get('duration_hours', '')}h, {b.get('category', '')})"
            )

        booking_rows.append(
            f"<tr>"
            f"<td style='padding:8px;text-transform:capitalize'>{btype}</td>"
            f"<td style='padding:8px;font-family:monospace'>{conf_num}</td>"
            f"<td style='padding:8px'>{detail}</td>"
            f"</tr>"
        )

    rows_html = "\n".join(booking_rows)
    date_range = f"{depart}" + (f" &ndash; {ret}" if ret else "")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#222">
  <h2 style="color:#1a56a0">Your trip to {destination} is confirmed</h2>
  <p>Hi {user_name},</p>
  <p>All bookings for your trip to <strong>{destination}</strong>
     ({date_range}) have been confirmed. Details below:</p>

  <table style="width:100%;border-collapse:collapse;margin:16px 0">
    <thead>
      <tr style="background:#f0f4fb">
        <th style="padding:8px;text-align:left">Type</th>
        <th style="padding:8px;text-align:left">Confirmation #</th>
        <th style="padding:8px;text-align:left">Details</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>

  <p><strong>Total charged: ${total:,.2f} USD</strong></p>
  <hr style="border:none;border-top:1px solid #ddd;margin:24px 0">
  <p style="font-size:12px;color:#888">
    This email was sent by Travel Planner. Please keep this for your records.
  </p>
</body>
</html>"""
