from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_allow_origins: str = "http://localhost:3000"

    # Loglama (bkz. app/core/logging.py)
    # DEBUG: LLM'e giden tam prompt'u da basar.
    log_level: str = "INFO"

    # LLM (provider-agnostic; see docs/AGENT.md)
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1"
    ollama_url: str = "http://localhost:11434"
    # Gerekce metni yaratici degil, verilen gerceklere sadik olmali:
    # dusuk temperature + kisa cikti siniri (bkz. app/agent/llm.py).
    llm_temperature: float = 0.1
    llm_max_tokens: int = 220

    # Supabase / DB (used from later phases)
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    database_url: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
