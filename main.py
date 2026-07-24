# ============================================================
#  FICHIER : main.py
#
#  RÔLE : Point d'entrée de l'application FastAPI.
#         C'est le fichier qu'on lance pour démarrer le serveur.
#
#  COMMANDE DE DÉMARRAGE :
#  uvicorn main:app --reload --host 0.0.0.0 --port 8000
#
#  QUE FAIT CE FICHIER ?
#  1. Crée l'application FastAPI
#  2. Configure le CORS (autorise le front-end à appeler l'API)
#  3. Branche tous les routeurs (routes étudiant, paiement, import)
#  4. Crée les tables en base au démarrage
#  5. Expose la documentation Swagger à /docs
#
#  COUCHE : Présentation (mais c'est aussi la racine du projet)
# ============================================================

# asynccontextmanager = pour gérer le cycle de vie de l'app
from contextlib import asynccontextmanager

from fastapi import FastAPI


from fastapi.middleware.cors import CORSMiddleware



# Configuration de l'application

from app.Infrastructure.database.models import Utilisateur
from app.core.config import settings

# Création des tables au démarrage
from app.Infrastructure.database.session import initialiser_base_de_donnees
import app.Infrastructure.database.session as db_session

# Gestionnaire d'erreurs global (404/409/400/500 propres)
from app.Presentation.error_handlers import enregistrer_handlers

# Les routeurs de chaque domaine fonctionnel
from app.Presentation.routes.etudiant_routes import router as etudiant_router
from app.Presentation.routes.paiement_routes import router as paiement_router
from app.Presentation.routes.import_routes   import router as import_router
from app.Presentation.routes.specialite_routes import router as specialite_router
from app.Presentation.routes.calendrier_routes import router as calendrier_router
from app.Presentation.routes.dashboard_routes import router as dashboard_router
from app.Presentation.routes.auth_routes import router as auth_router
from app.Presentation.routes.notification_routes import router as notification_router
from app.Presentation.routes.profil_routes import router as profil_router
from app.Presentation.routes.etudiant_photo_routes import router as photo_router
from app.Presentation.routes.presence_routes import router as presence_router
from app.Presentation.routes.qrcode_routes import router as qrcode_router


from app.Presentation.routes.auth_2fa_routes import router as auth_2fa_router

# Configurer le scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.Infrastructure.services.relance_service import envoyer_relances
from app.Infrastructure.database.session import AsyncSessionLocal


# ============================================================
#  LIFESPAN — Cycle de vie de l'application
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code exécuté au DÉMARRAGE et à l'ARRÊT de l'application.

    Structure :
        code avant yield → exécuté au démarrage
        yield            → l'application tourne ici
        code après yield → exécuté à l'arrêt

    C'est comme :
        ouvrir la boutique le matin
        travailler toute la journée
        fermer la boutique le soir
    """
    # ── Au démarrage ──────────────────────────────────────
    print("🚀 Démarrage de CampusPro...")

    # Connexion automatique à Supabase OU PostgreSQL local
    # selon disponibilité (voir app/Infrastructure/database/session.py)
    await initialiser_base_de_donnees()



    async def job_relances():
        """Tâche planifiée : envoyer les relances chaque soir."""
        print("\n⏰ Lancement des relances automatiques...")
        async with AsyncSessionLocal() as db:
            resultat = await envoyer_relances(db)
        print(f"✅ Relances terminées : {resultat['envoyes']} envoyées, {resultat['erreurs']} erreurs")

    scheduler = AsyncIOScheduler(timezone="Africa/Douala")
    scheduler.add_job(
        job_relances,
        CronTrigger(hour=20, minute=0),   # Chaque jour à 20h00
        id          = "relances_paiements",
        name        = "Relances paiements en retard",
        replace_existing = True,
    )
    scheduler.start()
    print("✅ Scheduler démarré — relances chaque jour à 20h00")

    yield

    # ── À l'arrêt ─────────────────────────────────────────
    scheduler.shutdown()
    if db_session.engine:
        await db_session.engine.dispose()
    print("👋 Arrêt de CampusPro.")


# ============================================================
#  CRÉATION DE L'APPLICATION FASTAPI
# ============================================================
app = FastAPI(
    title       = settings.APP_TITLE,
    version     = settings.APP_VERSION,
    description = """
## LGS - Logiciel de Gestion Scolaire

### Architecture
Ce projet suit la **Clean Architecture** avec 4 couches :
- **Domaine** : entités, value objects, règles métier pures
- **Application** : use cases, DTOs, orchestration
- **Infrastructure** : SQLAlchemy, PostgreSQL, QR code, Email/SMS
- **Présentation** : routes FastAPI (ce que vous utilisez ici)

### Fonctionnalités
| Fonctionnalité | Description |
|---|---|
| 📥 Import Excel | Upload du fichier LGS → insertion en base |
| 🎓 Étudiants | CRUD complet avec matricule et parent |
| 💰 Paiements | Suivi des 3 tranches, cumul versé, reste |
| 📱 QR Codes | Génération auto quand tranche 1 soldée |
| 🔔 Notifications | Email + SMS au parent à chaque paiement |

### Calendrier des niveaux
| Groupe | Niveaux | Démarrage |
|---|---|---|
| Groupe A | 1 et 2 | Octobre |
| Groupe B | 3 | Février |
| Groupe C | 4 et 5 | Avril |
    """,
    lifespan    = lifespan,    # Utilise notre fonction de cycle de vie
    docs_url    = "/docs",     # Swagger UI disponible à /docs
    redoc_url   = "/redoc",    # ReDoc disponible à /redoc
)


# Liste des origines autorisées à parler à ton API
origins = [
    "https://campuspro-front.bphanesouga.workers.dev",
    "http://localhost:5173", # Si tu testes aussi en local avec Vite
    "http://127.0.0.1:5173"
]



# ============================================================
#  MIDDLEWARE CORS
# ============================================================
# CORS = Cross-Origin Resource Sharing.
# Sans ça, le navigateur bloque les requêtes venant
# d'un autre domaine (ex: front-end sur localhost:3000
# qui appelle l'API sur localhost:8000).
app.add_middleware(
    CORSMiddleware,
    # En développement : on autorise toutes les origines pour éviter
    # les problèmes CORS. En production, remplacer "*" par la liste
    # des domaines autorisés.
 
 
 # ── CONFIGURATION CORS (OBLIGATOIRE POUR LE FRONT-END) ──

    #allow_origins=settings.ALLOWED_ORIGINS,  # Autorise les URLs définies dans config.py
    
    #modifié pour autoriser toutes les origines en développement
    allow_origins=["*"],  # En gros : autorise tout le monde
    allow_credentials=True,
    allow_methods=["*"],                     # Autorise toutes les méthodes (GET, POST, PUT, DELETE...)
    allow_headers=["*"],                     # Autorise tous les headers (Authorization, Content-Type...)
)


# ============================================================
#  GESTIONNAIRE D'ERREURS GLOBAL
# ============================================================
# Convertit toutes les exceptions métier du Domaine en réponses
# JSON HTTP propres (404, 409, 400...) + filet de sécurité 500.
enregistrer_handlers(app)


# ============================================================
#  BRANCHEMENT DES ROUTEURS
# ============================================================
# prefix="/api/v1" → toutes les routes commencent par /api/v1
# Exemple : /api/v1/etudiants, /api/v1/paiements/retards


app.include_router(auth_2fa_router, prefix="/api/v1")  # ← EN PREMIER
app.include_router(auth_router,     prefix="/api/v1")  # ← EN SECOND

app.include_router(etudiant_router, prefix="/api/v1")
app.include_router(paiement_router, prefix="/api/v1")
app.include_router(import_router,   prefix="/api/v1")
app.include_router(specialite_router, prefix="/api/v1")
app.include_router(calendrier_router, prefix="/api/v1")
app.include_router(dashboard_router,  prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")
app.include_router(profil_router,       prefix="/api/v1")
app.include_router(photo_router,        prefix="/api/v1")
app.include_router(presence_router,     prefix="/api/v1")
app.include_router(qrcode_router,       prefix="/api/v1")




# ============================================================
#  ROUTES UTILITAIRES
# ============================================================

@app.get("/", tags=["Santé"], summary="Accueil de l'API")
async def accueil():
    return {
        "application":   settings.APP_TITLE,
        "version":       settings.APP_VERSION,
        "statut":        "en ligne ✅",
        "base_active":   db_session.source_active,
        "documentation": "/docs",
    }


@app.get("/health", tags=["Santé"], summary="Vérification de santé")
async def health_check():
    return {
        "statut":      "ok",
        "base_active": db_session.source_active,
    }

