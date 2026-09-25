"""Runtime configuration for the API, read from environment variables."""
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    cors_origins: tuple[str, ...]

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
    )
