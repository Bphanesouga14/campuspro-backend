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


from fastapi.responses import StreamingResponse
import io

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
from app.Infrastructure.database.session import get_db
from app.Presentation.security import get_current_user, require_roles
from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur

# ── Routeur paiements ────────────────────────────────────────
router = APIRouter(tags=["Paiements & QR Codes"])


# ============================================================
#  ROUTE 1 : Enregistrer un versement physique
#  POST /api/v1/paiements/{id_paiement}/payer
# ============================================================



@router.get(
    "/paiements/{id_paiement}/recu",
    summary="Télécharger le reçu PDF d'un paiement",
)
async def telecharger_recu(
    id_paiement: str,
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    """
    Génère et retourne le reçu PDF d'un paiement.
    Appelé par le frontend avec un lien de téléchargement direct.
    """
    from app.Infrastructure.database.models import (
        Paiement as PModele, Etudiant as EModele
    )
    from app.Infrastructure.services.pdf_service import generer_recu_pdf

        # Récupérer le paiement
    p = await db.get(PModele, id_paiement)
    if not p:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")

    if p.montant_paye == 0:
        raise HTTPException(
            status_code=400,
            detail="Aucun versement enregistré pour ce paiement."
        )

    # Récupérer l'étudiant
    e = await db.get(EModele, p.id_etudiant)
    nom = f"{e.prenom} {e.nom}" if e else p.id_etudiant
    mat = str(e.matricule) if e else ""

    # Date de paiement — peut être None ou un objet date
    date_pai = "—"
    if p.date_paiement:
        if hasattr(p.date_paiement, "strftime"):
            date_pai = p.date_paiement.strftime("%d/%m/%Y")
        else:
            date_pai = str(p.date_paiement)

    # Montant payé — peut être None
    montant_paye = int(p.montant_paye or 0)
    montant_attendu = int(p.montant_attendu or 0)

    # Générer le PDF
    pdf_bytes = generer_recu_pdf(
        etudiant_nom    = nom,
        etudiant_mat    = mat,
        specialite      = str(p.id_specialite or ""),
        niveau          = int(p.niveau or 1),
        numero_tranche  = int(p.numero_tranche or 1),
        montant_attendu = montant_attendu,
        montant_paye    = montant_paye,
        date_paiement   = date_pai,
        id_paiement     = id_paiement,
    )
    nom_fichier = f"Recu_{mat}_{id_paiement}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={nom_fichier}"
        }
    )





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
    db = Depends(get_db),
    _utilisateur: UtilisateurDomaine = Depends(get_current_user),
):
    try:
        qr = await use_case.executer(id_etudiant)
    except EtudiantIntrouvableError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except QRCodeIntrouvableError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Récupérer l'étudiant et sa photo
    from app.Infrastructure.database.models import Etudiant as EModele
    e_modele = await db.get(EModele, id_etudiant)
    etudiant = await etudiant_repo.trouver_par_id(id_etudiant)

    # Construire le contenu du QR
    contenu = qr.qr_data
    if not contenu:
        import json as _json
        infos = {
            "id_qrcode":   qr.id_qrcode,
            "id_etudiant": id_etudiant,
            "specialite":  qr.id_specialite,
            "niveau":      qr.niveau,
            "valide":      qr.valide_jusqua,
        }
        if etudiant:
            infos["matricule"] = str(etudiant.matricule.valeur) if hasattr(etudiant.matricule, "valeur") else str(etudiant.matricule)
            infos["nom"]       = f"{etudiant.nom} {etudiant.prenom}"
        contenu = _json.dumps(infos, ensure_ascii=False)

    # Générer l'image QR avec photo intégrée si disponible
    photo_data = e_modele.photo if e_modele else None
    image_bytes = _generer_qr_avec_photo(contenu, id_etudiant, photo_data, etudiant)
    return Response(content=image_bytes, media_type="image/png")


def _generer_qr_avec_photo(contenu: str, id_etudiant: str, photo_data: str | None, etudiant) -> bytes:
    """
    Génère un QR code enrichi :
    - Si l'étudiant a une photo → la photo apparaît au centre du QR
    - Sinon → QR code simple
    Utilise Pillow (PIL) pour la composition d'images.
    """
    import io, base64 as _b64
    try:
        import qrcode
        from qrcode.image.styledpil import StyledPilImage
        from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
        from PIL import Image, ImageDraw, ImageFont, ImageOps
    except ImportError:
        return _qr_data_vers_png(contenu, id_etudiant)

    # 1. Générer le QR code de base
    niveau_correction = qrcode.constants.ERROR_CORRECT_H if photo_data else qrcode.constants.ERROR_CORRECT_M
    qr = qrcode.QRCode(
        version          = 1,
        error_correction = niveau_correction,
        box_size         = 10,
        border           = 4,
    )
    qr.add_data(contenu)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="#1a1a2e", back_color="white").convert("RGB")
    qr_size = qr_img.size[0]

    if photo_data:
        try:
            # 2. Décoder la photo de l'étudiant
            if "," in photo_data:
                photo_b64 = photo_data.split(",", 1)[1]
            else:
                photo_b64 = photo_data
            photo_bytes = _b64.b64decode(photo_b64)
            photo_img   = Image.open(io.BytesIO(photo_bytes)).convert("RGB")

            # 3. Rogner en cercle et redimensionner (20% du QR)
            logo_size = int(qr_size * 0.22)
            photo_img = photo_img.resize((logo_size, logo_size), Image.LANCZOS)

            # Masque circulaire
            masque = Image.new("L", (logo_size, logo_size), 0)
            draw   = ImageDraw.Draw(masque)
            draw.ellipse((0, 0, logo_size, logo_size), fill=255)

            # Fond blanc rond derrière la photo
            fond_blanc = Image.new("RGB", (logo_size + 8, logo_size + 8), "white")
            fond_pos   = ((qr_size - logo_size - 8) // 2, (qr_size - logo_size - 8) // 2)
            qr_img.paste(fond_blanc, fond_pos)

            # Coller la photo au centre
            photo_rgba = Image.new("RGBA", photo_img.size)
            photo_rgba.paste(photo_img)
            photo_rgba.putalpha(masque)

            pos = ((qr_size - logo_size) // 2, (qr_size - logo_size) // 2)
            qr_img.paste(photo_img, pos, masque)

        except Exception:
            pass  # Si erreur avec la photo → QR simple

    # 4. Créer une image finale avec infos étudiant en bas
    marge     = 20
    info_h    = 60
    total_h   = qr_size + info_h + marge
    finale    = Image.new("RGB", (qr_size, total_h), "white")
    finale.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(finale)
    # Ligne de séparation
    draw.line([(marge, qr_size + 5), (qr_size - marge, qr_size + 5)], fill="#e0e0e0", width=1)

    # Texte infos étudiant
    if etudiant:
        nom_complet = f"{etudiant.prenom} {etudiant.nom}" if etudiant else ""
        try:
            mat = etudiant.matricule.valeur if hasattr(etudiant.matricule, "valeur") else str(etudiant.matricule)
        except:
            mat = ""
        draw.text((qr_size // 2, qr_size + 18), nom_complet, fill="#1a1a2e", anchor="mm")
        draw.text((qr_size // 2, qr_size + 38), mat, fill="#666666", anchor="mm")

    buf = io.BytesIO()
    finale.save(buf, format="PNG")
    return buf.getvalue()


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
    


@router.get(
    "/etudiants/{id_etudiant}/carte",
    summary="Générer la carte étudiant PDF",
)
async def telecharger_carte_etudiant(
    id_etudiant: str,
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    """
    Génère et télécharge la carte étudiant PDF.
    Contient : photo, nom, matricule, spécialité,
    niveau, QR code recto/verso.
    """
    from app.Infrastructure.database.models import Etudiant as EModele
    from app.Infrastructure.services.carte_etudiant_service import (
        generer_carte_etudiant_pdf
    )

    e = await db.get(EModele, id_etudiant)
    if not e:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")

    try:
        pdf_bytes = generer_carte_etudiant_pdf(
            id_etudiant = e.id_etudiant,
            nom         = e.nom,
            prenom      = e.prenom,
            matricule   = str(e.matricule),
            specialite  = str(e.code_specialite),
            niveau      = int(e.niveau),
            annee       = str(e.annee_academique),
            photo_data  = getattr(e, "photo", None),
        )
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur génération carte : {str(ex)}"
        )

    nom_fichier = f"Carte_{e.matricule}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nom_fichier}"}
    )
