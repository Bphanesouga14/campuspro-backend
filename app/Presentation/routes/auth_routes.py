#Routes d'authentification (login, profil, gestion des comptes)

# ============================================================
#  FICHIER : app/Presentation/routes/auth_routes.py
#
#  RÔLE : Endpoints HTTP pour l'authentification.
#
#  ROUTES DÉFINIES :
#  POST /auth/login          → Connexion (publique, retourne un JWT)
#  GET  /auth/moi             → Profil de l'utilisateur connecté
#  POST /auth/utilisateurs    → Créer un compte (admin uniquement)
#  GET  /auth/utilisateurs    → Lister les comptes (admin uniquement)
#
#  COUCHE : Présentation
# ============================================================

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.Application.use_cases.auth_use_cases import (
    ConnexionUseCase,
    CreerUtilisateurUseCase,
    ListerUtilisateursUseCase,
)
from app.Application.DTOs.schemas import (
    UtilisateurCreerDTO,
    UtilisateurReponseDTO,
    TokenReponseDTO,
)
from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur
from app.Domain.exceptions import (
    IdentifiantsInvalidesError,
    CompteDesactiveError,
    UtilisateurDejaExistantError,
)
from app.Presentation.security import get_current_user, require_roles
from app.Presentation.dependencies import (
    get_connexion_uc,
    get_creer_utilisateur_uc,
    get_lister_utilisateurs_uc,
    get_utilisateur_repo,
)

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post(
    "/login",
    response_model=TokenReponseDTO,
    summary="Se connecter",
    description="""
Authentifie un utilisateur et retourne un token JWT à utiliser dans le
header `Authorization: Bearer <token>` pour toutes les routes protégées.

**Note** : le champ `username` du formulaire correspond à l'**email**.
    """,
)
async def login(
    formulaire: OAuth2PasswordRequestForm = Depends(),
    use_case: ConnexionUseCase = Depends(get_connexion_uc),
):
    try:
        # OAuth2PasswordRequestForm impose les noms de champs "username"/"password" —
        # ici "username" est utilisé comme email.
        return await use_case.executer(formulaire.username, formulaire.password)
    except (IdentifiantsInvalidesError, CompteDesactiveError) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get(
    "/moi",
    response_model=UtilisateurReponseDTO,
    summary="Profil de l'utilisateur connecté",
)
async def mon_profil(
    utilisateur: UtilisateurDomaine = Depends(get_current_user),
):
    return UtilisateurReponseDTO(
        id_utilisateur = utilisateur.id_utilisateur,
        email          = utilisateur.email,
        nom            = utilisateur.nom,
        role           = utilisateur.role.value,
        actif          = utilisateur.actif,
    )


@router.post(
    "/utilisateurs",
    response_model=UtilisateurReponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte utilisateur (admin uniquement)",
)
async def creer_utilisateur(
    dto: UtilisateurCreerDTO,
    use_case: CreerUtilisateurUseCase = Depends(get_creer_utilisateur_uc),
    _admin: UtilisateurDomaine = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    try:
        return await use_case.executer(dto)
    except UtilisateurDejaExistantError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "/utilisateurs",
    response_model=List[UtilisateurReponseDTO],
    summary="Lister les comptes utilisateurs (admin uniquement)",
)
async def lister_utilisateurs(
    use_case: ListerUtilisateursUseCase = Depends(get_lister_utilisateurs_uc),
    _admin: UtilisateurDomaine = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    return await use_case.executer()


@router.put(
    "/utilisateurs/{id_utilisateur}",
    response_model=UtilisateurReponseDTO,
    summary="Modifier un compte utilisateur (admin uniquement)",
)
async def modifier_utilisateur(
    id_utilisateur: str,
    dto: UtilisateurCreerDTO,
    repo = Depends(get_utilisateur_repo),
    _admin: UtilisateurDomaine = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    from app.Infrastructure.repositories.utilisateur_repo import SQLAlchemyUtilisateurRepository
    from app.Infrastructure.security.mot_de_passe import hasher_mot_de_passe
    from app.Domain.value_objects import RoleUtilisateur as RoleEnum2

    utilisateur = await repo.trouver_par_id(id_utilisateur)
    if not utilisateur:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Utilisateur '{id_utilisateur}' introuvable.")

    utilisateur.email = dto.email
    utilisateur.nom   = dto.nom
    utilisateur.role  = RoleEnum2(dto.role)
    if hasattr(dto, "mot_de_passe") and dto.mot_de_passe:
        utilisateur.mot_de_passe_hash = hasher_mot_de_passe(dto.mot_de_passe)

    sauvegarde = await repo.sauvegarder(utilisateur)
    return UtilisateurReponseDTO(
        id_utilisateur = sauvegarde.id_utilisateur,
        email          = sauvegarde.email,
        nom            = sauvegarde.nom,
        role           = sauvegarde.role.value,
        actif          = sauvegarde.actif,
    )


@router.delete(
    "/utilisateurs/{id_utilisateur}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un compte utilisateur (admin uniquement)",
)
async def supprimer_utilisateur(
    id_utilisateur: str,
    repo = Depends(get_utilisateur_repo),
    utilisateur_connecte: UtilisateurDomaine = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    if id_utilisateur == utilisateur_connecte.id_utilisateur:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "Vous ne pouvez pas supprimer votre propre compte."
        )
    utilisateur = await repo.trouver_par_id(id_utilisateur)
    if not utilisateur:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Utilisateur '{id_utilisateur}' introuvable.")

    from sqlalchemy import delete as sql_delete
    from app.Infrastructure.database.models import Utilisateur as UtilisateurModele
    await repo._db.execute(sql_delete(UtilisateurModele).where(UtilisateurModele.id_utilisateur == id_utilisateur))
    await repo._db.flush()
