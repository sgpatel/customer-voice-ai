# app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Use .env file in development, rely on environment variables in production
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    PROJECT_NAME: str = "Mention Analyzer API"
    API_V1_STR: str = "/api/v1"

    # OpenAI API Key
    OPENAI_API_KEY: str

    # LLM Model to use
    OPENAI_MODEL: str = "gpt-4o-mini" # Or your preferred model

    # Database URL (e.g., "postgresql+asyncpg://user:password@host:port/db")
    DATABASE_URL: str

    # Celery Broker URL (e.g., "redis://localhost:6379/0")
   # CELERY_BROKER_URL: str
    # Celery Result Backend URL (e.g., "redis://localhost:6379/1")
   # CELERY_RESULT_BACKEND: str

# Instantiate settings
settings = Settings()

# Basic Logging Setup (can be moved to logging_config.py for more detail)
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)