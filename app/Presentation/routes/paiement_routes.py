#Routes pour les paiements et QR codes



#  RÔLE : Endpoints HTTP pour les paiements, QR codes
#         et notifications.
#
#  ROUTES DÉFINIES :
#  POST /paiements/{id}/payer    → Enregistrer un versement physique
#  GET  /paiements/retards       → Tous les paiements en retard
#  GET  /etudiants/{id}/qr-code  → QR code actif d'un étudiant
#
#  COUCHE : Présentation
# ============================================================

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
import base64

from app.Application.use_cases.paiement_use_cases import (
    EnregistrerVersementUseCase,
    ListerPaiementsEnRetardUseCase,
    ObtenirQRCodeEtudiantUseCase,
)
from app.Application.DTOs.schemas import (
    VersementDTO,
    PaiementReponseDTO,
    QRCodeReponseDTO,
)
from app.Domain.exceptions import (
    PaiementIntrouvableError,
    PaiementExcessifError,
    PaiementDejaEffectueError,
    EtudiantIntrouvableError,
    QRCodeIntrouvableError,
    MontantNegatifError,
)
from app.Presentation.dependencies import (
    get_enregistrer_versement_uc,
    get_lister_retards_uc,
    get_obtenir_qr_uc,
    get_etudiant_repo,
)
from app.Presentation.security import get_current_user, require_roles
from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur

# ── Routeur paiements ────────────────────────────────────────
router = APIRouter(tags=["Paiements & QR Codes"])


# ============================================================
#  ROUTE 1 : Enregistrer un versement physique
#  POST /api/v1/paiements/{id_paiement}/payer
# ============================================================
@router.post(
    "/paiements/{id_paiement}/payer",
    response_model=PaiementReponseDTO,
    summary="Enregistrer un versement physique à la caisse",
    description="""
Le caissier utilise cette route après avoir reçu l'argent.

**Ce que fait cette route automatiquement :**
1. Vérifie que le montant ne dépasse pas ce qui est attendu
2. Met à jour le statut (EN ATTENTE → PARTIEL → PAYÉ)
3. Génère le QR code si la tranche 1 est entièrement soldée
4. Envoie une notification au parent (Email + SMS)

**Corps de la requête :**
```json
{
  "montant": 75000,
  "date_paiement": "15/10/2024",
  "observations": "Reçu N°1234"
}
```
    """,
)
async def enregistrer_versement(
    # {id_paiement} extrait depuis l'URL
    id_paiement: str,
    # Corps JSON validé automatiquement par Pydantic
    versement: VersementDTO,
    use_case: EnregistrerVersementUseCase = Depends(
        get_enregistrer_versement_uc
    ),
    _utilisateur: UtilisateurDomaine = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.CAISSIER)
    ),
):
    try:
        return await use_case.executer(id_paiement, versement)

    except PaiementIntrouvableError as e:
        # Le paiement (tranche) demandé n'existe pas en base
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(e),
        )
    except PaiementDejaEffectueError as e:
        # La tranche est déjà entièrement payée
        # HTTP 409 Conflict = état incompatible avec la demande
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = str(e),
        )
    except PaiementExcessifError as e:
        # Le montant versé dépasse ce qui est attendu
        # HTTP 400 Bad Request = données incorrectes
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = str(e),
        )
    except MontantNegatifError as e:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = str(e),
        )


# ============================================================
#  ROUTE 2 : Lister les paiements en retard
#  GET /api/v1/paiements/retards
# ============================================================
@router.get(
    "/paiements/retards",
    response_model=List[PaiementReponseDTO],
    summary="Tous les paiements en retard",
    description="""
Liste tous les paiements dont la date limite est dépassée
et qui ne sont pas encore soldés.

Utile pour :
- Envoyer des relances groupées aux parents
- Générer le rapport quotidien des retards
- Prendre des décisions sur les accès campus
    """,
)
async def paiements_en_retard(
    use_case: ListerPaiementsEnRetardUseCase = Depends(get_lister_retards_uc),
    _utilisateur: UtilisateurDomaine = Depends(get_current_user),
):
    # Pas d'exception possible ici → on retourne simplement la liste
    # (peut être vide si aucun retard)
    return await use_case.executer()


# ============================================================
#  ROUTE 3 : QR code actif d'un étudiant
#  GET /api/v1/etudiants/{id_etudiant}/qr-code
# ============================================================
@router.get(
    "/etudiants/{id_etudiant}/qr-code",
    response_model=QRCodeReponseDTO,
    summary="QR code actif d'un étudiant",
    description="""
Retourne le QR code actif de l'étudiant.

Le champ `qr_data` contient l'image en base64.
Pour l'afficher dans une page web :
```html
<img src="data:image/png;base64,{qr_data}" />
```

**Erreur 404** si aucun QR code actif n'existe
(étudiant pas encore à jour de paiement).
    """,
)
async def obtenir_qr_code(
    id_etudiant: str,
    use_case: ObtenirQRCodeEtudiantUseCase = Depends(get_obtenir_qr_uc),
    _utilisateur: UtilisateurDomaine = Depends(get_current_user),
):
    try:
        return await use_case.executer(id_etudiant)

    except EtudiantIntrouvableError as e:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(e),
        )
    except QRCodeIntrouvableError as e:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(e),
        )


# ============================================================
#  ROUTE 4 : Image PNG du QR code (binaire direct)
#  GET /api/v1/etudiants/{id_etudiant}/qr-code/image
# ============================================================
@router.get(
    "/etudiants/{id_etudiant}/qr-code/image",
    summary="Image PNG du QR code actif d'un étudiant",
    description="""
Retourne directement l'image PNG du QR code (binaire), pratique pour
l'afficher dans une balise `<img src="/api/v1/etudiants/ETU-001/qr-code/image">`
sans devoir décoder le base64 côté front-end.

**Erreur 404** si aucun QR code actif n'existe.
    """,
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
async def obtenir_qr_code_image(
    id_etudiant: str,
    use_case: ObtenirQRCodeEtudiantUseCase = Depends(get_obtenir_qr_uc),
    etudiant_repo = Depends(get_etudiant_repo),
    _utilisateur: UtilisateurDomaine = Depends(get_current_user),
):
    try:
        qr = await use_case.executer(id_etudiant)
    except EtudiantIntrouvableError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except QRCodeIntrouvableError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    contenu = qr.qr_data

    # Si qr_data est vide (cas fréquent après un import Excel sans image),
    # on reconstruit le contenu du QR à partir des infos de l'étudiant.
    if not contenu:
        etudiant = await etudiant_repo.trouver_par_id(id_etudiant)
        infos = {
            "id_qrcode":   qr.id_qrcode,
            "id_etudiant": qr.id_etudiant,
            "specialite":  qr.id_specialite,
            "niveau":      qr.niveau,
            "valide":      qr.valide_jusqua,
        }
        if etudiant:
            infos["matricule"] = etudiant.matricule.valeur if hasattr(etudiant.matricule, "valeur") else str(etudiant.matricule)
            infos["nom"]       = f"{etudiant.nom} {etudiant.prenom}"
        import json as _json
        contenu = _json.dumps(infos, ensure_ascii=False)

    image_bytes = _qr_data_vers_png(contenu, id_etudiant)
    return Response(content=image_bytes, media_type="image/png")


def _qr_data_vers_png(qr_data: str, id_etudiant: str) -> bytes:
    """
    Convertit le champ qr_data en image PNG (bytes).

    Le champ qr_data peut contenir deux formats différents :
    1. Le base64 d'une image PNG (QR généré par l'app lors d'un paiement)
    2. Du texte JSON (QR importé depuis Excel : {"matricule": ..., "nom": ...})

    On essaie d'abord de le décoder comme une image PNG. Si ça échoue
    (ce n'est pas une image), on génère une nouvelle image QR à partir
    du texte avec la bibliothèque qrcode.
    """
    import base64 as _b64

    # ── Cas 1 : qr_data est déjà une image PNG en base64 ─────
    # On retire un éventuel préfixe "data:image/png;base64,"
    donnees = qr_data
    if donnees.startswith("data:"):
        donnees = donnees.split(",", 1)[-1]

    try:
        image_bytes = _b64.b64decode(donnees, validate=True)
        # Vérifier la signature PNG (8 premiers octets)
        if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return image_bytes
    except Exception:
        pass  # Ce n'est pas du base64 PNG → on passe au cas 2

    # ── Cas 2 : qr_data est du texte (JSON) → générer le QR ──
    try:
        import qrcode
        import io as _io

        qr = qrcode.QRCode(
            version          = 1,
            error_correction = qrcode.constants.ERROR_CORRECT_H,
            box_size         = 10,
            border           = 4,
        )
        qr.add_data(qr_data)        # On encode le texte tel quel
        qr.make(fit=True)
        image  = qr.make_image(fill_color="black", back_color="white")
        buffer = _io.BytesIO()
        image.save(buffer)
        return buffer.getvalue()
    except ImportError:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = "La bibliothèque 'qrcode' n'est pas installée sur le serveur.",
        )
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = f"Impossible de générer l'image QR : {e}",
        )
