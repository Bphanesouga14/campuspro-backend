#Routes GET/POST pour les spécialités

# ============================================================
#  FICHIER : app/Presentation/routes/specialite_routes.py
#
#  RÔLE : Endpoints HTTP pour les spécialités/filières.
#
#  ROUTES DÉFINIES :
#  GET  /specialites           → Liste toutes les spécialités
#  GET  /specialites/{id}      → Détail d'une spécialité
#  POST /specialites           → Créer ou mettre à jour une spécialité
#
#  COUCHE : Présentation
# ============================================================

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.Application.use_cases.specialite_use_cases import (
    ListerSpecialitesUseCase,
    ObtenirSpecialiteUseCase,
    CreerOuModifierSpecialiteUseCase,
)
from app.Application.DTOs.schemas import SpecialiteCreerDTO, SpecialiteReponseDTO
from app.Domain.exceptions import SpecialiteIntrouvableError
from app.Presentation.dependencies import (
    get_lister_specialites_uc,
    get_obtenir_specialite_uc,
    get_creer_specialite_uc,
)
from app.Presentation.security import get_current_user, require_roles
from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur

router = APIRouter(prefix="/specialites", tags=["Spécialités"])


@router.get(
    "",
    response_model=List[SpecialiteReponseDTO],
    summary="Lister les spécialités",
    description="Retourne toutes les spécialités, avec filtre optionnel par niveau (1 à 5).",
)
async def lister_specialites(
    niveau: Optional[int] = Query(None, ge=1, le=5, description="Niveau de 1 à 5"),
    use_case: ListerSpecialitesUseCase = Depends(get_lister_specialites_uc),
    _utilisateur: UtilisateurDomaine = Depends(get_current_user),
):
    return await use_case.executer(niveau=niveau)


@router.get(
    "/{id_specialite}",
    response_model=SpecialiteReponseDTO,
    summary="Détail d'une spécialité",
)
async def obtenir_specialite(
    id_specialite: str,
    use_case: ObtenirSpecialiteUseCase = Depends(get_obtenir_specialite_uc),
    _utilisateur: UtilisateurDomaine = Depends(get_current_user),
):
    try:
        return await use_case.executer(id_specialite)
    except SpecialiteIntrouvableError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "",
    response_model=SpecialiteReponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Créer ou mettre à jour une spécialité",
    description="Si l'`id_specialite` existe déjà, la spécialité est mise à jour (upsert).",
)
async def creer_specialite(
    dto: SpecialiteCreerDTO,
    use_case: CreerOuModifierSpecialiteUseCase = Depends(get_creer_specialite_uc),
    _utilisateur: UtilisateurDomaine = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.SECRETAIRE)
    ),
):
    try:
        return await use_case.executer(dto)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
