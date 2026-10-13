from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    pg_primary_dsn: str = "postgresql://user123:app_pwd123@pg-primary:5432/appdb"

    redis_url: str = "redis://redis:6379/0"

    jwt_secret: str = "K2yBfQFgPnFvCBecUHHqb4h8geNPs3aqsvs4N1A9ouA"
    jwt_alg: str = "HS256"
    jwt_ttl_seconds: int = 3600

    # rate limits
    rl_unauth_limit: int = 1           # per IP
    rl_unauth_window_ms: int = 60_000   # 1 minute
    rl_auth_limit: int = 15           # per user
    rl_auth_window_ms: int = 60_000
    rl_burst_limit: int = 800           # global
    rl_burst_window_ms: int = 1_000     # 1 second

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()