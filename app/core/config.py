from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Pas de valeur par défaut : DOIT être fourni via le fichier .env.
    # Ne JAMAIS coder un identifiant de base de données en dur dans le code source.
    DATABASE_URL: str  # Supabase (base principale)

    # PostgreSQL local (base de secours si Supabase est inaccessible).
    # Format : postgresql+asyncpg://user:password@localhost:5432/nom_base
    # Optionnel : si absent, seul Supabase est utilisé.
    LOCAL_DATABASE_URL: str = ""

    # Ordre de priorité : "supabase" (défaut) ou "local"
    DATABASE_PRIORITY: str = "supabase"

    APP_TITLE: str = "CampusPro — Gestion des étudiants, paiements & QR codes"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM: str = "" # Optionnel si tu l'utilises
    
    SMS_API_KEY: str = ""
    SMS_USERNAME: str = ""

    # ── Authentification JWT ─────────────────────────────────
    # JWT_SECRET_KEY : OBLIGATOIRE, doit être une chaîne longue et
    # aléatoire (ex: générée avec `python -c "import secrets; print(secrets.token_hex(32))"`).
    # Ne JAMAIS utiliser une valeur par défaut prévisible en production.
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 480  # 8 heures (une journée de travail)

       # ── Configuration Pydantic ───────────────────────────────
    # env_file=".env" → lit automatiquement le fichier .env
    # extra="ignore"  → ignore les variables inconnues dans .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
