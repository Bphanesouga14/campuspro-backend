#Route pour le tableau de bord (statistiques globales)

# ============================================================
#  FICHIER : app/Presentation/routes/dashboard_routes.py
#
#  RÔLE : Endpoint HTTP pour le tableau de bord de la direction.
#
#  COUCHE : Présentation
# ============================================================

from fastapi import APIRouter, Depends

from app.Application.use_cases.dashboard_use_case import TableauDeBordUseCase
from app.Application.DTOs.schemas import TableauDeBordDTO
from app.Presentation.dependencies import get_tableau_de_bord_uc
from app.Presentation.security import require_roles
from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur

router = APIRouter(prefix="/dashboard", tags=["Tableau de bord"])


@router.get(
    "",
    response_model=TableauDeBordDTO,
    summary="Statistiques globales de l'établissement",
    description="""
Vue d'ensemble pour la direction :
- Nombre total d'étudiants et de spécialités
- Montants attendus / versés / restants (toutes spécialités confondues)
- Taux de recouvrement global
- Nombre d'étudiants à jour vs en retard
    """,
)
async def tableau_de_bord(
    use_case: TableauDeBordUseCase = Depends(get_tableau_de_bord_uc),
    _utilisateur: UtilisateurDomaine = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.SECRETAIRE, RoleUtilisateur.CAISSIER)
    ),
):
    return await use_case.executer()
