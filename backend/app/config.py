"""
Configuration management for the A/B Testing Platform.

Using pydantic for automatic validations, .env file support and
no hardcoded secrets in code

Works by reading environment variables first then falls back to
.env file if variable is not found or raises validation error if the variable
is missing
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
        Application settings loaded from environment variables.

        In production, these come from actual env vars (set in Docker/AWS).
        In development, they're loaded from a .env file.
    """

    # Database
    DATABASE_URL: str = "postgresql://localhost:5432/ab_testing_db"

    # Application
    APP_NAME: str = "A/B Testing Platform"
    DEBUG: bool = True

    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()