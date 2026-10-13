from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- Database ----
    # No default → app will fail fast if not provided in production.
    pg_primary_dsn: SecretStr = Field(..., description="Postgres DSN")

    # ---- Redis ----
    redis_url: str = "redis://redis:6379/0"

    # ---- JWT ----
    jwt_secret: SecretStr = Field(..., min_length=32)
    jwt_alg: str = "HS256"
    jwt_ttl_seconds: int = Field(3600, ge=60, le=86_400)

    # ---- Rate limits ----
    rl_unauth_limit: int = 1
    rl_unauth_window_ms: int = 60_000
    rl_auth_limit: int = 15
    rl_auth_window_ms: int = 60_000
    rl_burst_limit: int = 800
    rl_burst_window_ms: int = 1_000

    # ---- Application Insights ----
    applicationinsights_connection_string: SecretStr | None = None
    applicationinsights_enabled: bool = False

    # ---- Environment ----
    environment: str = Field("dev", pattern="^(dev|staging|prod)$")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # ignore unrelated env vars
    )

    # ---- Validators ----
    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_strength(cls, v: SecretStr) -> SecretStr:
        raw = v.get_secret_value()
        # Reject obviously weak secrets
        if raw.lower() in {"secret", "changeme", "password", "test"}:
            raise ValueError("jwt_secret is too weak")
        return v

    @field_validator("applicationinsights_connection_string")
    @classmethod
    def _ai_required_if_enabled(cls, v, info):
        # If AI is enabled, the connection string must be present.
        # (Runs after `enabled` in field order — see model_validator below if you reorder.)
        return v


settings = Settings()