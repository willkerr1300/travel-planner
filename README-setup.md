# Developer Setup Guide

## What's been built

### Week 1–2 — Auth + traveler profile

- **Google OAuth 2.0** via NextAuth 5 (server-side session, JWT strategy)
- **Protected routes** — `/dashboard` and `/profile` redirect to `/` when unauthenticated
- **Traveler profile** — users store passport number, TSA Known Traveler number, seat and meal preferences, and loyalty program numbers once; the agent reuses this on every booking
- **Application-layer encryption** — passport and TSA numbers are encrypted with Fernet before being written to the database; raw values are never stored in plaintext
- **Internal API key** — all Next.js → FastAPI calls require a shared secret in the `x-api-key` header; FastAPI is never exposed directly to the browser

### Week 3–4 — Search layer

- **Natural-language trip spec parser** — uses the Claude API to turn a plain-English request ("fly me to Tokyo in October, 10 days, under $3,000") into a structured spec (`origin`, `destination`, `depart_date`, `return_date`, `budget_total`, etc.). Falls back to a built-in rule-based parser when no Anthropic key is set.
- **Amadeus flight search** — queries the Amadeus v2 Flight Offers Search API for real flight options. Falls back to realistic mock data when no Amadeus credentials are set.
- **Amadeus hotel search** — queries the Amadeus v3 Hotel Offers API. Same mock fallback applies.
- **Itinerary builder** — packages search results into 3 curated options: Budget, Best Value, and Premium, each with a total cost breakdown.
- **Trip approval** — user picks one option; it's persisted as `approved_itinerary` on the trip.
- **Dashboard** — live trip request form and a list of past trips with status badges.
- **`/trips/[id]` page** — shows the 3 itinerary option cards with flight and hotel details.
- **`trips` and `bookings` tables** — added via Alembic migration 002.

### Week 5–7 — Booking execution

- **Celery + Redis task queue** — booking runs asynchronously after approval; the user sees live status updates without waiting.
- **Stripe Issuing virtual cards** — a single-use Visa card is created per booking, capped at the booking amount. The card is automatically cancelled if the booking fails.
- **Vision-based booking agent** — uses Playwright for browser automation and Claude claude-sonnet-4-6's vision API to navigate booking sites. Claude receives a screenshot at each step and decides the next action (click, type, scroll) based purely on what it sees — no fragile CSS selectors.
- **Supported sites** — United Airlines (carrier code `UA`) for flights; Marriott for hotels.
- **Mock mode** (default) — simulates the full booking pipeline with realistic logs and random confirmation numbers. No browser, no real site access, no Stripe account required. Turn it off only in a configured live environment.
- **Agent logs** — every step is recorded in the `agent_logs` table (step name, action taken, result, and screenshot for error/confirm steps).
- **Booking status UI** — the trip detail page shows a live-updating panel with per-booking status, a step-by-step timeline of agent actions, and confirmation numbers on success.
- **Profile extended** — first name, last name, date of birth, and phone number added to the profile (required for passenger forms on booking sites).

---

## Prerequisites

- Node.js 20+
- Python 3.12 (required — `psycopg2-binary` wheels are not available for 3.14+)
- Docker Desktop (must be running before any `docker` commands)

---

## 1. Start Docker services

From the project root:

```bash
docker compose up -d
```

If that fails with "unknown shorthand flag", use the v1 CLI:

```bash
docker-compose up -d
```

This starts three services:

| Service | URL / Port | Credentials |
|---|---|---|
| PostgreSQL | `localhost:5432` | travelplanner / travelplanner |
| pgAdmin | `http://localhost:5050` | admin@admin.com / admin |
| Redis | `localhost:6379` | no auth |

---

## 2. Backend

### 2a. Install dependencies

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2b. Install Playwright browsers (Week 5+, live mode only)

Playwright needs its browser binaries downloaded separately from the Python package:

```bash
playwright install chromium
```

This is only required when running with `BOOKING_MOCK_MODE=false`. In mock mode (the default), no browser is launched and this step can be skipped.

### 2c. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

#### Week 1–2 variables (required)

| Variable | How to get it |
|---|---|
| `DATABASE_URL` | Pre-filled for local Docker |
| `INTERNAL_API_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` — must match frontend |
| `ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

#### Week 3–4 variables (optional — mock fallbacks exist)

| Variable | How to get it | Required? |
|---|---|---|
| `AMADEUS_CLIENT_ID` | Free sandbox at [developers.amadeus.com](https://developers.amadeus.com) | No — mock data used if empty |
| `AMADEUS_CLIENT_SECRET` | Same as above | No |
| `AMADEUS_ENV` | `test` for sandbox (default) | No |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | No — rule-based parser used if empty |

#### Week 5–7 variables (optional — mock mode handles everything by default)

| Variable | How to get it | Required? |
|---|---|---|
| `CELERY_BROKER_URL` | Pre-filled for local Docker Redis | No — default is `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Same | No |
| `STRIPE_SECRET_KEY` | [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys) | No — mock card data used if empty |
| `BROWSERLESS_URL` | See below | No — local Playwright used if empty |
| `BOOKING_MOCK_MODE` | `true` (default) or `false` | No |

---

### Manual setup steps for Week 5–7 credentials

**Getting Amadeus sandbox credentials:**
1. Go to [developers.amadeus.com](https://developers.amadeus.com) and sign up
2. Create a new Self-Service app
3. Copy the **API Key** (`AMADEUS_CLIENT_ID`) and **API Secret** (`AMADEUS_CLIENT_SECRET`)
4. Leave `AMADEUS_ENV=test` — the sandbox is free and covers all development

**Getting an Anthropic API key:**
1. Go to [console.anthropic.com](https://console.anthropic.com) and sign in
2. **API Keys** → **Create Key**
3. Copy into `ANTHROPIC_API_KEY`

**Setting up Stripe Issuing (live mode only):**
1. Go to [dashboard.stripe.com](https://dashboard.stripe.com) and sign in
2. Navigate to **Developers** → **API Keys** → copy the **Secret key** into `STRIPE_SECRET_KEY`
3. Stripe Issuing requires a separate application — go to **Issuing** in the dashboard and apply for access (typically approved within a few days for US businesses)
4. Create a **Restricted Key** with `issuing_card_number:read` permission for retrieving raw card numbers server-side
5. In test mode, use `sk_test_...` keys — Stripe provides test card numbers automatically

**Setting up Browserless.io (optional, replaces local Playwright):**

Option A — Local Docker (simplest for development):
```bash
docker run -p 3000:3000 ghcr.io/browserless/chromium
```
Then set `BROWSERLESS_URL=ws://localhost:3000`.

Option B — Browserless.io cloud:
1. Sign up at [browserless.io](https://www.browserless.io)
2. Copy your token
3. Set `BROWSERLESS_URL=wss://chrome.browserless.io?token=YOUR_TOKEN`

If neither is set, the agent launches a local Chromium via Playwright directly. This works fine for development but is not suitable for production.

**Switching to live booking mode:**
1. Ensure `ANTHROPIC_API_KEY` is set (Claude vision is required)
2. Ensure `STRIPE_SECRET_KEY` is set (or leave empty to skip real card creation — agent will use a mock card)
3. Run `playwright install chromium` if using local Playwright
4. Set `BOOKING_MOCK_MODE=false` in `.env`

> **Warning:** Live mode will attempt to navigate real airline and hotel websites and complete real bookings. Only enable it with test/sandbox Stripe keys and on itineraries you actually intend to book.

**Google OAuth setup:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → **APIs & Services** → **Credentials** → **Create OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Authorized redirect URI: `http://localhost:3000/api/auth/callback/google`
5. Copy Client ID and Secret into `frontend/.env.local`

---

### 2d. Run migrations

```bash
alembic upgrade head
```

> `alembic upgrade head` is idempotent — it only runs migrations that haven't been applied yet. Run it whenever you pull new code.

Migration history:
- `001` — `users` table (auth + encrypted profile fields)
- `002` — `trips` and `bookings` tables
- `003` — `agent_logs` table, `virtual_card_id` on bookings, personal info columns on users (first_name, last_name, date_of_birth, phone)

### 2e. Start the API server

```bash
uvicorn app.main:app --reload
```

### 2f. Start the Celery worker (Week 5+)

In a second terminal, with the venv activated:

```bash
cd backend
celery -A app.worker worker --loglevel=info
```

The worker must be running for bookings to execute. In mock mode, tasks still go through Celery — they just simulate the steps without a real browser.

**Troubleshooting:**
- If `pip install` fails on `psycopg2-binary`, you are likely on Python 3.14. Install Python 3.12 and recreate the venv.
- If Celery can't connect to Redis, make sure `docker compose up -d` ran successfully and port 6379 is not blocked.
- If `playwright install chromium` fails behind a proxy, set `PLAYWRIGHT_DOWNLOAD_HOST` to an accessible mirror.

---

## 3. Frontend

### 3a. Install dependencies

```bash
cd frontend
npm install
```

### 3b. Configure environment

```bash
cp env.local.example .env.local
```

Edit `.env.local`:

| Variable | Where to get it |
|---|---|
| `AUTH_SECRET` | `openssl rand -base64 32` |
| `AUTH_URL` | `http://localhost:3000` |
| `GOOGLE_CLIENT_ID` | Google Cloud Console (see above) |
| `GOOGLE_CLIENT_SECRET` | Same |
| `INTERNAL_API_KEY` | Same value as in `backend/.env` |
| `BACKEND_URL` | `http://localhost:8000` |

### 3c. Start the dev server

```bash
npm run dev
```

---

## What's running

| Service | URL |
|---|---|
| Next.js frontend | http://localhost:3000 |
| FastAPI backend | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 |
| Redis | localhost:6379 |

---

## How the end-to-end booking flow works

1. User types a request — _"Fly me to Tokyo in October, 10 days, under $3,000, hotel near Shinjuku"_
2. Backend parses it (Claude or rule-based fallback) and searches Amadeus (or returns mock data)
3. Itinerary builder packages results into up to 3 options (Budget / Best Value / Premium)
4. User views `/trips/[id]` and clicks **Choose this trip** to approve one option
5. User fills in first name, last name (and optionally phone, date of birth, loyalty numbers) in `/profile` if not already done
6. User clicks **Book this trip** — backend creates Booking records, enqueues a Celery task, and returns 202
7. The Celery worker picks up the task:
   - Creates a Stripe Issuing virtual card capped at the booking amount
   - Runs the `BookingAgent` for the flight (United.com) then the hotel (Marriott.com)
   - In mock mode: simulates each step with realistic delays and a random confirmation number
   - In live mode: launches Playwright, screenshots the page, asks Claude what to do next, executes the action, repeats until a confirmation number is on screen
8. The `/trips/[id]` page polls `/api/trips/[id]/bookings` every 3 seconds and shows the live agent log timeline
9. When confirmed, each booking displays its confirmation number

> **No credentials? No problem.** With `BOOKING_MOCK_MODE=true` (the default), the full pipeline — request → parse → options → approve → book → live status → confirmation — works without Amadeus, Anthropic, Stripe, or Playwright credentials.

---

## New API endpoints (Week 5–7)

| Method | Path | Description |
|---|---|---|
| `POST` | `/trips/{id}/book` | Trigger async booking (202 Accepted). Requires `approved` status and first+last name in profile. |
| `GET` | `/trips/{id}/bookings` | List bookings with agent log entries. Polled by the frontend every 3 s. |

All endpoints require the same `x-api-key` and `x-user-email` headers. Full interactive docs at **http://localhost:8000/docs**.

---

## Project structure (Week 5–7 additions highlighted)

```
backend/
  app/
    routers/
      profile.py        ← updated: adds first_name, last_name, date_of_birth, phone
      trips.py          ← updated: adds /book and /bookings endpoints
    services/
      amadeus.py
      trip_parser.py
      itinerary.py
      virtual_card.py   ← NEW: Stripe Issuing + mock card
      booking_agent.py  ← NEW: Playwright + Claude vision agent + mock mode
    tasks/              ← NEW directory
      __init__.py       ← NEW: Celery app instance
      booking_tasks.py  ← NEW: execute_trip_bookings Celery task
    worker.py           ← NEW: Celery worker entry point
    models.py           ← updated: AgentLog model, profile fields, virtual_card_id
    config.py           ← updated: Stripe, Browserless, Redis, mock mode settings
  alembic/
    versions/
      001_create_users_table.py
      002_create_trips_and_bookings.py
      003_add_booking_agent.py       ← NEW migration
  requirements.txt      ← updated: adds celery[redis], playwright, stripe
  .env.example          ← updated: adds Week 5–7 env vars

docker-compose.yml      ← updated: adds Redis service

frontend/
  app/
    api/
      trips/
        [id]/
          book/
            route.ts      ← NEW: POST → trigger booking
          bookings/
            route.ts      ← NEW: GET → booking status (polled)
    trips/
      [id]/page.tsx       ← updated: shows BookingStatus panel after approval
  components/
    BookingStatus.tsx     ← NEW: live-polling booking status + agent log timeline
    ItineraryCard.tsx     ← updated: removed Week 5 placeholder text
    ProfileForm.tsx       ← updated: adds Personal Info section
```
