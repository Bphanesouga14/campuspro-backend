from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def lire_racine():
    return {"Bienvenue": "Bienvenue sur mon API FastAPI!"}


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
from app.core.config import settings

# Création des tables au démarrage
from app.Infrastructure.database.session import create_tables

# Les routeurs de chaque domaine fonctionnel
from app.Presentation.routes.etudiant_routes import router as etudiant_router
from app.Presentation.routes.paiement_routes import router as paiement_router
from app.Presentation.routes.import_routes   import router as import_router


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
    print("🚀 Démarrage de LGS...")

    # Créer toutes les tables PostgreSQL si elles n'existent pas
    # Équivaut à : CREATE TABLE IF NOT EXISTS etudiants (...) etc.
    await create_tables()
    print("✅ Tables PostgreSQL prêtes.")

    # L'application tourne pendant ce yield
    yield

    # ── À l'arrêt ─────────────────────────────────────────
    # (rien à nettoyer ici — SQLAlchemy ferme les connexions seul)
    print("👋 Arrêt de LGS.")


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


# ============================================================
#  MIDDLEWARE CORS
# ============================================================
# CORS = Cross-Origin Resource Sharing.
# Sans ça, le navigateur bloque les requêtes venant
# d'un autre domaine (ex: front-end sur localhost:3000
# qui appelle l'API sur localhost:8000).
app.add_middleware(
    CORSMiddleware,
    # allow_origins = liste des domaines autorisés à appeler l'API
    allow_origins     = settings.ALLOWED_ORIGINS,
    # allow_credentials = autoriser les cookies et headers d'auth
    allow_credentials = True,
    # allow_methods = méthodes HTTP autorisées
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    # allow_headers = headers HTTP autorisés
    allow_headers     = ["*"],
)


# ============================================================
#  BRANCHEMENT DES ROUTEURS
# ============================================================
# prefix="/api/v1" → toutes les routes commencent par /api/v1
# Exemple : /api/v1/etudiants, /api/v1/paiements/retards

app.include_router(etudiant_router, prefix="/api/v1")
app.include_router(paiement_router, prefix="/api/v1")
app.include_router(import_router,   prefix="/api/v1")


# ============================================================
#  ROUTES UTILITAIRES
# ============================================================

@app.get("/", tags=["Santé"], summary="Accueil de l'API")
async def accueil():
    """
    Route racine — confirme que l'API est en ligne.
    Utile pour les health checks des serveurs de déploiement.
    """
    return {
        "application": settings.APP_TITLE,
        "version":     settings.APP_VERSION,
        "statut":      "en ligne ✅",
        "documentation": "/docs",
    }


@app.get("/health", tags=["Santé"], summary="Vérification de santé")
async def health_check():
    """
    Endpoint de health check.
    Les outils de monitoring (Docker, Kubernetes...) appellent
    cette route pour savoir si l'application fonctionne.
    Retourne 200 OK si tout va bien.
    """
    return {"statut": "ok"}
