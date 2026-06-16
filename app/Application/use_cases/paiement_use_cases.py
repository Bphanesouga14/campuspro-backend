#Enregistrer un paiement, lister retards

# ============================================================
#  FICHIER : app/application/use_cases/paiement_use_cases.py
#
#  RÔLE : Cas d'usage liés aux paiements.
#
#  C'est ici que se passe la logique la plus importante :
#  enregistrer un versement physique, mettre à jour le statut,
#  déclencher la génération du QR code et la notification parent.
#
#  COUCHE : Application
# ============================================================

import uuid                       # Pour générer des identifiants uniques
from decimal import Decimal
from typing import List

from app.Domain.entities import (
    PaiementDomaine,
    NotificationDomaine,
    QRCodeDomaine,
)
from app.Domain.value_objects import (
    Montant, StatutPaiement, StatutQRCode, TypeNotification
)
from app.Domain.interfaces import (
    IEtudiantRepository,
    IPaiementRepository,
    IQRCodeRepository,
    INotificationRepository,
    INotificationService,
    IQRCodeService,
)
from app.Domain.exceptions import (
    EtudiantIntrouvableError,
    PaiementIntrouvableError,
)
from app.Application.DTOs.schemas import (
    VersementDTO,
    PaiementReponseDTO,
    HistoriquePaiementsDTO,
    QRCodeReponseDTO,
)


# ── Fonction utilitaire ──────────────────────────────────────
def _paiement_vers_dto(p: PaiementDomaine) -> PaiementReponseDTO:
    """Convertit une entité PaiementDomaine en DTO de réponse."""
    return PaiementReponseDTO(
        id_paiement          = p.id_paiement,
        id_etudiant          = p.id_etudiant,
        id_specialite        = p.id_specialite,
        niveau               = p.niveau,
        numero_tranche       = p.numero_tranche,
        montant_attendu      = float(p.montant_attendu.valeur),
        montant_paye         = float(p.montant_paye.valeur),
        reste_a_payer        = float(p.reste_a_payer.valeur),
        date_paiement        = p.date_paiement,
        date_limite          = p.date_limite,
        statut               = p.statut.value,
        qr_code_genere       = p.qr_code_genere,
        notif_parent_envoyee = p.notif_envoyee,
        observations         = p.observations,
    )


# ============================================================
#  CAS D'USAGE 1 : EnregistrerVersementUseCase
# ============================================================
class EnregistrerVersementUseCase:
    """
    Enregistre un paiement physique reçu à la caisse.

    C'est le use case le plus important du système.
    Il orchestre 5 actions dans l'ordre :
    1. Charger le paiement et l'étudiant
    2. Appliquer les règles métier (via l'entité Domaine)
    3. Sauvegarder le paiement mis à jour
    4. Générer le QR code si tranche 1 soldée
    5. Envoyer la notification au parent
    """

    def __init__(
        self,
        etudiant_repo:     IEtudiantRepository,
        paiement_repo:     IPaiementRepository,
        qr_repo:           IQRCodeRepository,
        notif_repo:        INotificationRepository,
        notif_service:     INotificationService,   # Service d'envoi Email/SMS
        qr_service:        IQRCodeService,          # Service de génération QR
    ):
        self._etudiant_repo = etudiant_repo
        self._paiement_repo = paiement_repo
        self._qr_repo       = qr_repo
        self._notif_repo    = notif_repo
        self._notif_service = notif_service
        self._qr_service    = qr_service

    async def executer(
        self,
        id_paiement: str,
        dto: VersementDTO,
    ) -> PaiementReponseDTO:

        # ── Étape 1a : Charger le paiement ──────────────────
        paiement = await self._paiement_repo.trouver_par_id(id_paiement)
        if not paiement:
            raise PaiementIntrouvableError(id_paiement)

        # ── Étape 1b : Charger l'étudiant ───────────────────
        etudiant = await self._etudiant_repo.trouver_par_id(paiement.id_etudiant)
        if not etudiant:
            raise EtudiantIntrouvableError(paiement.id_etudiant)

        # ── Étape 2 : Appliquer les règles métier ───────────
        # On demande à l'entité Domaine de valider et enregistrer le versement.
        # C'est l'entité qui contient les règles, PAS le use case.
        # Si le montant dépasse ce qui est attendu → PaiementExcessifError
        # Si déjà soldée → PaiementDejaEffectueError
        montant_verse = Montant(dto.montant)
        paiement.enregistrer_versement(montant_verse, dto.date_paiement)

        if dto.observations:
            paiement.observations = dto.observations

        # ── Étape 3 : Sauvegarder le paiement ───────────────
        paiement_sauvegarde = await self._paiement_repo.sauvegarder(paiement)

        # ── Étape 4 : Générer le QR code si nécessaire ──────
        # peut_generer_qr() vérifie : tranche 1 ET statut PAYÉ
        if paiement_sauvegarde.peut_generer_qr():

            # Construire les données à encoder dans le QR
            donnees_qr = {
                "id_etudiant":   etudiant.id_etudiant,
                "matricule":     str(etudiant.matricule),
                "nom_complet":   etudiant.nom_complet,
                "id_specialite": paiement_sauvegarde.id_specialite,
                "niveau":        paiement_sauvegarde.niveau,
                "annee":         etudiant.annee_academique,
                "valide_jusqua": paiement_sauvegarde.date_limite,
            }

            # Demander au service Infrastructure de générer l'image QR
            qr_data_str = await self._qr_service.generer(
                donnees    = donnees_qr,
                id_etudiant= etudiant.id_etudiant,
            )

            # Créer l'entité QRCodeDomaine
            # uuid.uuid4() génère un identifiant unique aléatoire
            qr_id = f"QR-{etudiant.id_etudiant}-{str(uuid.uuid4())[:8].upper()}"
            qr_code = QRCodeDomaine(
                id_qrcode       = qr_id,
                id_etudiant     = etudiant.id_etudiant,
                id_paiement     = paiement_sauvegarde.id_paiement,
                id_specialite   = paiement_sauvegarde.id_specialite,
                niveau          = paiement_sauvegarde.niveau,
                date_generation = dto.date_paiement,
                valide_jusqua   = paiement_sauvegarde.date_limite,
                statut          = StatutQRCode.ACTIF,
                qr_data         = qr_data_str,
            )

            # Marquer l'entité domaine (vérifie les règles)
            paiement_sauvegarde.marquer_qr_genere()

            # Sauvegarder le QR code en base
            await self._qr_repo.sauvegarder(qr_code)

            # Resauvegarder le paiement avec qr_code_genere=True
            paiement_sauvegarde = await self._paiement_repo.sauvegarder(
                paiement_sauvegarde
            )

        # ── Étape 5 : Notifier le parent ─────────────────────
        await self._notifier_parent(etudiant, paiement_sauvegarde, dto)

        return _paiement_vers_dto(paiement_sauvegarde)

    async def _notifier_parent(self, etudiant, paiement, dto) -> None:
        """
        Méthode privée (préfixe _) : construit et envoie la notification.
        Séparée pour que executer() reste lisible.
        """

        # Déterminer le type de notification selon le statut
        if paiement.statut == StatutPaiement.PAYE:
            type_notif = TypeNotification.CONFIRMATION
        else:
            type_notif = TypeNotification.PARTIEL

        # Construire le message (méthode statique du Domaine)
        message = NotificationDomaine.construire_message(
            nom_etudiant    = etudiant.nom_complet,
            numero_tranche  = paiement.numero_tranche,
            montant_paye    = paiement.montant_paye,
            montant_attendu = paiement.montant_attendu,
            date_paiement   = dto.date_paiement,
        )

        # Créer l'entité notification
        notif_id = f"NOTIF-{str(uuid.uuid4())[:8].upper()}"
        notification = NotificationDomaine(
            id_notification   = notif_id,
            id_paiement       = paiement.id_paiement,
            id_etudiant       = etudiant.id_etudiant,
            nom_parent        = etudiant.nom_parent,
            contact_parent    = str(etudiant.telephone_parent) if etudiant.telephone_parent else "",
            type_notification = type_notif,
            message           = message,
            canal             = "Email+SMS",
            statut_envoi      = "EN ATTENTE",
        )

        # Sauvegarder la notification en base (historique)
        await self._notif_repo.sauvegarder(notification)

        # Tenter l'envoi réel
        envoi_ok = False
        try:
            # Envoi SMS si téléphone disponible
            if etudiant.telephone_parent:
                envoi_ok = await self._notif_service.envoyer_sms(
                    numero  = str(etudiant.telephone_parent),
                    message = message,
                )
            # Envoi Email si email disponible
            if etudiant.email_parent:
                await self._notif_service.envoyer_email(
                    destinataire = str(etudiant.email_parent),
                    sujet        = f"Paiement reçu — {etudiant.nom_complet}",
                    message      = message,
                )
                envoi_ok = True
        except Exception:
            # On ne bloque pas le paiement si la notification échoue.
            # L'erreur est silencieuse ici : le statut reste "EN ATTENTE"
            # et un job planifié retentera plus tard.
            pass

        # Mettre à jour le statut de la notification
        if envoi_ok:
            notification.statut_envoi = "ENVOYÉ"
            notification.date_envoi   = dto.date_paiement
            paiement.notif_envoyee    = True
            await self._notif_repo.sauvegarder(notification)
            await self._paiement_repo.sauvegarder(paiement)


# ============================================================
#  CAS D'USAGE 2 : ListerPaiementsEnRetardUseCase
# ============================================================
class ListerPaiementsEnRetardUseCase:
    """
    Liste tous les paiements en retard, toutes spécialités confondues.

    SCÉNARIO :
    Chaque matin, la direction consulte la liste des retards
    pour décider quelles relances envoyer aux parents.
    """

    def __init__(self, paiement_repo: IPaiementRepository):
        self._paiement_repo = paiement_repo

    async def executer(self) -> List[PaiementReponseDTO]:
        paiements = await self._paiement_repo.lister_en_retard()
        # On traduit chaque PaiementDomaine en DTO
        return [_paiement_vers_dto(p) for p in paiements]


# ============================================================
#  CAS D'USAGE 3 : ObtenirQRCodeEtudiantUseCase
# ============================================================
class ObtenirQRCodeEtudiantUseCase:
    """
    Récupère le QR code actif d'un étudiant.

    SCÉNARIO :
    Le vigile à l'entrée scanne le QR code de l'étudiant
    → le système vérifie qu'il est actif et valide.
    """

    def __init__(
        self,
        etudiant_repo: IEtudiantRepository,
        qr_repo:       IQRCodeRepository,
    ):
        self._etudiant_repo = etudiant_repo
        self._qr_repo       = qr_repo

    async def executer(self, id_etudiant: str) -> QRCodeReponseDTO:

        # Vérifier que l'étudiant existe
        etudiant = await self._etudiant_repo.trouver_par_id(id_etudiant)
        if not etudiant:
            raise EtudiantIntrouvableError(id_etudiant)

        # Chercher son QR code actif
        from app.Domain.exceptions import QRCodeIntrouvableError
        qr = await self._qr_repo.trouver_actif_par_etudiant(id_etudiant)
        if not qr:
            raise QRCodeIntrouvableError(id_etudiant)

        return QRCodeReponseDTO(
            id_qrcode       = qr.id_qrcode,
            id_etudiant     = qr.id_etudiant,
            id_specialite   = qr.id_specialite,
            niveau          = qr.niveau,
            date_generation = qr.date_generation,
            valide_jusqua   = qr.valide_jusqua,
            statut          = qr.statut.value,
            est_valide      = qr.est_valide,
            qr_data         = qr.qr_data,
        )
