#Injection de dépendances (crée les repos/use cases)


#
#  RÔLE : Construire et fournir les use cases aux routes
#         via l'injection de dépendances FastAPI.
#
#  ANALOGIE : Le gestionnaire du restaurant qui s'assure
#  que le chef (use case) a tous ses ingrédients (repositories)
#  avant que le serveur (route) prenne la commande.
#
#  FONCTIONNEMENT :
#  Route déclare :  use_case = Depends(get_creer_etudiant_use_case)
#  FastAPI appelle : get_creer_etudiant_use_case()
#                 → get_etudiant_repo()
#                 → get_db()  (ouvre la session PostgreSQL)
#  Tout est injecté automatiquement.
# ============================================================

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.Infrastructure.database.session import get_db
from app.Infrastructure.repositories.etudiant_repo import (
    SQLAlchemyEtudiantRepository, SQLAlchemySpecialiteRepository,
)
from app.Infrastructure.repositories.autres_repos import (
    SQLAlchemyPaiementRepository, SQLAlchemyQRCodeRepository,
    SQLAlchemyNotificationRepository,
)
from app.Infrastructure.services.qr_notification_services import (
    QRCodeServiceImpl, NotificationServiceImpl,
)
from app.Application.use_cases.etudiant_use_cases import (
    CreerEtudiantUseCase, TrouverEtudiantUseCase,
    ListerEtudiantsUseCase, HistoriquePaiementsEtudiantUseCase,
)
from app.Application.use_cases.paiement_use_cases import (
    EnregistrerVersementUseCase, ListerPaiementsEnRetardUseCase,
    ObtenirQRCodeEtudiantUseCase,
)
from app.Application.use_cases.import_use_cases import ImporterExcelUseCase


# ── Repositories ─────────────────────────────────────────────
# Chaque fonction reçoit la session et retourne un repository.
# FastAPI appelle ces fonctions automatiquement via Depends().

def get_etudiant_repo(db: AsyncSession = Depends(get_db)):
    return SQLAlchemyEtudiantRepository(db)

def get_specialite_repo(db: AsyncSession = Depends(get_db)):
    return SQLAlchemySpecialiteRepository(db)

def get_paiement_repo(db: AsyncSession = Depends(get_db)):
    return SQLAlchemyPaiementRepository(db)

def get_qr_repo(db: AsyncSession = Depends(get_db)):
    return SQLAlchemyQRCodeRepository(db)

def get_notif_repo(db: AsyncSession = Depends(get_db)):
    return SQLAlchemyNotificationRepository(db)


# ── Use Cases ────────────────────────────────────────────────
# Chaque fonction assemble le use case avec ses repositories.

def get_creer_etudiant_uc(
    repo: SQLAlchemyEtudiantRepository = Depends(get_etudiant_repo),
):
    return CreerEtudiantUseCase(repo)

def get_trouver_etudiant_uc(
    etudiant_repo = Depends(get_etudiant_repo),
    paiement_repo = Depends(get_paiement_repo),
    qr_repo       = Depends(get_qr_repo),
):
    return TrouverEtudiantUseCase(etudiant_repo, paiement_repo, qr_repo)

def get_lister_etudiants_uc(
    etudiant_repo = Depends(get_etudiant_repo),
    paiement_repo = Depends(get_paiement_repo),
):
    return ListerEtudiantsUseCase(etudiant_repo, paiement_repo)

def get_historique_paiements_uc(
    etudiant_repo = Depends(get_etudiant_repo),
    paiement_repo = Depends(get_paiement_repo),
):
    return HistoriquePaiementsEtudiantUseCase(etudiant_repo, paiement_repo)

def get_enregistrer_versement_uc(
    etudiant_repo = Depends(get_etudiant_repo),
    paiement_repo = Depends(get_paiement_repo),
    qr_repo       = Depends(get_qr_repo),
    notif_repo    = Depends(get_notif_repo),
):
    # Les services externes n'ont pas besoin de la session BDD
    return EnregistrerVersementUseCase(
        etudiant_repo = etudiant_repo,
        paiement_repo = paiement_repo,
        qr_repo       = qr_repo,
        notif_repo    = notif_repo,
        notif_service = NotificationServiceImpl(),
        qr_service    = QRCodeServiceImpl(),
    )

def get_lister_retards_uc(
    paiement_repo = Depends(get_paiement_repo),
):
    return ListerPaiementsEnRetardUseCase(paiement_repo)

def get_obtenir_qr_uc(
    etudiant_repo = Depends(get_etudiant_repo),
    qr_repo       = Depends(get_qr_repo),
):
    return ObtenirQRCodeEtudiantUseCase(etudiant_repo, qr_repo)

def get_importer_excel_uc(
    specialite_repo = Depends(get_specialite_repo),
    etudiant_repo   = Depends(get_etudiant_repo),
    paiement_repo   = Depends(get_paiement_repo),
    qr_repo         = Depends(get_qr_repo),
    notif_repo      = Depends(get_notif_repo),
):
    return ImporterExcelUseCase(
        specialite_repo = specialite_repo,
        etudiant_repo   = etudiant_repo,
        paiement_repo   = paiement_repo,
        qr_repo         = qr_repo,
        notif_repo      = notif_repo,
    )
