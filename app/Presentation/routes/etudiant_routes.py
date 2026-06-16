#Routes GET/POST pour les étudiants



#  RÔLE : Définir les endpoints HTTP pour les étudiants.
#
#  C'EST QUOI UNE ROUTE FASTAPI ?
#  C'est une fonction Python décorée avec @router.get() ou
#  @router.post() qui répond à une URL précise.
#
#  EXEMPLE SIMPLE :
#  @router.get("/etudiants")       → répond à GET /etudiants
#  @router.post("/etudiants")      → répond à POST /etudiants
#  @router.get("/etudiants/{id}")  → répond à GET /etudiants/ETU-001
#
#  UNE ROUTE NE FAIT QUE TROIS CHOSES :
#  1. Recevoir les données de la requête HTTP
#  2. Appeler le bon use case
#  3. Retourner le résultat en JSON
#
#  ELLE NE CONTIENT AUCUNE LOGIQUE MÉTIER.
#  Toute la logique est dans les use cases (couche Application).
#
#  COUCHE : Présentation
# ============================================================

from typing import List, Optional

# APIRouter = un groupe de routes (comme un "mini-application")
# Depends = pour l'injection de dépendances
# HTTPException = pour retourner des erreurs HTTP (404, 400...)
# Query = pour les paramètres d'URL (?niveau=1&annee=2024-2025)
# status = constantes HTTP (200, 201, 404...)
from fastapi import APIRouter, Depends, HTTPException, Query, status

# Les use cases qu'on va appeler
from app.Application.use_cases.etudiant_use_cases import (
    CreerEtudiantUseCase,
    TrouverEtudiantUseCase,
    ListerEtudiantsUseCase,
    HistoriquePaiementsEtudiantUseCase,
)

# Les DTOs — ce que l'API reçoit et retourne
from app.Application.DTOs.schemas import (
    EtudiantCreerDTO,
    EtudiantReponseDTO,
    EtudiantDetailDTO,
    HistoriquePaiementsDTO,
)

# Les exceptions du Domaine — pour les convertir en erreurs HTTP
from app.Domain.exceptions import (
    EtudiantDejaExistantError,
    EtudiantIntrouvableError,
)

# Les fonctions d'injection de dépendances
from app.Presentation.dependencies import (
    get_creer_etudiant_uc,
    get_trouver_etudiant_uc,
    get_lister_etudiants_uc,
    get_historique_paiements_uc,
)


# ── Créer le routeur ────────────────────────────────────────
# prefix="/etudiants" → toutes les routes commencent par /etudiants
# tags=["Étudiants"]  → groupe dans la documentation Swagger
router = APIRouter(prefix="/etudiants", tags=["Étudiants"])


# ============================================================
#  ROUTE 1 : Lister les étudiants
#  GET /api/v1/etudiants
#  GET /api/v1/etudiants?niveau=1
#  GET /api/v1/etudiants?niveau=1&annee=2024-2025
# ============================================================
@router.get(
    "",
    response_model=List[EtudiantReponseDTO],
    # response_model indique à FastAPI le format de la réponse JSON.
    # FastAPI valide automatiquement que le retour correspond au schéma.
    summary="Lister les étudiants",
    description="""
Retourne la liste de tous les étudiants.

**Filtres optionnels :**
- `niveau` : filtrer par niveau (1 à 5)
- `id_specialite` : filtrer par spécialité
- `annee` : filtrer par année académique (ex: 2024-2025)
    """,
)
async def lister_etudiants(
    # Query() définit un paramètre d'URL optionnel
    # None = valeur par défaut si non fourni
    # ge=1, le=5 = validation automatique (entre 1 et 5)
    niveau: Optional[int] = Query(
        None,
        ge=1, le=5,
        description="Niveau de 1 à 5"
    ),
    id_specialite: Optional[str] = Query(
        None,
        description="Identifiant de la spécialité (ex: SP-001)"
    ),
    annee: Optional[str] = Query(
        None,
        description="Année académique (ex: 2024-2025)"
    ),
    # Le use case est injecté automatiquement par FastAPI
    use_case: ListerEtudiantsUseCase = Depends(get_lister_etudiants_uc),
):
    """
    La route ne fait que trois choses :
    1. Recevoir les filtres depuis l'URL
    2. Appeler le use case
    3. Retourner le résultat

    Pas de logique métier ici.
    """
    return await use_case.executer(
        niveau           = niveau,
        id_specialite    = id_specialite,
        annee_academique = annee,
    )


# ============================================================
#  ROUTE 2 : Créer un étudiant
#  POST /api/v1/etudiants
# ============================================================
@router.post(
    "",
    response_model=EtudiantReponseDTO,
    # status_code=201 → HTTP 201 Created (au lieu de 200 OK)
    # C'est la convention REST : on retourne 201 quand on crée une ressource
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouvel étudiant",
)
async def creer_etudiant(
    # Le corps de la requête HTTP (JSON envoyé par le client)
    # FastAPI valide automatiquement que le JSON correspond à EtudiantCreerDTO
    # Si un champ est manquant ou de mauvais type → erreur 422 automatique
    dto: EtudiantCreerDTO,
    use_case: CreerEtudiantUseCase = Depends(get_creer_etudiant_uc),
):
    try:
        return await use_case.executer(dto)

    except EtudiantDejaExistantError as e:
        # L'exception métier du Domaine → on la convertit en erreur HTTP 409
        # HTTP 409 Conflict = la ressource existe déjà
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = str(e),
        )
    except ValueError as e:
        # Erreur de validation des Value Objects (Matricule, Email...)
        # HTTP 422 Unprocessable Entity = données invalides
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail      = str(e),
        )


# ============================================================
#  ROUTE 3 : Détail d'un étudiant
#  GET /api/v1/etudiants/ETU-2024-001
# ============================================================
@router.get(
    "/{id_etudiant}",
    # {id_etudiant} dans l'URL → FastAPI le passe comme paramètre
    response_model=EtudiantDetailDTO,
    summary="Détail complet d'un étudiant",
    description="Retourne l'étudiant avec ses paiements et QR codes.",
)
async def obtenir_etudiant(
    # id_etudiant est extrait automatiquement depuis l'URL
    id_etudiant: str,
    use_case: TrouverEtudiantUseCase = Depends(get_trouver_etudiant_uc),
):
    try:
        return await use_case.executer(id_etudiant)

    except EtudiantIntrouvableError as e:
        # HTTP 404 Not Found = la ressource n'existe pas
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(e),
        )


# ============================================================
#  ROUTE 4 : Historique des paiements d'un étudiant
#  GET /api/v1/etudiants/ETU-2024-001/paiements
# ============================================================
@router.get(
    "/{id_etudiant}/paiements",
    response_model=HistoriquePaiementsDTO,
    summary="Historique financier d'un étudiant",
    description="""
Retourne le résumé financier complet :
- Cumul versé toutes tranches confondues
- Total annuel attendu
- Reste global à payer
- Détail tranche par tranche avec statuts
    """,
)
async def historique_paiements(
    id_etudiant: str,
    use_case: HistoriquePaiementsEtudiantUseCase = Depends(
        get_historique_paiements_uc
    ),
):
    try:
        return await use_case.executer(id_etudiant)

    except EtudiantIntrouvableError as e:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(e),
        )
