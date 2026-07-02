"""Routes de gestion du profil personnel."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import base64

from sqlalchemy import update
from app.Infrastructure.database.session import get_db
from app.Infrastructure.database.models import Utilisateur as UModele
from app.Infrastructure.repositories.utilisateur_repo import SQLAlchemyUtilisateurRepository
from app.Infrastructure.security.mot_de_passe import hasher_mot_de_passe, verifier_mot_de_passe
from app.Presentation.security import get_current_user
from app.Domain.entities import UtilisateurDomaine
from app.Application.DTOs.schemas import UtilisateurReponseDTO

router = APIRouter(prefix="/profil", tags=["Mon profil"])


class ModifierProfilDTO(BaseModel):
    nom:                  Optional[str] = None
    email:                Optional[str] = None
    mot_de_passe_actuel:  Optional[str] = None
    nouveau_mot_de_passe: Optional[str] = None


@router.get("", response_model=UtilisateurReponseDTO)
async def mon_profil(
    utilisateur: UtilisateurDomaine = Depends(get_current_user),
    db = Depends(get_db),
):
    """Retourne le profil complet incluant la photo."""
    u = await db.get(UModele, utilisateur.id_utilisateur)
    return {
        "id_utilisateur": u.id_utilisateur,
        "email":          u.email,
        "nom":            u.nom,
        "role":           u.role.value if hasattr(u.role, "value") else u.role,
        "actif":          u.actif,
        "photo":          u.photo,
    }


@router.put("", response_model=UtilisateurReponseDTO)
async def modifier_mon_profil(
    dto: ModifierProfilDTO,
    utilisateur: UtilisateurDomaine = Depends(get_current_user),
    db = Depends(get_db),
):
    u = await db.get(UModele, utilisateur.id_utilisateur)
    if not u:
        raise HTTPException(status_code=404, detail="Compte introuvable.")

    if dto.nom:   u.nom   = dto.nom
    if dto.email: u.email = dto.email

    if dto.nouveau_mot_de_passe:
        if not dto.mot_de_passe_actuel:
            raise HTTPException(status_code=400, detail="Fournissez votre mot de passe actuel.")
        if not verifier_mot_de_passe(dto.mot_de_passe_actuel, u.mot_de_passe_hash):
            raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect.")
        if len(dto.nouveau_mot_de_passe) < 8:
            raise HTTPException(status_code=400, detail="Min. 8 caractères requis.")
        u.mot_de_passe_hash = hasher_mot_de_passe(dto.nouveau_mot_de_passe)

    await db.flush()
    return {
        "id_utilisateur": u.id_utilisateur,
        "email":          u.email,
        "nom":            u.nom,
        "role":           u.role.value if hasattr(u.role, "value") else u.role,
        "actif":          u.actif,
        "photo":          u.photo,
    }


@router.post("/photo")
async def uploader_ma_photo(
    fichier: UploadFile = File(...),
    utilisateur: UtilisateurDomaine = Depends(get_current_user),
    db = Depends(get_db),
):
    """Upload la photo de profil — retourne la data URL pour mise à jour immédiate."""
    contenu = await fichier.read()
    if len(contenu) > 3 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop volumineuse (max 3 Mo).")

    media_type = fichier.content_type or "image/jpeg"
    b64        = base64.b64encode(contenu).decode()
    data_url   = f"data:{media_type};base64,{b64}"

    # Mise à jour directe via UPDATE SQL — la plus fiable
    await db.execute(
        update(UModele)
        .where(UModele.id_utilisateur == utilisateur.id_utilisateur)
        .values(photo=data_url)
    )
    await db.flush()
    return {"photo": data_url, "message": "Photo mise à jour avec succès."}


@router.get("/photo/{id_utilisateur}")
async def get_photo_utilisateur(
    id_utilisateur: str,
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    u = await db.get(UModele, id_utilisateur)
    if not u or not u.photo:
        raise HTTPException(status_code=404, detail="Aucune photo.")
    return {"photo": u.photo}
