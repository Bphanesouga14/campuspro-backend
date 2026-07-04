"""Routes photo étudiant + suppression spécialité."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import update
import base64

from app.Infrastructure.database.session import get_db
from app.Infrastructure.database.models import (
    Etudiant as EModele, Specialite as SModele
)
from app.Presentation.security import get_current_user, require_roles
from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur

router = APIRouter(tags=["Photos étudiants & Spécialités"])


@router.post("/etudiants/{id_etudiant}/photo")
async def uploader_photo_etudiant(
    id_etudiant: str,
    fichier: UploadFile = File(...),
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(
        require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.SECRETAIRE)
    ),
):
    """Upload la photo d'un étudiant."""
    contenu = await fichier.read()
    if len(contenu) > 3 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image trop volumineuse (max 3 Mo).")

    # Vérifier que l'étudiant existe
    e = await db.get(EModele, id_etudiant)
    if not e:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")

    media_type = fichier.content_type or "image/jpeg"
    b64        = base64.b64encode(contenu).decode()
    data_url   = f"data:{media_type};base64,{b64}"

    # UPDATE direct — fiable
    await db.execute(
        update(EModele)
        .where(EModele.id_etudiant == id_etudiant)
        .values(photo=data_url)
    )
    await db.flush()
    return {"photo": data_url, "message": f"Photo de {e.prenom} {e.nom} mise à jour."}


@router.get("/etudiants/{id_etudiant}/photo")
async def get_photo_etudiant(
    id_etudiant: str,
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    e = await db.get(EModele, id_etudiant)
    if not e or not e.photo:
        raise HTTPException(status_code=404, detail="Aucune photo pour cet étudiant.")
    return {"photo": e.photo}


@router.delete("/specialites/{id_specialite}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_specialite(
    id_specialite: str,
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(require_roles(RoleUtilisateur.ADMIN)),
):
    sp = await db.get(SModele, id_specialite)
    if not sp:
        raise HTTPException(status_code=404, detail="Spécialité introuvable.")
    try:
        await db.delete(sp)
        await db.flush()
    except Exception:
        raise HTTPException(
            status_code=409,
            detail="Impossible de supprimer : des étudiants sont liés à cette spécialité."
        )
