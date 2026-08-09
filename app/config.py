from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    tavily_api_key: str | None = None
    openrouter_api_key: str | None = None
    nvidia_api_key: str | None = None
    mongodb_uri: str | None = None
    ai_provider: str = "openrouter"
    ai_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    gemini_api_key: str | None = None
    x_auth_token: str | None = None
    
    # Autonomous Settings
    discovery_interval_minutes: int = 30
    publish_threshold: int = 75
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()  # type: ignore
