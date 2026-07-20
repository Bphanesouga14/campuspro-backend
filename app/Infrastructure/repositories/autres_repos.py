

# ============================================================
#  FICHIER : app/infrastructure/repositories/autres_repos.py
#
#  RÔLE : Implémenter les repositories pour
#         Paiement, QRCode et Notification.
#
#  Même principe que etudiant_repo.py :
#  chaque méthode = une vraie requête SQL.
#
#  COUCHE : Infrastructure
# ============================================================

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.Infrastructure.database.models import (
    Paiement     as PaiementModele,
    QRCode       as QRCodeModele,
    Notification as NotificationModele,
    StatutPaiementEnum, StatutQREnum, StatutNotifEnum,
)
from app.Domain.interfaces import (
    IPaiementRepository,
    IQRCodeRepository,
    INotificationRepository,
)
from app.Domain.entities import PaiementDomaine, QRCodeDomaine, NotificationDomaine
from app.Infrastructure.database.mappers import (
    paiement_modele_vers_domaine,  paiement_domaine_vers_modele,
    qrcode_modele_vers_domaine,    qrcode_domaine_vers_modele,
    notification_modele_vers_domaine, notification_domaine_vers_modele,
)


# ============================================================
#  REPOSITORY : SQLAlchemyPaiementRepository
# ============================================================
class SQLAlchemyPaiementRepository(IPaiementRepository):
    """
    Implémentation concrète de IPaiementRepository.

    Gère les opérations SQL sur la table 'paiements'.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def sauvegarder(self, paiement: PaiementDomaine) -> PaiementDomaine:
        """
        Upsert d'un paiement.
        Si le paiement existe (même id_paiement) → UPDATE.
        Sinon → INSERT.
        """
        modele_existant = await self._db.get(PaiementModele, paiement.id_paiement)
        if modele_existant:
            modele = paiement_domaine_vers_modele(paiement, modele_existant)
        else:
            modele = paiement_domaine_vers_modele(paiement)
            self._db.add(modele)
        await self._db.flush()
        return paiement_modele_vers_domaine(modele)

    async def trouver_par_id(self, id_paiement: str) -> Optional[PaiementDomaine]:
        """
        SELECT * FROM paiements WHERE id_paiement = '...'
        Retourne None si non trouvé.
        """
        modele = await self._db.get(PaiementModele, id_paiement)
        return paiement_modele_vers_domaine(modele) if modele else None

    async def lister_par_etudiant(self, id_etudiant: str) -> List[PaiementDomaine]:
        """
        Retourne toutes les tranches d'un étudiant,
        triées par numéro de tranche (1, 2, 3).

        SQL généré :
        SELECT * FROM paiements
        WHERE id_etudiant = '...'
        ORDER BY numero_tranche ASC
        """
        stmt = (
            select(PaiementModele)
            .where(PaiementModele.id_etudiant == id_etudiant)
            # .order_by() = ORDER BY en SQL
            .order_by(PaiementModele.numero_tranche)
        )
        modeles = (await self._db.execute(stmt)).scalars().all()
        return [paiement_modele_vers_domaine(m) for m in modeles]

    async def lister_en_retard(self) -> List[PaiementDomaine]:
        """
        Retourne tous les paiements dont le statut est EN_RETARD.
        Trié par date limite (les plus urgents en premier).

        SQL généré :
        SELECT * FROM paiements
        WHERE statut = 'EN RETARD'
        ORDER BY date_limite ASC
        """
        stmt = (
            select(PaiementModele)
            .where(PaiementModele.statut == StatutPaiementEnum.EN_RETARD)
            .order_by(PaiementModele.date_limite)
        )
        modeles = (await self._db.execute(stmt)).scalars().all()
        return [paiement_modele_vers_domaine(m) for m in modeles]

    async def sauvegarder_tous(
        self,
        paiements: List[PaiementDomaine],
    ) -> List[PaiementDomaine]:
        """
        Sauvegarde une liste de paiements en une seule transaction.
        Utilisé lors de l'import Excel.
        """
        return [await self.sauvegarder(p) for p in paiements]


# ============================================================
#  REPOSITORY : SQLAlchemyQRCodeRepository
# ============================================================
class SQLAlchemyQRCodeRepository(IQRCodeRepository):
    """
    Implémentation concrète de IQRCodeRepository.
    Gère les opérations SQL sur la table 'qr_codes'.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def sauvegarder(self, qr_code: QRCodeDomaine) -> QRCodeDomaine:
        """Upsert d'un QR code."""
        modele_existant = await self._db.get(QRCodeModele, qr_code.id_qrcode)
        if modele_existant:
            modele = qrcode_domaine_vers_modele(qr_code, modele_existant)
        else:
            modele = qrcode_domaine_vers_modele(qr_code)
            self._db.add(modele)
        await self._db.flush()
        return qrcode_modele_vers_domaine(modele)

    async def trouver_actif_par_etudiant(
        self,
        id_etudiant: str,
    ) -> Optional[QRCodeDomaine]:
        """
        Cherche le QR code ACTIF d'un étudiant.
        Un étudiant ne peut avoir qu'un seul QR actif à la fois.

        SQL généré :
        SELECT * FROM qr_codes
        WHERE id_etudiant = '...'
        AND statut = 'ACTIF'
        LIMIT 1
        """
        stmt = (
            select(QRCodeModele)
            .where(and_(
                QRCodeModele.id_etudiant == id_etudiant,
                QRCodeModele.statut      == StatutQREnum.ACTIF,
            ))
            # .limit(1) → on ne veut qu'un seul résultat
            .limit(1)
        )
        modele = (await self._db.execute(stmt)).scalar_one_or_none()
        return qrcode_modele_vers_domaine(modele) if modele else None

    async def trouver_dernier_par_etudiant(
        self,
        id_etudiant: str,
    ) -> Optional[QRCodeDomaine]:
        """
        Cherche le dernier QR code d'un étudiant, quel que soit
        son statut (ACTIF, SUSPENDU, EXPIRÉ).

        Utilisé pour l'affichage administratif du QR code,
        contrairement à trouver_actif_par_etudiant() qui est
        utilisé lors du scan (contrôle de solvabilité).
        """
        from sqlalchemy import select
        from app.Infrastructure.database.models import QRCode as QRCodeModele

        res = await self._db.execute(
            select(QRCodeModele)
            .where(QRCodeModele.id_etudiant == id_etudiant)
            .order_by(QRCodeModele.date_generation.desc())
            .limit(1)
        )
        modele = res.scalar_one_or_none()
        if not modele:
            return None
        return qrcode_modele_vers_domaine(modele)

    async def lister_par_etudiant(self, id_etudiant: str) -> List[QRCodeDomaine]:
        """
        Retourne tout l'historique des QR codes d'un étudiant.
        Le plus récent en premier.

        SQL généré :
        SELECT * FROM qr_codes
        WHERE id_etudiant = '...'
        ORDER BY created_at DESC
        """
        stmt = (
            select(QRCodeModele)
            .where(QRCodeModele.id_etudiant == id_etudiant)
            # desc() = ORDER BY DESC (plus récent en premier)
            .order_by(QRCodeModele.created_at.desc())
        )
        modeles = (await self._db.execute(stmt)).scalars().all()
        return [qrcode_modele_vers_domaine(m) for m in modeles]


# ============================================================
#  REPOSITORY : SQLAlchemyNotificationRepository
# ============================================================
class SQLAlchemyNotificationRepository(INotificationRepository):
    """
    Implémentation concrète de INotificationRepository.
    Gère les opérations SQL sur la table 'notifications'.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def sauvegarder(self, notification: NotificationDomaine) -> NotificationDomaine:
        """Upsert d'une notification."""
        modele_existant = await self._db.get(
            NotificationModele,
            notification.id_notification
        )
        if modele_existant:
            modele = notification_domaine_vers_modele(notification, modele_existant)
        else:
            modele = notification_domaine_vers_modele(notification)
            self._db.add(modele)
        await self._db.flush()
        return notification_modele_vers_domaine(modele)

    async def lister_par_etudiant(self, id_etudiant: str) -> List[NotificationDomaine]:
        """
        Retourne tout l'historique des notifications pour un étudiant.
        Les plus récentes en premier.
        """
        stmt = (
            select(NotificationModele)
            .where(NotificationModele.id_etudiant == id_etudiant)
            .order_by(NotificationModele.created_at.desc())
        )
        modeles = (await self._db.execute(stmt)).scalars().all()
        return [notification_modele_vers_domaine(m) for m in modeles]

    async def lister_non_envoyees(self) -> List[NotificationDomaine]:
        """
        Retourne les notifications en attente d'envoi.
        Utilisé par un job planifié pour les renvoyer.

        SQL généré :
        SELECT * FROM notifications
        WHERE statut_envoi = 'EN ATTENTE'
        ORDER BY created_at ASC
        """
        stmt = (
            select(NotificationModele)
            .where(NotificationModele.statut_envoi == StatutNotifEnum.EN_ATTENTE)
            # Les plus anciennes en premier (priorité aux plus vieilles)
            .order_by(NotificationModele.created_at)
        )
        modeles = (await self._db.execute(stmt)).scalars().all()
        return [notification_modele_vers_domaine(m) for m in modeles]
