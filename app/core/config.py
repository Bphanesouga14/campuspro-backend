from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:supabase14.Com@db.biftryazdcxzvcwnqfcw.supabase.co:5432/lgs_db"

    APP_TITLE: str = "Logiciel de Gestion Scolaire"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    
    SMS_API_KEY: str = ""
    SMS_USERNAME: str = ""

       # ── Configuration Pydantic ───────────────────────────────
    # env_file=".env" → lit automatiquement le fichier .env
    # extra="ignore"  → ignore les variables inconnues dans .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
