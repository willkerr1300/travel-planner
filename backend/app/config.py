from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    internal_api_key: str
    encryption_key: str

    # Amadeus API — get sandbox keys at https://developers.amadeus.com
    # Leave empty to run in mock mode (realistic sample data, no real API calls)
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    # "test" uses test.api.amadeus.com; "production" uses api.amadeus.com
    amadeus_env: str = "test"

    # Anthropic API — get key at https://console.anthropic.com
    # Leave empty to use the built-in rule-based trip spec parser fallback
    # Required for real booking execution (vision agent uses claude-sonnet-4-6)
    anthropic_api_key: str = ""

    # Celery + Redis — task queue for async booking execution
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Stripe Issuing — single-use virtual cards per booking
    # Leave empty to use mock card data (no real Stripe calls)
    stripe_secret_key: str = ""

    # Browserless.io — scalable headless Chrome
    # Leave empty to launch a local Playwright browser instead
    browserless_url: str = ""

    # When true (default), the booking agent simulates steps without a real
    # browser. Set to false only after Playwright is installed and you have
    # live site access.
    booking_mock_mode: bool = True

    # SendGrid — transactional email for booking confirmations
    # Leave empty to skip email delivery (best-effort, no error raised)
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "confirmations@travelplanner.app"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
