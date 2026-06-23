#Gestionnaire d'erreurs global

# ============================================================
#  FICHIER : app/presentation/error_handlers.py
#
#  RÔLE : Intercepter les exceptions et les transformer
#         en réponses HTTP claires avec le bon code d'erreur.
#
#  SANS CE FICHIER :
#  Si une exception est levée, FastAPI retourne une erreur 500
#  générique et peu lisible.
#
#  AVEC CE FICHIER :
#  Chaque exception métier est capturée et transformée
#  en réponse JSON structurée avec le bon code HTTP.
#
#  CODES HTTP UTILISÉS :
#  400 Bad Request  → Données invalides envoyées par l'utilisateur
#  404 Not Found    → Ressource introuvable (étudiant, paiement...)
#  409 Conflict     → Conflit (matricule déjà existant)
#  422 Unprocessable→ Données mal formatées (Pydantic)
#  500 Server Error → Erreur interne inattendue
#
#  COUCHE : Présentation
# ============================================================

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Les exceptions métier du Domaine
from app.Domain.exceptions import (
    DomaineError,
    EtudiantIntrouvableError,
    EtudiantDejaExistantError,
    EtudiantSuppressionImpossibleError,
    PaiementIntrouvableError,
    PaiementExcessifError,
    PaiementDejaEffectueError,
    QRCodeIntrouvableError,
    QRCodeNonAutoriseSError,
    SpecialiteIntrouvableError,
    FichierExcelInvalideError,
    ImportExcelError,
    MontantNegatifError,
    UtilisateurDejaExistantError,
    UtilisateurIntrouvableError,
    IdentifiantsInvalidesError,
    CompteDesactiveError,
)


def _reponse_erreur(status: int, code: str, message: str) -> JSONResponse:
    """
    Crée une réponse JSON d'erreur standardisée.

    Toutes les erreurs ont le même format :
    {
        "erreur": {
            "code":    "ETUDIANT_INTROUVABLE",
            "message": "Aucun étudiant trouvé avec l'id 'ETU-999'"
        }
    }
    Ce format uniforme facilite la gestion des erreurs côté front-end.
    """
    return JSONResponse(
        status_code = status,
        content     = {
            "erreur": {
                "code":    code,
                "message": message,
            }
        }
    )


def enregistrer_handlers(app: FastAPI) -> None:
    """
    Enregistre tous les gestionnaires d'erreurs sur l'app FastAPI.
    Appelée une seule fois dans main.py au démarrage.
    """

    # ── 404 : Ressource introuvable ──────────────────────────
    # Ces exceptions sont levées quand on cherche quelque chose
    # qui n'existe pas en base de données.

    @app.exception_handler(EtudiantIntrouvableError)
    async def handler_etudiant_introuvable(
        request: Request,
        exc: EtudiantIntrouvableError
    ) -> JSONResponse:
        # str(exc) appelle __str__ de l'exception → le message défini dans exceptions.py
        return _reponse_erreur(404, "ETUDIANT_INTROUVABLE", str(exc))

    @app.exception_handler(PaiementIntrouvableError)
    async def handler_paiement_introuvable(
        request: Request,
        exc: PaiementIntrouvableError
    ) -> JSONResponse:
        return _reponse_erreur(404, "PAIEMENT_INTROUVABLE", str(exc))

    @app.exception_handler(QRCodeIntrouvableError)
    async def handler_qr_introuvable(
        request: Request,
        exc: QRCodeIntrouvableError
    ) -> JSONResponse:
        return _reponse_erreur(404, "QRCODE_INTROUVABLE", str(exc))

    @app.exception_handler(SpecialiteIntrouvableError)
    async def handler_specialite_introuvable(
        request: Request,
        exc: SpecialiteIntrouvableError
    ) -> JSONResponse:
        return _reponse_erreur(404, "SPECIALITE_INTROUVABLE", str(exc))

    @app.exception_handler(UtilisateurIntrouvableError)
    async def handler_utilisateur_introuvable(
        request: Request,
        exc: UtilisateurIntrouvableError
    ) -> JSONResponse:
        return _reponse_erreur(404, "UTILISATEUR_INTROUVABLE", str(exc))

    # ── 401 : Authentification ───────────────────────────────

    @app.exception_handler(IdentifiantsInvalidesError)
    async def handler_identifiants_invalides(
        request: Request,
        exc: IdentifiantsInvalidesError
    ) -> JSONResponse:
        return _reponse_erreur(401, "IDENTIFIANTS_INVALIDES", str(exc))

    @app.exception_handler(CompteDesactiveError)
    async def handler_compte_desactive(
        request: Request,
        exc: CompteDesactiveError
    ) -> JSONResponse:
        return _reponse_erreur(401, "COMPTE_DESACTIVE", str(exc))

    # ── 409 : Conflit (doublon) ──────────────────────────────
    # Levée quand on essaie de créer quelque chose qui existe déjà.

    @app.exception_handler(EtudiantDejaExistantError)
    async def handler_etudiant_existant(
        request: Request,
        exc: EtudiantDejaExistantError
    ) -> JSONResponse:
        return _reponse_erreur(409, "ETUDIANT_DEJA_EXISTANT", str(exc))

    @app.exception_handler(PaiementDejaEffectueError)
    async def handler_paiement_deja_effectue(
        request: Request,
        exc: PaiementDejaEffectueError
    ) -> JSONResponse:
        return _reponse_erreur(409, "PAIEMENT_DEJA_EFFECTUE", str(exc))

    @app.exception_handler(EtudiantSuppressionImpossibleError)
    async def handler_etudiant_suppression_impossible(
        request: Request,
        exc: EtudiantSuppressionImpossibleError
    ) -> JSONResponse:
        return _reponse_erreur(409, "ETUDIANT_SUPPRESSION_IMPOSSIBLE", str(exc))

    @app.exception_handler(UtilisateurDejaExistantError)
    async def handler_utilisateur_existant(
        request: Request,
        exc: UtilisateurDejaExistantError
    ) -> JSONResponse:
        return _reponse_erreur(409, "UTILISATEUR_DEJA_EXISTANT", str(exc))

    # ── 400 : Données invalides ──────────────────────────────
    # Levée quand les données envoyées violent une règle métier.

    @app.exception_handler(PaiementExcessifError)
    async def handler_paiement_excessif(
        request: Request,
        exc: PaiementExcessifError
    ) -> JSONResponse:
        return _reponse_erreur(400, "PAIEMENT_EXCESSIF", str(exc))

    @app.exception_handler(MontantNegatifError)
    async def handler_montant_negatif(
        request: Request,
        exc: MontantNegatifError
    ) -> JSONResponse:
        return _reponse_erreur(400, "MONTANT_NEGATIF", str(exc))

    @app.exception_handler(QRCodeNonAutoriseSError)
    async def handler_qr_non_autorise(
        request: Request,
        exc: QRCodeNonAutoriseSError
    ) -> JSONResponse:
        return _reponse_erreur(400, "QRCODE_NON_AUTORISE", str(exc))

    @app.exception_handler(FichierExcelInvalideError)
    async def handler_fichier_invalide(
        request: Request,
        exc: FichierExcelInvalideError
    ) -> JSONResponse:
        return _reponse_erreur(400, "FICHIER_EXCEL_INVALIDE", str(exc))

    @app.exception_handler(ImportExcelError)
    async def handler_import_excel(
        request: Request,
        exc: ImportExcelError
    ) -> JSONResponse:
        return _reponse_erreur(400, "IMPORT_EXCEL_ERREUR", str(exc))

    # ── 400 : ValueError (Value Objects) ─────────────────────
    # Levée par les Value Objects (Matricule, Email, Telephone...)
    # quand le format est incorrect.

    @app.exception_handler(ValueError)
    async def handler_valeur_invalide(
        request: Request,
        exc: ValueError
    ) -> JSONResponse:
        return _reponse_erreur(400, "VALEUR_INVALIDE", str(exc))

    # ── 500 : Erreur interne inattendue ──────────────────────
    # Filet de sécurité : attrape toute exception non gérée au-dessus.
    # On retourne un message générique pour ne pas exposer
    # les détails techniques à l'utilisateur.

    @app.exception_handler(Exception)
    async def handler_erreur_interne(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        # En production, on loguerait l'erreur complète ici
        # (avec un outil comme Sentry ou un fichier de log)
        print(f"[ERREUR INTERNE] {type(exc).__name__}: {exc}")
        return _reponse_erreur(
            500,
            "ERREUR_INTERNE",
            "Une erreur inattendue s'est produite. Veuillez réessayer."
        )