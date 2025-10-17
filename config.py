from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """
    Loads all configuration and secrets from environment variables
    (typically from a .env file).
    """
    
    # API Keys
    GOOGLE_API_KEY: str
    GITHUB_TOKEN: str

    # Project config
    GITHUB_USER: str
    STUDENT_SECRET: str
    
    # Points to the .env file and ignores extra env vars
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def validate_all_present(self):
        """Raises a clear error if any required setting is missing."""
        missing = []
        for name, value in self:
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(name.upper())
        
        if missing:
            raise ValueError(f"Missing required .env variables: {', '.join(missing)}")
        
        # Obscure the token in logs
        print("Settings loaded:")
        print(f"  GITHUB_USER: {self.GITHUB_USER}")
        print(f"  STUDENT_SECRET: {'*' * 8}")
        print(f"  GITHUB_TOKEN: {'*' * 8}")
        print(f"  GOOGLE_API_KEY: {'*' * 8}")


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings object.
    The first call will load from .env and validate.
    """
    settings = Settings()
    settings.validate_all_present()
    return settings