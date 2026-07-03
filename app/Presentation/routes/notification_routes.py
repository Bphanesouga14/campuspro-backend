from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.Infrastructure.database.session import get_db
from app.Infrastructure.database.models import (
    Notification, Etudiant, TypeNotifEnum
)
from app.Presentation.security import get_current_user, require_roles
from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur

router = APIRouter(prefix="/notifications", tags=["Notifications"])




@router.post("/relances/lancer", summary="Lancer les relances manuellement (admin)")
async def lancer_relances_manuellement(
    utilisateur: UtilisateurDomaine = Depends(
        require_roles(RoleUtilisateur.ADMIN)
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Permet à l'admin de lancer les relances sans attendre 20h00.
    Utile pour tester ou en cas d'urgence.
    """
    from app.Infrastructure.services.relance_service import envoyer_relances
    resultat = await envoyer_relances(db)
    return {
        "message":  f"{resultat['envoyes']} relance(s) envoyée(s)",
        "details":  resultat,
    }





@router.get("/recentes")
async def notifications_recentes(
    utilisateur: UtilisateurDomaine = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les 15 dernières notifications selon le rôle :
    - ADMIN      → toutes les notifications
    - CAISSIER   → types CONFIRMATION PAIEMENT et PAIEMENT PARTIEL
    - SECRETAIRE → tous les autres types
    """
    stmt = (
        select(Notification, Etudiant.nom, Etudiant.prenom)
        .join(Etudiant, Notification.id_etudiant == Etudiant.id_etudiant)
        .order_by(desc(Notification.created_at))
        .limit(15)
    )

    # Filtrer par type selon le rôle
    if utilisateur.role == RoleUtilisateur.CAISSIER:
        stmt = stmt.where(
            Notification.type_notification.in_([
                TypeNotifEnum.CONFIRMATION,
                TypeNotifEnum.PARTIEL,
            ])
        )
    elif utilisateur.role == RoleUtilisateur.SECRETAIRE:
        stmt = stmt.where(
            Notification.type_notification == TypeNotifEnum.RAPPEL
        )
    # ADMIN → pas de filtre, voit tout

    result = await db.execute(stmt)
    rows   = result.all()

    return [
        {
            "id_notification": n.id_notification,
            "id_etudiant":     n.id_etudiant,
            "nom_etudiant":    f"{prenom} {nom}",
            "type":            n.type_notification.value if hasattr(n.type_notification, "value") else str(n.type_notification),
            "message":         n.message,
            "statut":          n.statut_envoi.value if hasattr(n.statut_envoi, "value") else str(n.statut_envoi),
            "canal":           n.canal,
            "date_envoi":      n.date_envoi,
            "created_at":      n.created_at.strftime("%d/%m/%Y %H:%M") if n.created_at else None,
        }
        for n, nom, prenom in rows
    ]
