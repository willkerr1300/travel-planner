# End-to-End Travel Booking Agent

An AI agent that takes a trip request in plain English, searches flights/hotels/activities, presents options, and actually completes the bookings on your behalf — no handing you off to other sites, no re-entering your info twelve times.

---

## Core Features

### Trip Request

- User types something like "fly me to Tokyo in October, 10 days, under $3,000, hotel near Shinjuku"
- Agent parses that into a structured spec: origin, destination, dates, budget, preferences
- On account creation, user stores traveler info once (passport, TSA number, seat preferences, loyalty numbers) — agent uses it on every booking

### Search & Planning

- Agent searches flights (via Kayak/Google Flights scraping or Amadeus API), hotels (Booking.com or direct), and activities (Viator)
- Generates 2–3 complete itinerary options with total cost breakdown
- User picks one or says "cheaper flights but nicer hotel" — agent adjusts and re-presents
- One-click approve to kick off booking

### Booking Execution (the hard part)

- Agent uses browser automation (Playwright) to navigate to each site and complete the booking using stored traveler info and a virtual card
- Handles seat selection screens, loyalty number fields, cancellation policy confirmations, all the annoying intermediate steps
- Sends structured confirmation summary when done: flight PNR, hotel confirmation number, check-in times, all in one place

### Trip Management

- Monitors booked trips for schedule changes or cancellations
- Emails user if a flight changes or a cheaper fare appears on a refundable ticket
- Can modify bookings ("extend my hotel by one night") on request

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Next.js | Fast to build, familiar |
| Auth | NextAuth with Google | Simple OAuth, matches travel use case |
| Browser Automation | Playwright + Browserless.io | Scalable headless Chrome, handles most booking sites |
| Agent/AI | Claude API | Vision + reasoning for navigating site UIs |
| Flight Data | Amadeus API (or scraping) | Structured search before handing off to booking |
| Backend | FastAPI (Python) | Async, good for long-running booking tasks |
| Database | PostgreSQL | User profiles, booking state, trip history |
| Payment | Stripe Issuing (virtual cards) | Agent gets a single-use card per booking — no stored card numbers on airline sites |
| Email | SendGrid | Booking confirmations, trip alerts |
| Hosting | EC2 (agent) + Vercel (frontend) | Agent needs persistent compute for long booking sessions |
| Task Queue | Celery + Redis | Bookings run async, user gets status updates while agent works |

---

## Database Schema (simplified)

- **users** — id, email, passport info, TSA/Known Traveler, seat preferences, loyalty numbers
- **trips** — id, user_id, status, destination, dates, budget, approved_itinerary
- **bookings** — id, trip_id, type (flight/hotel/activity), status, confirmation_number, details
- **agent_logs** — id, trip_id, step, screenshot_url, error (for debugging failed bookings)

---

## Build Order

**Week 1–2:** Auth + user profile setup. Get traveler info storage right from the start — passport numbers, loyalty accounts, payment method. Security here matters.

**Week 3–4:** Search layer. Connect Amadeus for flights, Booking.com API for hotels. Build the trip spec parser and itinerary generator. No booking yet — just solid search and presentation.

**Week 5–7:** Booking execution for one airline (United or American) and one hotel chain (Marriott). Get one full end-to-end flow working reliably before touching anything else. This is the hardest engineering work.

**Week 8–9:** Expand to 3–4 more sites. Add Expedia as a fallback for hotels. Add one activity platform (Viator). Build the confirmation parser that extracts structured data from confirmation emails.

**Week 10–12:** Trip monitoring, change detection, and the modification flow. Polish the frontend booking status UI so users can watch the agent work in real time.

---

## Key Decisions to Make Early

**Virtual cards are non-negotiable** — use Stripe Issuing to generate a single-use card per booking. Never store a real card number in a site's checkout form. This also gives you chargeback protection if a booking goes wrong.

**Start with one site and make it bulletproof** — the temptation is to support 20 airlines on launch. Don't. A 95% success rate on United beats a 60% success rate on ten airlines. Users will not trust an agent that fails.

**Vision-based navigation beats CSS selectors** — airline sites change their UI constantly. Use the Claude vision API to identify form fields by what they look like, not by their HTML class names. It's slower to build but survives site redesigns.

**Don't touch flights that require calling the airline** — basic economy changes, lap infant add-ons, anything that requires a phone call is out of scope for v1. Filter these out during search and tell the user upfront.

**Amadeus API has a free sandbox** — use it heavily during development. Production access requires an application but it's free at low volume, which covers your whole beta period.
