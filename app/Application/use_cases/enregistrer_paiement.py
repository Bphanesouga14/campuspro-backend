


#  RÔLE : Orchestrer l'enregistrement d'un versement physique.
#
#  C'EST LE CAS D'USAGE LE PLUS IMPORTANT DU PROJET.
#  Quand un parent paie à la caisse, voici ce qui se passe :
#
#  1. Trouver le paiement (la tranche concernée)
#  2. Trouver l'étudiant lié à ce paiement
#  3. Appliquer la règle métier (via l'entité Domaine)
#  4. Sauvegarder le paiement mis à jour
#  5. Si tranche 1 soldée → générer le QR code
#  6. Dans tous les cas → notifier le parent
#  7. Retourner le résultat
#
#  COUCHE : Application
# ============================================================

from decimal import Decimal

from app.Domain.entities      import PaiementDomaine, NotificationDomaine
from app.Domain.value_objects import Montant, TypeNotification
from app.Domain.interfaces    import (
    IPaiementRepository,
    IEtudiantRepository,
    IQRCodeRepository,
    INotificationRepository,
    IQRCodeService,
    INotificationService,
)
from app.Domain.exceptions import (
    PaiementIntrouvableError,
    EtudiantIntrouvableError,
)
from app.Application.DTOs.schemas import VersementIn, PaiementOut


class EnregistrerPaiementUseCase:
    """
    Cas d'usage : Enregistrer un versement physique reçu à la caisse.

    Ce cas d'usage reçoit BEAUCOUP de dépendances car il
    coordonne plusieurs actions (paiement + QR + notification).
    C'est normal pour un cas d'usage central.
    """

    def __init__(
        self,
        paiement_repo:     IPaiementRepository,
        etudiant_repo:     IEtudiantRepository,
        qr_repo:           IQRCodeRepository,
        notification_repo: INotificationRepository,
        qr_service:        IQRCodeService,
        notif_service:     INotificationService,
    ):
        self._paiement_repo     = paiement_repo
        self._etudiant_repo     = etudiant_repo
        self._qr_repo           = qr_repo
        self._notification_repo = notification_repo
        self._qr_service        = qr_service
        self._notif_service     = notif_service

    async def executer(
        self,
        id_paiement: str,
        versement:   VersementIn,
    ) -> PaiementOut:
        """
        Enregistre un versement pour une tranche donnée.

        Paramètres :
          id_paiement → l'identifiant de la tranche (ex: "PAY-001")
          versement   → le DTO contenant montant + date + observations
        """

        # ── Étape 1 : Trouver la tranche de paiement ─────────
        paiement = await self._paiement_repo.trouver_par_id(id_paiement)
        if not paiement:
            # Si la tranche n'existe pas → erreur métier claire
            raise PaiementIntrouvableError(id_paiement)

        # ── Étape 2 : Trouver l'étudiant ─────────────────────
        etudiant = await self._etudiant_repo.trouver_par_id(paiement.id_etudiant)
        if not etudiant:
            raise EtudiantIntrouvableError(paiement.id_etudiant)

        # ── Étape 3 : Appliquer la règle métier domaine ───────
        # On convertit le montant du DTO en Value Object Montant
        montant_verse = Montant(versement.montant)

        # C'est ICI que les règles du domaine s'appliquent :
        # - Pas de paiement négatif
        # - Tranche déjà soldée → erreur
        # - Dépassement du montant attendu → erreur
        # - Mise à jour du statut automatiquement
        paiement.enregistrer_versement(
            montant_verse = montant_verse,
            date          = versement.date_paiement,
        )

        # Ajouter les observations si précisées
        if versement.observations:
            paiement.observations = versement.observations

        # ── Étape 4 : Sauvegarder le paiement mis à jour ──────
        paiement_sauvegarde = await self._paiement_repo.sauvegarder(paiement)

        # ── Étape 5 : Générer le QR code si conditions remplies
        # La règle : QR uniquement si c'est la TRANCHE 1
        # et qu'elle est maintenant ENTIÈREMENT payée
        if paiement_sauvegarde.peut_generer_qr():
            await self._generer_qr_code(paiement_sauvegarde, etudiant.nom_complet)
            # Marquer dans le paiement que le QR a été généré
            paiement_sauvegarde.marquer_qr_genere()
            await self._paiement_repo.sauvegarder(paiement_sauvegarde)

        # ── Étape 6 : Notifier le parent ──────────────────────
        await self._notifier_parent(paiement_sauvegarde, etudiant)

        # ── Étape 7 : Retourner le DTO de sortie ──────────────
        return self._vers_dto(paiement_sauvegarde)

    async def _generer_qr_code(
        self,
        paiement:     PaiementDomaine,
        nom_etudiant: str,
    ) -> None:
        """
        Génère et sauvegarde le QR code de l'étudiant.
        Méthode privée (préfixe _) appelée en interne uniquement.
        """
        from app.Domain.entities    import QRCodeDomaine
        from app.Domain.value_objects import StatutQRCode
        import json

        # Les données encodées dans le QR (ce qu'on verra en le scannant)
        donnees_qr = {
            "id_etudiant":   paiement.id_etudiant,
            "nom":           nom_etudiant,
            "id_specialite": paiement.id_specialite,
            "niveau":        paiement.niveau,
            "tranche":       paiement.numero_tranche,
            "date_paiement": paiement.date_paiement,
            "valide_jusqua": paiement.date_limite,
        }

        # Appelle le service de génération (implémenté dans Infrastructure)
        qr_image = await self._qr_service.generer(
            donnees    = donnees_qr,
            id_etudiant = paiement.id_etudiant,
        )

        # Construire l'entité QRCode domaine
        qr_id = f"QR-{paiement.id_etudiant}-T1"
        qr_code = QRCodeDomaine(
            id_qrcode       = qr_id,
            id_etudiant     = paiement.id_etudiant,
            id_paiement     = paiement.id_paiement,
            id_specialite   = paiement.id_specialite,
            niveau          = paiement.niveau,
            date_generation = paiement.date_paiement,
            valide_jusqua   = paiement.date_limite,
            statut          = StatutQRCode.ACTIF,
            qr_data         = json.dumps(donnees_qr, ensure_ascii=False),
        )

        # Sauvegarder en base
        await self._qr_repo.sauvegarder(qr_code)

    async def _notifier_parent(
        self,
        paiement: PaiementDomaine,
        etudiant,                  # EtudiantDomaine
    ) -> None:
        """
        Construit et envoie la notification au parent.
        Méthode privée appelée après chaque paiement.
        """
        from datetime import datetime

        # Déterminer le type de notification selon le statut
        if paiement.statut.value == "PAYÉ":
            type_notif = TypeNotification.CONFIRMATION
        else:
            type_notif = TypeNotification.PARTIEL

        # Construire le texte du message (règle dans le domaine)
        message = NotificationDomaine.construire_message(
            nom_etudiant   = etudiant.nom_complet,
            numero_tranche = paiement.numero_tranche,
            montant_paye   = paiement.montant_paye,
            montant_attendu= paiement.montant_attendu,
            date_paiement  = paiement.date_paiement,
        )

        # Déterminer le canal : Email si disponible, sinon SMS
        contact_parent = ""
        canal          = ""
        if etudiant.email_parent:
            contact_parent = str(etudiant.email_parent)
            canal          = "Email"
        if etudiant.telephone_parent:
            contact_parent = str(etudiant.telephone_parent)
            canal          = "SMS" if canal == "" else "Email+SMS"

        # Générer un ID unique pour cette notification
        notif_id = f"NOTIF-{paiement.id_paiement}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Construire l'entité notification
        notification = NotificationDomaine(
            id_notification   = notif_id,
            id_paiement       = paiement.id_paiement,
            id_etudiant       = paiement.id_etudiant,
            nom_parent        = etudiant.nom_parent,
            contact_parent    = contact_parent,
            type_notification = type_notif,
            message           = message,
            canal             = canal,
            date_envoi        = paiement.date_paiement,
            statut_envoi      = "EN ATTENTE",
        )

        # Sauvegarder la notification en base
        notification_sauvee = await self._notification_repo.sauvegarder(notification)

        # Envoyer réellement via le service (Email et/ou SMS)
        succes = False
        if etudiant.email_parent:
            succes = await self._notif_service.envoyer_email(
                destinataire = str(etudiant.email_parent),
                sujet        = f"Paiement scolarité — {etudiant.nom_complet}",
                message      = message,
            )
        if etudiant.telephone_parent:
            succes = await self._notif_service.envoyer_sms(
                numero  = str(etudiant.telephone_parent),
                message = message,
            )

        # Mettre à jour le statut d'envoi
        notification_sauvee.statut_envoi = "ENVOYÉ" if succes else "ÉCHOUÉ"
        await self._notification_repo.sauvegarder(notification_sauvee)

    def _vers_dto(self, paiement: PaiementDomaine) -> PaiementOut:
        """Convertit l'entité domaine en DTO de sortie."""
        return PaiementOut(
            id_paiement     = paiement.id_paiement,
            id_etudiant     = paiement.id_etudiant,
            id_specialite   = paiement.id_specialite,
            niveau          = paiement.niveau,
            numero_tranche  = paiement.numero_tranche,
            montant_attendu = paiement.montant_attendu.valeur,
            montant_paye    = paiement.montant_paye.valeur,
            reste_a_payer   = paiement.reste_a_payer.valeur,
            date_paiement   = paiement.date_paiement,
            date_limite     = paiement.date_limite,
            statut          = paiement.statut.value,
            qr_code_genere  = paiement.qr_code_genere,
            notif_envoyee   = paiement.notif_envoyee,
            observations    = paiement.observations,
        )
