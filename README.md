# Travel Planner

An AI agent that takes a trip request in plain English, searches real flight and hotel inventory, presents curated itinerary options, and autonomously completes the bookings on your behalf — navigating airline and hotel websites with a vision-based browser agent so you never have to re-enter your details.

---

## How it works

```
"Fly me to Tokyo in June for 10 days, budget $3000, hotel near Shinjuku"
        │
        ▼
  Trip Spec Parser ──── Claude Sonnet 4.6 (or rule-based fallback)
        │
        ▼
  Amadeus Flight + Hotel Search ──── mock data fallback
        │
        ▼
  Itinerary Builder ──── 3 options: Budget / Best Value / Premium
        │
        ▼
  User approves one option
        │
        ▼
  Booking Agent ──────── Playwright + Claude vision API
  (async, Celery)         navigates airline + hotel sites,
        │                 fills forms using saved profile,
        │                 pays with single-use virtual card
        ▼
  Confirmed ──── email confirmation + hourly monitoring for
                 schedule changes and price drops
```

The agent uses Claude Sonnet 4.6's vision API to interpret live screenshots at each step — no fragile CSS selectors. The user's saved traveler profile (passport, TSA number, loyalty numbers, seat preferences) is used on every booking automatically.

---

## Features

**Search and planning**
- Parses plain-English trip requests into structured specs (origin, destination, dates, budget, cabin class, hotel area)
- Searches the Amadeus API for real flights and hotels; falls back to realistic mock data with no credentials
- Presents 2–3 curated itinerary packages with total cost breakdowns and within-budget flags

**Booking execution**
- Vision-based browser agent reads booking site screenshots and decides what to do next (click, type, scroll) — no hardcoded selectors
- Generates a single-use Stripe Issuing virtual card per booking, capped at the booking amount; card is automatically voided if booking fails
- Supported carriers: United, Delta, American, Southwest
- Supported hotels: Expedia (default), Marriott.com (when user has Marriott loyalty number)
- Full mock mode simulates every step with realistic timing and confirmation numbers — no live site access required

**Trip management**
- Live booking status UI polls every 3 seconds and shows a step-by-step agent action timeline
- Hourly monitoring scans all confirmed trips for flight schedule changes and price drops; sends email alerts on new findings
- Natural-language modification endpoint: "extend my hotel by 2 nights", "upgrade to business class"
- Consolidated confirmation email sent via SendGrid after all bookings complete

**Security**
- Passport and TSA numbers encrypted with Fernet before storage — never written to the database in plaintext
- Google OAuth 2.0 via NextAuth 5; FastAPI is never directly accessible from the browser
- All Next.js → FastAPI calls go through server-side API routes that inject a shared secret header

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Auth | NextAuth 5 (Google OAuth) |
| Backend API | FastAPI (Python 3.12), SQLAlchemy, Alembic |
| Database | PostgreSQL 16 |
| Task queue | Celery 5 + Redis 7 |
| Browser automation | Playwright 1.49 |
| AI | Claude Sonnet 4.6 (Anthropic) — trip parsing + vision agent |
| Flight/hotel search | Amadeus API |
| Payments | Stripe Issuing (single-use virtual cards) |
| Email | SendGrid |
| Hosting | Vercel (frontend), EC2 (backend) |

---

## Quick start

Everything works with zero API credentials in mock mode — real flight data, real browser sessions, and real emails are optional upgrades.

**Prerequisites:** Python 3.12, Node.js 20+, Docker Desktop

```bash
# 1. Start PostgreSQL and Redis
docker compose up -d

# 2. Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in INTERNAL_API_KEY and ENCRYPTION_KEY (see below)
alembic upgrade head
uvicorn app.main:app --reload

# 3. Celery worker (separate terminal)
celery -A app.worker worker --loglevel=info

# 4. Frontend (separate terminal)
cd frontend
npm install
cp env.local.example .env.local   # fill in AUTH_SECRET, Google OAuth, INTERNAL_API_KEY
npm run dev
```

Open `http://localhost:3000`.

**Generate the two required keys:**
```bash
# INTERNAL_API_KEY — paste into both backend/.env and frontend/.env.local
python -c "import secrets; print(secrets.token_hex(32))"

# ENCRYPTION_KEY — backend/.env only
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

For Google OAuth, create a Web Application credential in [Google Cloud Console](https://console.cloud.google.com) and add `http://localhost:3000/api/auth/callback/google` as an authorized redirect URI.

See [SETUP.md](SETUP.md) for the complete walkthrough including all optional API integrations and production deployment on Vercel + EC2.

---

## Mock mode

By default, `BOOKING_MOCK_MODE=true`. In this mode:

- The booking agent simulates every step (navigate, fill passenger info, select seat, payment, confirm) with realistic delays and a random confirmation number
- No Playwright browser is launched and no real site is contacted
- No Stripe account needed — a test card number is used
- The full pipeline (request → parse → options → approve → book → live status → confirmation) works end-to-end

Set `BOOKING_MOCK_MODE=false` and add `ANTHROPIC_API_KEY` and `STRIPE_SECRET_KEY` to switch to live mode.

---

## Configuration

All optional — the app runs fully in mock mode without any of these.

| Variable | Purpose | Where to get it |
|---|---|---|
| `AMADEUS_CLIENT_ID` / `SECRET` | Real flight and hotel search | [developers.amadeus.com](https://developers.amadeus.com) — free sandbox |
| `ANTHROPIC_API_KEY` | Claude trip parser + vision booking agent | [console.anthropic.com](https://console.anthropic.com) |
| `STRIPE_SECRET_KEY` | Single-use virtual cards per booking | [dashboard.stripe.com](https://dashboard.stripe.com) — requires Issuing access |
| `SENDGRID_API_KEY` | Confirmation and alert emails | [app.sendgrid.com](https://app.sendgrid.com) |
| `BROWSERLESS_URL` | Cloud headless Chrome (replaces local Playwright) | [browserless.io](https://www.browserless.io) |

---

## Project structure

```
travel-planner/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point
│   │   ├── models.py             # SQLAlchemy models (User, Trip, Booking, AgentLog, TripAlert)
│   │   ├── routers/
│   │   │   ├── trips.py          # Trip CRUD, approve, book, bookings, alerts, modify
│   │   │   └── profile.py        # Traveler profile (encrypted passport, loyalty numbers)
│   │   ├── services/
│   │   │   ├── trip_parser.py    # NL → structured spec (Claude + rule-based fallback)
│   │   │   ├── amadeus.py        # Flight + hotel search (real + mock)
│   │   │   ├── itinerary.py      # Build Budget / Best Value / Premium options
│   │   │   ├── booking_agent.py  # Playwright + Claude vision booking agent
│   │   │   ├── virtual_card.py   # Stripe Issuing single-use cards
│   │   │   ├── confirmation.py   # Structured confirmation builder
│   │   │   ├── monitor.py        # Schedule change + price drop detection
│   │   │   ├── modification.py   # NL modification parser and handlers
│   │   │   └── email.py          # SendGrid confirmations and alerts
│   │   ├── tasks/
│   │   │   ├── booking_tasks.py  # Celery task: async booking execution
│   │   │   └── monitor_tasks.py  # Celery beat task: hourly trip monitoring
│   │   └── worker.py             # Celery worker entry point
│   ├── alembic/versions/         # 4 migrations (users → trips → agent → monitoring)
│   ├── tests/benchmark.py        # Service-level performance benchmarks
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── dashboard/            # Trip list + request form
│   │   ├── profile/              # Traveler profile editor
│   │   ├── trips/[id]/           # Trip detail: options, booking status, alerts, modify
│   │   └── api/trips/[id]/       # Server-side API bridge (book, bookings, alerts, modify)
│   └── components/
│       ├── BookingStatus.tsx     # Live-polling booking agent timeline
│       ├── ItineraryCard.tsx     # Flight + hotel option card
│       ├── TripAlerts.tsx        # Schedule change / price drop banners
│       ├── ModifyTrip.tsx        # Modification request form
│       └── ProfileForm.tsx       # Traveler profile editor
│
├── docker-compose.yml            # PostgreSQL + Redis + pgAdmin
├── SETUP.md                      # Full setup and deployment guide
└── PERFORMANCE.md                # Benchmark results and resume entry
```

---

## API reference

Interactive docs available at `http://localhost:8000/docs` when the backend is running.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/trips` | Parse request, search, return itinerary options |
| `GET` | `/trips` | List all trips for the authenticated user |
| `GET` | `/trips/{id}` | Get a single trip |
| `POST` | `/trips/{id}/approve` | Select an itinerary option |
| `POST` | `/trips/{id}/book` | Trigger async booking (returns 202 immediately) |
| `GET` | `/trips/{id}/bookings` | Booking status + agent logs (polled by frontend) |
| `GET` | `/trips/{id}/confirmation` | Structured confirmation for a completed trip |
| `GET` | `/trips/{id}/alerts` | Schedule change and price drop alerts |
| `POST` | `/trips/{id}/alerts/{alert_id}/read` | Mark alert as read |
| `POST` | `/trips/{id}/modify` | Apply a natural-language modification |
| `GET` | `/profile` | Get traveler profile |
| `POST` | `/profile` | Create or update traveler profile |

All endpoints require `x-user-email` and `x-api-key` headers, injected server-side by Next.js API routes.

---

## Trip status flow

```
parsing → searching → options_ready → approved → booking → confirmed
                   ↘ search_failed              ↘ booking_failed
```

Each booking within a trip: `pending → in_progress → confirmed | failed | unsupported`
