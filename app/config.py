from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 30
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()