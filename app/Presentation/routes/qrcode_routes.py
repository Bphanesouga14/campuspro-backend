"""
Routes de gestion manuelle des QR codes.
Permet aux utilisateurs autorisés de modifier
le statut d'un QR code (ACTIF / INACTIF).
"""
import io
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from typing import Optional

from app.Infrastructure.database.session import get_db
from app.Infrastructure.database.models import QRCode, Etudiant, StatutQREnum
from app.Presentation.security import get_current_user, require_roles
from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur

router = APIRouter(prefix="/qrcodes", tags=["QR Codes"])

ADMIN      = RoleUtilisateur.ADMIN
SECRETAIRE = RoleUtilisateur.SECRETAIRE
CAISSIER   = RoleUtilisateur.CAISSIER


# ── DTOs ─────────────────────────────────────────────────────
class ModifierStatutDTO(BaseModel):
    statut: str
    raison: Optional[str] = None


class QRCodeReponse(BaseModel):
    id_qrcode:    str
    id_etudiant:  str
    nom_etudiant: str
    statut:       str
    modifie_par:  str
    raison:       Optional[str]
    message:      str


# ── 1. Liste tous les QR codes ────────────────────────────────
@router.get(
    "",
    summary="Lister tous les QR codes",
)
async def lister_qrcodes(
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    res = await db.execute(
        select(QRCode, Etudiant.nom, Etudiant.prenom, Etudiant.matricule)
        .join(Etudiant, QRCode.id_etudiant == Etudiant.id_etudiant)
        .order_by(QRCode.date_generation.desc())
    )
    rows = res.all()
    return [
        {
            "id_qrcode":       qr.id_qrcode,
            "id_etudiant":     qr.id_etudiant,
            "nom_etudiant":    f"{prenom} {nom}",
            "matricule":       matricule,
            "statut":          qr.statut.value if hasattr(qr.statut, "value") else str(qr.statut),
            "date_generation": str(qr.date_generation) if qr.date_generation else None,
        }
        for qr, nom, prenom, matricule in rows
    ]


# ── 2. QR code d'un étudiant ──────────────────────────────────
@router.get(
    "/etudiant/{id_etudiant}",
    summary="QR code d'un étudiant",
)
async def qrcode_etudiant(
    id_etudiant: str,
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    res = await db.execute(
        select(QRCode)
        .where(QRCode.id_etudiant == id_etudiant)
        .order_by(QRCode.date_generation.desc())
        .limit(1)
    )
    qr = res.scalar_one_or_none()
    if not qr:
        raise HTTPException(
            status_code=404,
            detail="Aucun QR code pour cet étudiant."
        )
    etudiant = await db.get(Etudiant, id_etudiant)
    return {
        "id_qrcode":    qr.id_qrcode,
        "id_etudiant":  qr.id_etudiant,
        "statut":       qr.statut.value if hasattr(qr.statut, "value") else str(qr.statut),
        "nom_etudiant": f"{etudiant.prenom} {etudiant.nom}" if etudiant else "Inconnu",
    }


# ── 3. Modifier le statut — ADMIN et SECRETAIRE ───────────────
@router.patch(
    "/modifier-statut/{id_qrcode}",
    response_model=QRCodeReponse,
    summary="Modifier le statut d'un QR code (Admin/Secrétaire)",
)
async def modifier_statut_qrcode(
    id_qrcode: str,
    dto: ModifierStatutDTO,
    db = Depends(get_db),
    utilisateur: UtilisateurDomaine = Depends(
        require_roles(ADMIN, SECRETAIRE)
    ),
):
    """
    Modifie manuellement le statut d'un QR code.

    - **ADMIN** : peut activer et désactiver n'importe quel QR code
    - **SECRETAIRE** : peut activer et désactiver n'importe quel QR code

    Statuts acceptés : `ACTIF` ou `INACTIF`
    """
    # Valider le statut
    statuts_valides = [e.value for e in StatutQREnum]
    if dto.statut.upper() not in statuts_valides:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide. Valeurs acceptées : {statuts_valides}"
        )

    # Récupérer le QR code
    qr = await db.get(QRCode, id_qrcode)
    if not qr:
        raise HTTPException(
            status_code=404,
            detail=f"QR code '{id_qrcode}' introuvable."
        )

    # Récupérer l'étudiant
    etudiant = await db.get(Etudiant, qr.id_etudiant)
    if not etudiant:
        raise HTTPException(
            status_code=404,
            detail="Étudiant introuvable."
        )

    # Vérifier si le statut change vraiment
    statut_actuel = qr.statut.value if hasattr(qr.statut, "value") else str(qr.statut)
    if statut_actuel == dto.statut.upper():
        return QRCodeReponse(
            id_qrcode    = qr.id_qrcode,
            id_etudiant  = qr.id_etudiant,
            nom_etudiant = f"{etudiant.prenom} {etudiant.nom}",
            statut       = statut_actuel,
            modifie_par  = utilisateur.id_utilisateur,
            raison       = dto.raison,
            message      = f"Statut déjà {statut_actuel} — aucune modification.",
        )

    # Appliquer le changement
    ancien_statut = statut_actuel
    try:
        # APRÈS — mapping explicite
        mapping = {
            "ACTIF":    StatutQREnum.ACTIF,
            "SUSPENDU": StatutQREnum.SUSPENDU,
        }
        qr.statut = mapping[dto.statut.upper()]
    except KeyError:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide : {dto.statut}. Valeurs : {statuts_valides}"
        )
    await db.flush()

    action = "activé" if dto.statut.upper() == "ACTIF" else "désactivé"
    print(
        f"[QR] {id_qrcode} {action} par {utilisateur.id_utilisateur} "
        f"— Raison: {dto.raison or 'Non précisée'}"
    )

    return QRCodeReponse(
        id_qrcode    = qr.id_qrcode,
        id_etudiant  = qr.id_etudiant,
        nom_etudiant = f"{etudiant.prenom} {etudiant.nom}",
        statut       = dto.statut.upper(),
        modifie_par  = utilisateur.id_utilisateur,
        raison       = dto.raison,
        message      = f"QR code {action} avec succès. Ancien statut : {ancien_statut}.",
    )


# ── 4. Activer rapidement — ADMIN seulement ───────────────────
@router.post(
    "/{id_qrcode}/activer",
    summary="Activer un QR code (Admin uniquement)",
)
async def activer_qrcode(
    id_qrcode: str,
    raison: Optional[str] = None,
    db = Depends(get_db),
    utilisateur: UtilisateurDomaine = Depends(require_roles(ADMIN)),
):
    """Active un QR code — réservé à l'Administrateur."""
    qr = await db.get(QRCode, id_qrcode)
    if not qr:
        raise HTTPException(
            status_code=404,
            detail="QR code introuvable."
        )

    etudiant  = await db.get(Etudiant, qr.id_etudiant)
    nom       = f"{etudiant.prenom} {etudiant.nom}" if etudiant else "Inconnu"
    ancien    = qr.statut.value if hasattr(qr.statut, "value") else str(qr.statut)

    qr.statut = StatutQREnum.ACTIF
    await db.flush()

    print(f"[QR] {id_qrcode} activé par {utilisateur.id_utilisateur}")
    return {
        "message":      f"QR code activé pour {nom}.",
        "id_qrcode":    id_qrcode,
        "statut":       "ACTIF",
        "ancien_statut": ancien,
        "modifie_par":  utilisateur.id_utilisateur,
        "raison":       raison,
    }


# ── 5. Désactiver rapidement — ADMIN et SECRETAIRE ────────────
@router.post(
    "/{id_qrcode}/desactiver",
    summary="Désactiver un QR code (Admin/Secrétaire)",
)
async def desactiver_qrcode(
    id_qrcode: str,
    raison: Optional[str] = None,
    db = Depends(get_db),
    utilisateur: UtilisateurDomaine = Depends(
        require_roles(ADMIN, SECRETAIRE)
    ),
):
    """
    Désactive un QR code.
    L'étudiant ne pourra plus entrer sur le campus
    jusqu'à réactivation manuelle ou paiement.
    """
    qr = await db.get(QRCode, id_qrcode)
    if not qr:
        raise HTTPException(
            status_code=404,
            detail="QR code introuvable."
        )

    etudiant  = await db.get(Etudiant, qr.id_etudiant)
    nom       = f"{etudiant.prenom} {etudiant.nom}" if etudiant else "Inconnu"
    ancien    = qr.statut.value if hasattr(qr.statut, "value") else str(qr.statut)

    qr.statut = StatutQREnum.INACTIF
    qr.statut = StatutQREnum.SUSPENDU 
    await db.flush()

    print(
        f"[QR] {id_qrcode} désactivé par {utilisateur.id_utilisateur} "
        f"— Raison: {raison or 'Non précisée'}"
    )
    return {
        "message":       f"QR code désactivé pour {nom}.",
        "id_qrcode":     id_qrcode,
        "statut":        "INACTIF",
        "ancien_statut": ancien,
        "modifie_par":   utilisateur.id_utilisateur,
        "raison":        raison,
    }










@router.post(
    "/changer-statut/{id_qrcode}",
    summary="Changer statut QR code",
)
async def changer_statut(
        id_qrcode: str,
        dto: ModifierStatutDTO,
        db = Depends(get_db),
        utilisateur: UtilisateurDomaine = Depends(
            require_roles(ADMIN, SECRETAIRE)
        ),
):
    qr = await db.get(QRCode, id_qrcode)
    if not qr:
        raise HTTPException(status_code=404, detail="QR code introuvable.")

    etudiant = await db.get(Etudiant, qr.id_etudiant)
    ancien   = qr.statut.value if hasattr(qr.statut, "value") else str(qr.statut)

    mapping = {
        "ACTIF":    StatutQREnum.ACTIF,
        "SUSPENDU": StatutQREnum.SUSPENDU,
    }
    if dto.statut.upper() not in mapping:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide. Valeurs : {list(mapping.keys())}"
        )

    qr.statut = mapping[dto.statut.upper()]
    await db.flush()

    action = "activé" if dto.statut.upper() == "ACTIF" else "suspendu"
    return {
       "message":      f"QR code {action} avec succès.",            "id_qrcode":    id_qrcode,
        "statut":       dto.statut.upper(),
        "ancien_statut": ancien,
        "modifie_par":  utilisateur.id_utilisateur,
    }