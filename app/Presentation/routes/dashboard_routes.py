#Route pour le tableau de bord (statistiques globales)

# ============================================================
#  FICHIER : app/Presentation/routes/dashboard_routes.py
#
#  RÔLE : Endpoint HTTP pour le tableau de bord de la direction.
#
#  COUCHE : Présentation
# ============================================================


from sqlalchemy.ext.asyncio import AsyncSession
from app.Infrastructure.database.session import get_db
from app.Presentation.security import get_current_user
from app.Domain.entities import UtilisateurDomaine



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







@router.get("/analytique", summary="Données analytiques pour les graphiques")

async def dashboard_analytique(
    _: UtilisateurDomaine = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les données nécessaires pour les graphiques du tableau de bord :
    - Paiements par spécialité
    - Répartition des statuts
    - Évolution mensuelle des paiements
    """
    from sqlalchemy import select, func
    from app.Infrastructure.database.models import (
        Paiement, Specialite, StatutPaiementEnum
    )

    # ── 1. Paiements par spécialité ───────────────────────────
    res = await db.execute(
        select(
            Paiement.id_specialite,
            func.sum(Paiement.montant_attendu).label("attendu"),
            func.sum(Paiement.montant_paye).label("verse"),
            func.count(Paiement.id_paiement).label("nb"),
        ).group_by(Paiement.id_specialite)
    )
    par_specialite = [
        {
            "specialite": row.id_specialite,
            "attendu":    int(row.attendu or 0),
            "verse":      int(row.verse or 0),
            "reste":      int((row.attendu or 0) - (row.verse or 0)),
        }
        for row in res.all()
    ]

    # ── 2. Répartition des statuts ────────────────────────────
    res2 = await db.execute(
        select(
            Paiement.statut,
            func.count(Paiement.id_paiement).label("nb"),
            func.sum(Paiement.montant_paye).label("total"),
        ).group_by(Paiement.statut)
    )
    statuts = [
        {
            "statut": row.statut.value if hasattr(row.statut,"value") else str(row.statut),
            "nb":     int(row.nb or 0),
            "total":  int(row.total or 0),
        }
        for row in res2.all()
    ]

    # ── 3. Évolution mensuelle ────────────────────────────────
    # Grouper par date_paiement (format JJ/MM/AAAA → extraire MM/AAAA)
    res3 = await db.execute(
        select(
            Paiement.date_paiement,
            func.sum(Paiement.montant_paye).label("total"),
            func.count(Paiement.id_paiement).label("nb"),
        )
        .where(Paiement.date_paiement != None)
        .where(Paiement.montant_paye > 0)
        .group_by(Paiement.date_paiement)
        .order_by(Paiement.date_paiement)
    )

    # Regrouper par mois
    mois_map = {}
    for row in res3.all():
        if not row.date_paiement:
            continue
        date_str = str(row.date_paiement)
        # Format JJ/MM/AAAA
        if "/" in date_str and len(date_str) >= 7:
            parts = date_str.split("/")
            if len(parts) >= 3:
                mois = f"{parts[1]}/{parts[2][:4]}"
            else:
                continue
        else:
            continue
        if mois not in mois_map:
            mois_map[mois] = {"mois": mois, "total": 0, "nb": 0}
        mois_map[mois]["total"] += int(row.total or 0)
        mois_map[mois]["nb"]    += int(row.nb or 0)

    evolution = sorted(mois_map.values(), key=lambda x: x["mois"])

    return {
        "par_specialite": par_specialite,
        "statuts":        statuts,
        "evolution":      evolution,
    }
