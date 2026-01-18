from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str = "postgresql://sentiment_user:sentiment_pass@postgres:5432/sentiment_db"
    redis_url: str = "redis://redis:6379"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    alpha_vantage_api_key: str = "demo"
    news_api_key: str = "demo"
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-in-production"
    cache_ttl_seconds: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
