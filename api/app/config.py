from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    pg_primary_dsn: str = "postgresql://app:app_pass@pg-primary:5432/appdb"

    redis_url: str = "redis://redis:6379/0"

    jwt_secret: str = "K2yBfQFgPnFvCBecUHHqb4h8geNPs3aqsvs4N1A9ouA"
    jwt_alg: str = "HS256"
    jwt_ttl_seconds: int = 3600

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()