"""
Vision-based booking agent.

Uses Playwright for browser automation and the Claude claude-sonnet-4-6 vision API to
navigate booking sites without fragile CSS selectors. Claude receives a
screenshot at each step and decides the next action (click, type, scroll,
etc.) based purely on what it sees.

Two modes
---------
Mock mode  (BOOKING_MOCK_MODE=true, default)
    Simulates the booking flow with realistic step-by-step logs and random
    confirmation numbers. No browser, no real site access required. The full
    pipeline — approve → book → polling → confirmation — works in mock mode.

Live mode  (BOOKING_MOCK_MODE=false)
    Launches a real headless Chromium browser (local Playwright or
    Browserless.io) and drives it with the Claude vision agent loop.

Supported sites (live mode)
---------------------------
Flights : United Airlines (UA), Delta (DL), American Airlines (AA), Southwest (WN)
Hotels  : Expedia (default); Marriott.com for Marriott-brand hotels when the
          traveler has a Marriott loyalty number
Activities: Not supported in live mode (use mock mode)

Any other carrier in live mode raises BookingNotSupported, which sets the
booking status to "unsupported" rather than "failed".
"""

import asyncio
import base64
import contextlib
import json
import random
import re
import string
from typing import Optional

from anthropic import AsyncAnthropic
from sqlalchemy.orm import Session

from app.config import settings


class BookingNotSupported(Exception):
    """Raised when the carrier/hotel/activity is not supported for automated booking."""


SUPPORTED_CARRIERS = {
    "UA": "https://www.united.com/en/us/book/flights",
    "DL": "https://www.delta.com/us/en/flight-search/book-a-flight",
    "AA": "https://www.aa.com/booking/find-flights",
    "WN": "https://www.southwest.com/air/booking/",
}

MARRIOTT_BRANDS = {
    "marriott", "westin", "sheraton", "w hotel", "st. regis",
    "ritz-carlton", "courtyard", "residence inn",
}


class BookingAgent:
    MAX_AGENT_STEPS = 30

    def __init__(self, booking_id: str, db: Session):
        self.booking_id = booking_id
        self.db = db

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(
        self,
        booking_type: str,
        itinerary: dict,
        traveler: dict,
        virtual_card: dict,
    ) -> str:
        """
        Execute the booking. Returns a confirmation number string.
        Raises BookingNotSupported or RuntimeError on failure.
        """
        if settings.booking_mock_mode:
            return await self._mock_booking(booking_type, itinerary, traveler)

        if booking_type == "flight":
            return await self._book_flight(itinerary["flight"], traveler, virtual_card)
        elif booking_type == "hotel":
            return await self._book_hotel(itinerary["hotel"], traveler, virtual_card)
        elif booking_type == "activity":
            raise BookingNotSupported(
                "Activity booking via Viator is not yet supported in live mode. "
                "Set BOOKING_MOCK_MODE=true to simulate activity bookings."
            )
        else:
            raise ValueError(f"Unknown booking type: {booking_type}")

    # ------------------------------------------------------------------
    # Mock mode
    # ------------------------------------------------------------------

    async def _mock_booking(self, booking_type: str, itinerary: dict, traveler: dict) -> str:
        """Simulate a realistic booking flow without a real browser."""
        _carrier_sites = {
            "UA": "united.com",
            "DL": "delta.com",
            "AA": "aa.com",
            "WN": "southwest.com",
        }
        if booking_type == "flight":
            flight = itinerary.get("flight", {})
            carrier = flight.get("carrier", "UA")
            site = _carrier_sites.get(carrier, f"{carrier.lower()}.com")
            detail = flight.get("segments", [{}])[0]
            target = f"{detail.get('from', '???')} → {detail.get('to', '???')}"
        elif booking_type == "activity":
            activity = itinerary.get("activity", {})
            site = "viator.com"
            target = activity.get("name", "activity")
        else:
            hotel = itinerary.get("hotel", {})
            hotel_name = hotel.get("name", "").lower()
            is_marriott = any(brand in hotel_name for brand in MARRIOTT_BRANDS)
            site = "marriott.com" if is_marriott else "expedia.com"
            target = hotel.get("name", "hotel")

        steps = [
            ("navigate",       f"Navigating to {site}"),
            ("search",         f"Searching for {target}"),
            ("select",         "Selecting the option from search results"),
            ("passenger_info", f"Filling in passenger: {traveler.get('first_name', '')} {traveler.get('last_name', '')}"),
            ("seat_selection", f"Selecting seat preference: {traveler.get('seat_preference', 'No preference')}"),
            ("loyalty_number", "Entering loyalty program number"),
            ("payment",        "Entering virtual card details"),
            ("review",         "Reviewing booking summary"),
            ("confirm",        "Submitting booking"),
        ]

        for step_name, step_desc in steps:
            await asyncio.sleep(1.2)
            self._log_step(step_name, step_desc, "success")

        confirmation = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self._log_step("done", f"Booking confirmed — confirmation number: {confirmation}", "success")
        return confirmation

    # ------------------------------------------------------------------
    # Live mode — Airlines (UA, DL, AA, WN)
    # ------------------------------------------------------------------

    async def _book_flight(self, flight: dict, traveler: dict, virtual_card: dict) -> str:
        carrier = flight.get("carrier", "")
        if carrier not in SUPPORTED_CARRIERS:
            raise BookingNotSupported(
                f"Carrier {carrier!r} is not supported for automated flight booking. "
                f"Supported carriers: {', '.join(SUPPORTED_CARRIERS)}. "
                f"Set BOOKING_MOCK_MODE=true to simulate any carrier."
            )

        segments = flight.get("segments", [])
        if not segments:
            raise ValueError("Flight has no segments")

        carrier_url = SUPPORTED_CARRIERS[carrier]
        carrier_names = {"UA": "United Airlines", "DL": "Delta Air Lines", "AA": "American Airlines", "WN": "Southwest Airlines"}
        carrier_name = carrier_names.get(carrier, carrier)
        site = carrier_url.split("/")[2]  # e.g. "www.united.com"

        outbound = segments[0]
        context = {
            "goal": "book_flight",
            "carrier": carrier,
            "carrier_name": carrier_name,
            "site": site,
            "flight_number": outbound.get("flight", ""),
            "depart_date": outbound.get("departs", "")[:10],
            "origin": outbound.get("from", ""),
            "destination": outbound.get("to", ""),
            "cabin": flight.get("cabin", "ECONOMY"),
            "passenger": {
                "first_name": traveler.get("first_name", ""),
                "last_name": traveler.get("last_name", ""),
                "date_of_birth": traveler.get("date_of_birth", ""),
                "email": traveler.get("email", ""),
                "phone": traveler.get("phone", ""),
                "seat_preference": traveler.get("seat_preference", "No preference"),
                "loyalty_numbers": traveler.get("loyalty_numbers", []),
                "tsa_number": traveler.get("tsa_number", ""),
            },
            "virtual_card": {
                "number": virtual_card["number"],
                "exp_month": virtual_card["exp_month"],
                "exp_year": virtual_card["exp_year"],
                "cvc": virtual_card["cvc"],
            },
        }

        async with self._browser_page() as page:
            self._log_step("navigate", f"Navigating to {site}", "in_progress")
            await page.goto(carrier_url, timeout=30_000)
            return await self._agent_loop(page, context)

    # ------------------------------------------------------------------
    # Live mode — Hotels (Expedia default, Marriott for loyalty members)
    # ------------------------------------------------------------------

    async def _book_hotel(self, hotel: dict, traveler: dict, virtual_card: dict) -> str:
        hotel_name = hotel.get("name", "").lower()
        is_marriott_brand = any(brand in hotel_name for brand in MARRIOTT_BRANDS)
        has_marriott_loyalty = any(
            ln.get("program", "").lower() in ("marriott bonvoy", "marriott")
            for ln in traveler.get("loyalty_numbers", [])
        )

        if is_marriott_brand and has_marriott_loyalty:
            site = "www.marriott.com"
            booking_url = "https://www.marriott.com/reservation/availabilitySearch.mi"
        else:
            site = "www.expedia.com"
            booking_url = "https://www.expedia.com/Hotel-Search"

        context = {
            "goal": "book_hotel",
            "site": site,
            "hotel_name": hotel.get("name", ""),
            "check_in": hotel.get("check_in", ""),
            "check_out": hotel.get("check_out", ""),
            "room_type": hotel.get("room_type", ""),
            "passenger": {
                "first_name": traveler.get("first_name", ""),
                "last_name": traveler.get("last_name", ""),
                "email": traveler.get("email", ""),
                "phone": traveler.get("phone", ""),
                "loyalty_numbers": traveler.get("loyalty_numbers", []),
            },
            "virtual_card": {
                "number": virtual_card["number"],
                "exp_month": virtual_card["exp_month"],
                "exp_year": virtual_card["exp_year"],
                "cvc": virtual_card["cvc"],
            },
        }

        async with self._browser_page() as page:
            self._log_step("navigate", f"Navigating to {site}", "in_progress")
            await page.goto(booking_url, timeout=30_000)
            return await self._agent_loop(page, context)

    # ------------------------------------------------------------------
    # Claude vision agent loop
    # ------------------------------------------------------------------

    async def _agent_loop(self, page, context: dict) -> str:
        """
        Repeatedly: screenshot → ask Claude what to do → execute → repeat.
        Returns a confirmation number when Claude signals "done".
        """
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        for step_num in range(self.MAX_AGENT_STEPS):
            screenshot_bytes = await page.screenshot(type="png")
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": screenshot_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": self._build_prompt(context, step_num),
                            },
                        ],
                    }
                ],
            )

            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            action = json.loads(raw)

            action_type = action.get("action", "wait")
            thought = action.get("thought", "")

            # Only store screenshots on error or final confirmation (saves DB space)
            save_screenshot = action_type in ("done", "error")
            self._log_step(
                f"step_{step_num}",
                f"[{action_type}] {thought}",
                "in_progress" if action_type not in ("done", "error") else action_type,
                screenshot_b64=screenshot_b64 if save_screenshot else None,
            )

            if action_type == "done":
                confirmation = action.get("confirmation_number", "")
                self._log_step("done", f"Booking confirmed: {confirmation}", "success")
                return confirmation

            if action_type == "error":
                msg = action.get("error_message", "Agent reported an error")
                self._log_step("error", msg, "error", screenshot_b64=screenshot_b64)
                raise RuntimeError(msg)

            await self._execute_action(page, action)

        raise RuntimeError(f"Agent reached {self.MAX_AGENT_STEPS} steps without completing the booking")

    def _build_prompt(self, context: dict, step_num: int) -> str:
        goal = context.get("goal", "")

        if goal == "book_flight":
            carrier_name = context.get("carrier_name", context.get("carrier", "airline"))
            task = (
                f"Book a {carrier_name} flight on {context.get('site')}:\n"
                f"  Flight: {context.get('flight_number')} departing {context.get('depart_date')}\n"
                f"  Route: {context.get('origin')} → {context.get('destination')}\n"
                f"  Cabin: {context.get('cabin')}\n"
                f"  Passenger: {json.dumps(context['passenger'])}\n"
                f"  Payment: Visa virtual card ending "
                f"{context['virtual_card']['number'][-4:]} "
                f"exp {context['virtual_card']['exp_month']}/{context['virtual_card']['exp_year']}"
            )
        else:
            task = (
                f"Book a hotel room at {context.get('hotel_name')} on {context.get('site')}:\n"
                f"  Check-in: {context.get('check_in')}   Check-out: {context.get('check_out')}\n"
                f"  Room type: {context.get('room_type')}\n"
                f"  Guest: {json.dumps(context['passenger'])}\n"
                f"  Payment: Visa virtual card ending "
                f"{context['virtual_card']['number'][-4:]} "
                f"exp {context['virtual_card']['exp_month']}/{context['virtual_card']['exp_year']}"
            )

        return f"""You are controlling a web browser to complete a booking. Step {step_num + 1} of max {self.MAX_AGENT_STEPS}.

Task:
{task}

Look at the screenshot and decide the SINGLE next action. Return ONLY a JSON object — no markdown, no explanation:

{{
  "thought": "what you see and why you're taking this action",
  "action": "click" | "type" | "select" | "scroll_down" | "scroll_up" | "wait" | "done" | "error",
  "x": <integer pixel x for click/type>,
  "y": <integer pixel y for click/type>,
  "text": "<text to type>",
  "confirmation_number": "<PNR or record locator, for done action only>",
  "error_message": "<reason, for error action only>"
}}

Rules:
- One action per response. Click a field first, then type in the next step.
- Use "done" ONLY after seeing a booking confirmation page with a record locator / PNR.
- Use "error" if booking is impossible (sold out, card declined, unsupported flow).
- If a cookie banner or popup appears, dismiss it before doing anything else.
- Do not re-enter information already submitted in a previous step.
- Prefer clicking visible button labels and input labels over guessing coordinates.
"""

    async def _execute_action(self, page, action: dict) -> None:
        action_type = action.get("action")
        x = action.get("x")
        y = action.get("y")

        if action_type == "click":
            await page.mouse.click(x, y)
            await page.wait_for_timeout(800)

        elif action_type == "type":
            if x is not None and y is not None:
                await page.mouse.click(x, y)
                await page.wait_for_timeout(300)
            await page.keyboard.type(action.get("text", ""), delay=50)

        elif action_type == "scroll_down":
            await page.mouse.wheel(0, 600)
            await page.wait_for_timeout(400)

        elif action_type == "scroll_up":
            await page.mouse.wheel(0, -600)
            await page.wait_for_timeout(400)

        elif action_type == "wait":
            await page.wait_for_timeout(2_000)

        # "select" — Claude should click the dropdown then click the option value;
        # fallback: treat like click at coordinates
        elif action_type == "select":
            if x is not None and y is not None:
                await page.mouse.click(x, y)
                await page.wait_for_timeout(600)

    # ------------------------------------------------------------------
    # Browser context manager
    # ------------------------------------------------------------------

    @contextlib.asynccontextmanager
    async def _browser_page(self):
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            if settings.browserless_url:
                browser = await p.chromium.connect(settings.browserless_url)
            else:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                )

            ctx = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await ctx.new_page()
            try:
                yield page
            finally:
                await browser.close()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_step(
        self,
        step: str,
        action: str,
        result: str,
        screenshot_b64: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        from app.models import AgentLog

        log = AgentLog(
            booking_id=self.booking_id,
            step=step,
            action=action,
            result=result,
            screenshot_b64=screenshot_b64,
            error_message=error_message,
        )
        self.db.add(log)
        self.db.commit()
