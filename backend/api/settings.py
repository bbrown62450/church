"""Runtime configuration for the API, read from environment variables."""
import os
from dataclasses import dataclass, field
from functools import lru_cache

from google_oauth import GoogleOAuthConfig


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    cors_origins: tuple[str, ...]
    app_env: str = "development"           # APP_ENV; api.startup.check_app_env validates it
    log_level: str = "INFO"                # LOG_LEVEL; api.logging_config validates it
    # Slice 5b-2: the Google OAuth client Streamlit used (same id and secret) and this
    # deployment's /gmail/callback page; api.startup.log_gmail_state says what is missing.
    google_client_id: str = ""
    google_client_secret: str = field(default="", repr=False)
    google_oauth_redirect_uri: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def google_oauth(self) -> GoogleOAuthConfig:
        return GoogleOAuthConfig(self.google_client_id, self.google_client_secret, self.google_oauth_redirect_uri)

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def token_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"


def _split_origins(raw: str) -> tuple[str, ...]:
    return tuple(o.strip().rstrip("/") for o in raw.split(",") if o.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings(
        supabase_url=os.environ.get("SUPABASE_URL", "").strip().rstrip("/"),
        cors_origins=_split_origins(os.environ.get("CORS_ORIGINS", "http://localhost:3000")),
        app_env=os.environ.get("APP_ENV", "").strip().lower() or "development",
        log_level=os.environ.get("LOG_LEVEL", "").strip() or "INFO",
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
        google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "").strip(),
        google_oauth_redirect_uri=os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "").strip(),
    )
