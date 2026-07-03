"""
Service de relances automatiques par email.
S'exécute automatiquement chaque soir à 20h00.
Envoie un email aux parents des étudiants en retard de paiement.
"""
import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.database.models import (
    Paiement, Etudiant, Notification,
    StatutPaiementEnum, TypeNotifEnum
)
from app.core.config import settings


async def envoyer_relances(db: AsyncSession) -> dict:
    """
    Vérifie les paiements en retard et envoie les emails.
    Retourne un résumé des relances envoyées.
    """
    from app.Infrastructure.services.qr_notification_services import (
        NotificationServiceImpl
    )

    service = NotificationServiceImpl()
    aujourd_hui = datetime.now().strftime("%d/%m/%Y")
    nb_envoyes  = 0
    nb_erreurs  = 0
    details     = []

    # Récupérer tous les paiements EN RETARD ou EN_ATTENTE dépassés
    res = await db.execute(
        select(Paiement, Etudiant)
        .join(Etudiant, Paiement.id_etudiant == Etudiant.id_etudiant)
        .where(
            Paiement.statut.in_([
                StatutPaiementEnum.EN_RETARD,
                StatutPaiementEnum.EN_ATTENTE,
                StatutPaiementEnum.PARTIEL,
            ])
        )
        .where(Paiement.montant_paye < Paiement.montant_attendu)
    )
    rows = res.all()

    print(f"\n[RELANCES] {aujourd_hui} — {len(rows)} paiement(s) à relancer")

    for paiement, etudiant in rows:
        # Vérifier si une relance a déjà été envoyée aujourd'hui
        res_notif = await db.execute(
            select(Notification).where(
                Notification.id_etudiant   == etudiant.id_etudiant,
                Notification.type_notification == TypeNotifEnum.RAPPEL,
                Notification.date_envoi    == aujourd_hui,
            )
        )
        deja_envoye = res_notif.scalar_one_or_none()
        if deja_envoye:
            continue  # Pas de doublon

        # Construire le message
        reste       = paiement.montant_attendu - paiement.montant_paye
        nom_complet = f"{etudiant.prenom} {etudiant.nom}"
        message     = (
            f"Bonjour {etudiant.prenom_parent} {etudiant.nom_parent},\n\n"
            f"Nous vous contactons au sujet de votre enfant "
            f"{nom_complet} (matricule : {etudiant.matricule}).\n\n"
            f"La tranche {paiement.numero_tranche} de paiement est en retard :\n"
            f"  • Montant attendu  : {paiement.montant_attendu:,} FCFA\n"
            f"  • Montant versé    : {paiement.montant_paye:,} FCFA\n"
            f"  • Reste à payer    : {reste:,} FCFA\n"
            f"  • Date limite      : {paiement.date_limite}\n\n"
            f"Merci de régulariser cette situation au plus tôt "
            f"pour éviter toute suspension de scolarité.\n\n"
            f"Cordialement,\n"
            f"L'Administration — CampusPro"
        )

        # Envoyer l'email si disponible
        email_envoye = False
        if etudiant.email_parent:
            try:
                await asyncio.to_thread(
                    service._envoyer_email_sync,
                    etudiant.email_parent,
                    f"⚠ Rappel paiement — {nom_complet} — Tranche {paiement.numero_tranche}",
                    message,
                )
                email_envoye = True
            except Exception as ex:
                print(f"[RELANCES] Erreur email {etudiant.email_parent}: {ex}")
                nb_erreurs += 1

        # Enregistrer la notification en base
        notif = Notification(
            id_notification    = f"REL-{paiement.id_paiement}-{aujourd_hui.replace('/','')}" ,
            id_etudiant        = etudiant.id_etudiant,
            id_paiement        = paiement.id_paiement,
            type_notification  = TypeNotifEnum.RAPPEL,
            message            = message,
            canal              = "Email" if email_envoye else "Simulé",
            statut_envoi       = "ENVOYÉ" if email_envoye else "SIMULÉ",
            date_envoi         = aujourd_hui,
        )
        db.add(notif)

        nb_envoyes += 1
        details.append(f"{nom_complet} → {etudiant.email_parent or 'pas email'}")
        print(f"[RELANCES] ✅ {nom_complet} — T{paiement.numero_tranche} — {reste:,} FCFA")

    await db.commit()

    return {
        "date":       aujourd_hui,
        "total":      len(rows),
        "envoyes":    nb_envoyes,
        "erreurs":    nb_erreurs,
        "details":    details,
    }