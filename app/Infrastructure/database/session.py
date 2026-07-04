# ============================================================
#  FICHIER : app/Infrastructure/database/session.py
#
#  RÔLE : Connexion PostgreSQL avec basculement automatique.
#
#  CORRECTIONS apportées :
#  - Timeout Supabase porté à 30 s (SQLAlchemy fait 2 requêtes
#    internes avant la nôtre : version() + current_schema())
#  - Création automatique de la base locale si elle est absente
#  - Détection précise de "base inexistante" via asyncpg
#  - Message d'erreur final clair avec solutions concrètes
# ============================================================

import asyncio
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from app.Infrastructure.database.models import Base
from app.core.config import settings

logger = logging.getLogger("lgs.database")

engine:            Optional[AsyncEngine]        = None
AsyncSessionLocal: Optional[async_sessionmaker] = None
source_active:     str                          = "non initialisée"


# ────────────────────────────────────────────────────────────
#  Création des moteurs
# ────────────────────────────────────────────────────────────

def _moteur_supabase() -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        echo          = settings.DEBUG,
        pool_pre_ping = True,
        pool_size     = 5,
        max_overflow  = 10,
        connect_args  = {"ssl": "require"},
    )


def _moteur_local(url: Optional[str] = None) -> AsyncEngine:
    return create_async_engine(
        url or settings.LOCAL_DATABASE_URL,
        echo          = settings.DEBUG,
        pool_pre_ping = True,
        pool_size     = 10,
        max_overflow  = 20,
    )


# ────────────────────────────────────────────────────────────
#  Test de connexion
# ────────────────────────────────────────────────────────────

async def _tester(moteur: AsyncEngine, nom: str, timeout_s: int) -> bool:
    """
    Ouvre une connexion réelle et exécute SELECT 1.

    POURQUOI 30 s pour Supabase ?
    SQLAlchemy effectue 2 requêtes d'initialisation AVANT la nôtre :
      1. SELECT pg_catalog.version()
      2. SELECT current_schema()
    Sur une connexion Supabase avec handshake SSL + réseau lent,
    ces 2 requêtes peuvent prendre 5-10 s à elles seules.
    30 s donne une marge confortable sans bloquer indéfiniment.
    """
    try:
        async with asyncio.timeout(timeout_s):
            async with moteur.connect() as conn:
                await conn.execute(text("SELECT 1"))
        print(f"   ✅ {nom} : connecté.")
        return True
    except asyncio.TimeoutError:
        print(f"   ⏱️  {nom} : pas de réponse après {timeout_s} s.")
        return False
    except Exception as e:
        msg = str(e)
        # "does not exist" = base PostgreSQL introuvable → on tente de la créer
        if "does not exist" in msg or "InvalidCatalogNameError" in type(e).__name__:
            print(f"   ⚠️  {nom} : la base de données n'existe pas encore.")
            return False
        print(f"   ❌ {nom} : {type(e).__name__} — {e}")
        return False


# ────────────────────────────────────────────────────────────
#  Création automatique de la base locale
# ────────────────────────────────────────────────────────────

async def _creer_base_locale() -> bool:
    """
    Se connecte à la base système 'postgres' et crée la base cible
    (ex: lgs_local) si elle n'existe pas encore.
    """
    url = settings.LOCAL_DATABASE_URL
    if not url:
        return False

    try:
        nom_base   = url.rstrip("/").rsplit("/", 1)[-1]
        url_sys    = url.rsplit("/", 1)[0] + "/postgres"
    except Exception:
        return False

    print(f"   🔧 Création automatique de la base '{nom_base}'...")

    moteur_sys = _moteur_local(url_sys)
    try:
        async with asyncio.timeout(10):
            async with moteur_sys.connect() as conn:
                await conn.execution_options(isolation_level="AUTOCOMMIT")
                existe = (await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :n"),
                    {"n": nom_base},
                )).fetchone()
                if existe:
                    print(f"   ℹ️  La base '{nom_base}' existe déjà.")
                else:
                    await conn.execute(text(f'CREATE DATABASE "{nom_base}"'))
                    print(f"   ✅ Base '{nom_base}' créée.")
        return True
    except asyncio.TimeoutError:
        print("   ⏱️  PostgreSQL local ne répond pas (timeout).")
        print("       → Vérifiez que le service PostgreSQL est démarré :")
        print("         Win+R → services.msc → postgresql-x64-XX → Démarrer")
        return False
    except Exception as e:
        print(f"   ❌ Impossible de créer la base : {type(e).__name__} — {e}")
        return False
    finally:
        await moteur_sys.dispose()


# ────────────────────────────────────────────────────────────
#  Initialisation principale (appelée au démarrage)
# ────────────────────────────────────────────────────────────

async def initialiser_base_de_donnees() -> None:
    global engine, AsyncSessionLocal, source_active

    priorite = getattr(settings, "DATABASE_PRIORITY", "supabase").lower()

    # (nom_affichage, fabrique_moteur, est_supabase, timeout_secondes)
    sources = []
    if priorite == "local":
        if settings.LOCAL_DATABASE_URL:
            sources.append(("PostgreSQL Local", _moteur_local,   False, 10))
        if settings.DATABASE_URL:
            sources.append(("Supabase",          _moteur_supabase, True, 30))
    else:
        if settings.DATABASE_URL:
            sources.append(("Supabase",          _moteur_supabase, True, 30))
        if settings.LOCAL_DATABASE_URL:
            sources.append(("PostgreSQL Local", _moteur_local,   False, 10))

    if not sources:
        raise RuntimeError(
            "❌ Aucune base configurée dans .env\n"
            "   Renseignez DATABASE_URL et/ou LOCAL_DATABASE_URL"
        )

    moteur_retenu: Optional[AsyncEngine] = None

    for nom, fabrique, est_supabase, timeout_s in sources:
        print(f"\n🔌 Tentative de connexion → {nom} ...")

        try:
            candidat = fabrique()
        except Exception as e:
            print(f"   ❌ Impossible de créer le moteur : {e}")
            continue

        ok = await _tester(candidat, nom, timeout_s)

        # Base locale absente → créer puis retenter
        if not ok and not est_supabase:
            creee = await _creer_base_locale()
            if creee:
                await candidat.dispose()
                candidat = fabrique()
                ok = await _tester(candidat, nom, timeout_s)

        if ok:
            moteur_retenu = candidat
            source_active = nom
            break

        await candidat.dispose()

    if moteur_retenu is None:
        msg_local = (
            "\n  → PostgreSQL local :"
            "\n      1. Win+R → tapez 'services.msc' → Entrée"
            "\n      2. Cherchez 'postgresql-x64-XX' → clic droit → Démarrer"
            "\n      3. Vérifiez LOCAL_DATABASE_URL dans votre .env"
        ) if settings.LOCAL_DATABASE_URL else ""

        raise RuntimeError(
            "❌ Aucune base de données accessible.\n"
            "\n  → Supabase :"
            "\n      - Vérifiez DATABASE_URL dans .env (mot de passe, nom du projet)"
            "\n      - Vérifiez votre connexion internet"
            f"{msg_local}"
        )

    engine = moteur_retenu
    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    print(f"\n{'='*52}")
    print(f"  ✅  Base active : {source_active}")
    print(f"{'='*52}\n")

    await create_tables()


# ────────────────────────────────────────────────────────────
#  Tables & Session
# ────────────────────────────────────────────────────────────

async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"✅ Tables vérifiées dans : {source_active}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocal is None:
        raise RuntimeError("Base de données non initialisée.")
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
