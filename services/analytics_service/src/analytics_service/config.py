from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration settings."""

    service_name: str = "analytics_service"
    database_url: str
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    rabbitmq_exchange: str = "bookstore.events"

    class Config:
        env_prefix = ""
        env_file = ".env"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()  # type: ignore[arg-type]


