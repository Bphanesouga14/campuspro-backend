#Routes pour le calendrier académique des niveaux

# ============================================================
#  FICHIER : app/Presentation/routes/calendrier_routes.py
#
#  RÔLE : Endpoint HTTP pour consulter le calendrier académique
#         (dates de démarrage et limites de tranches par niveau).
#
#  COUCHE : Présentation
# ============================================================

from typing import List

from fastapi import APIRouter, Depends

from app.Application.DTOs.schemas import CalendrierNiveauDTO
from app.Infrastructure.repositories.calendrier_repo import SQLAlchemyCalendrierRepository
from app.Presentation.dependencies import get_calendrier_repo
from app.Presentation.security import get_current_user
from app.Domain.entities import UtilisateurDomaine

router = APIRouter(prefix="/calendrier", tags=["Calendrier académique"])


@router.get(
    "",
    response_model=List[CalendrierNiveauDTO],
    summary="Calendrier académique par niveau",
    description="Retourne, pour chaque niveau (1 à 5), les dates de démarrage et les limites des 3 tranches.",
)
async def lister_calendrier(
    repo: SQLAlchemyCalendrierRepository = Depends(get_calendrier_repo),
    _utilisateur: UtilisateurDomaine = Depends(get_current_user),
):
    lignes = await repo.lister_tous()
    return [CalendrierNiveauDTO.model_validate(l) for l in lignes]
