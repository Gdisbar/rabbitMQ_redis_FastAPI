from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    pg_primary_dsn: str = "postgresql://user123:app_pwd123@pg-primary:5432/appdb"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()