from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./gemini_notebook.db"

    # CORS
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # JWT — override SECRET_KEY in .env for production!
    secret_key: str = "dev-secret-change-me-in-production"

    # Gemini
    gemini_api_key: str = ""

    # Groq LLM
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
