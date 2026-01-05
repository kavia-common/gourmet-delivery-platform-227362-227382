import os
from dataclasses import dataclass
from typing import List, Optional


def _split_csv(value: str) -> List[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_name: str
    app_version: str
    environment: str

    cors_origins: List[str]

    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    database_url: str

    payments_provider: str
    payments_webhook_secret: Optional[str]


def _build_database_url_from_postgres_env() -> str:
    """
    Build SQLAlchemy database URL from the database container env vars.

    Env vars are expected to be injected by the platform (do not hardcode values).
    """
    pg_user = os.getenv("POSTGRES_USER", "")
    pg_password = os.getenv("POSTGRES_PASSWORD", "")
    pg_db = os.getenv("POSTGRES_DB", "")
    # POSTGRES_URL is typically host; may include scheme in some setups.
    pg_host = os.getenv("POSTGRES_URL", "")
    pg_port = os.getenv("POSTGRES_PORT", "")

    # Handle cases where POSTGRES_URL might already contain a scheme like postgres://
    host = pg_host
    if "://" in host:
        host = host.split("://", 1)[1]

    if not (pg_user and pg_password and pg_db and host and pg_port):
        return ""

    return f"postgresql+psycopg2://{pg_user}:{pg_password}@{host}:{pg_port}/{pg_db}"


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load and return application settings from environment variables."""
    app_name = os.getenv("APP_NAME", "Gourmet Delivery Platform API")
    app_version = os.getenv("APP_VERSION", "0.1.0")
    environment = os.getenv("ENVIRONMENT", "development")

    cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    cors_origins = _split_csv(cors_origins_raw) if cors_origins_raw else ["http://localhost:3000"]

    jwt_secret = os.getenv("JWT_SECRET", "change-me")
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    explicit_db_url = os.getenv("DATABASE_URL", "").strip()
    database_url = explicit_db_url if explicit_db_url else _build_database_url_from_postgres_env()

    payments_provider = os.getenv("PAYMENTS_PROVIDER", "mock")
    payments_webhook_secret = os.getenv("PAYMENTS_WEBHOOK_SECRET") or None

    return Settings(
        app_name=app_name,
        app_version=app_version,
        environment=environment,
        cors_origins=cors_origins,
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        database_url=database_url,
        payments_provider=payments_provider,
        payments_webhook_secret=payments_webhook_secret,
    )
