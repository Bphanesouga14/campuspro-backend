#connexion PostgreSQL

# ============================================================
#  FICHIER : app/infrastructure/database/session.py
#
#  RÔLE : Gérer la connexion à PostgreSQL via Supabase.
#
#  DIFFÉRENCE AVEC L'ANCIENNE VERSION (Docker) :
#  Supabase impose une connexion SSL sécurisée.
#  On ajoute "ssl=require" dans les options du moteur.
#  Tout le reste est identique.
# ============================================================

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from app.Infrastructure.database.models import Base
from app.core.config import settings


# ── Moteur de connexion ──────────────────────────────────────
# connect_args={"ssl": "require"} → OBLIGATOIRE pour Supabase.
# Sans ça, Supabase refusera la connexion avec une erreur SSL.
#
# "ssl": "require" signifie :
# "Je veux absolument une connexion chiffrée (HTTPS pour les BDD)"
# C'est une sécurité : les données transitent de façon chiffrée
# entre votre serveur FastAPI et Supabase.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo         = settings.DEBUG,
    pool_pre_ping= True,
    pool_size    = 5,      # Réduit par rapport à Docker
    max_overflow = 10,     # Supabase gratuit a une limite de connexions
    connect_args = {"ssl": "require"},
    # ↑ LA LIGNE CLÉE pour Supabase
)

# ── Fabrique de sessions ─────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_          = AsyncSession,
    expire_on_commit= False,
)


# ── Générateur de session pour FastAPI ───────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Fournit une session à chaque requête HTTP.
    Commit si tout va bien, rollback si erreur.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Créer les tables au démarrage ───────────────────────────
async def create_tables():
    """
    Crée toutes les tables dans Supabase si elles n'existent pas.
    SQLAlchemy génère le SQL et l'envoie à Supabase.

    Vous verrez apparaître les tables dans :
    Supabase → Table Editor
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables créées dans Supabase.")
