"""
Routes de gestion des présences par scan QR.
Modèle : présences GLOBALES à l'entrée du campus.
Un scan par étudiant par jour — anti-doublon intégré.
"""

# APRÈS — retour simple avec status_code forcé dans Response
from fastapi.responses import JSONResponse

from datetime import datetime, date, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, select, func
from sqlalchemy.orm import relationship

from app.Infrastructure.database.session import get_db
from app.Infrastructure.database.models import Base, QRCode, Etudiant
from app.Presentation.security import get_current_user
from app.Domain.entities import UtilisateurDomaine

router = APIRouter(prefix="/presences", tags=["Présences (Flutter)"])


# ── Modèle Présence ──────────────────────────────────────────
class Presence(Base):
    __tablename__ = "presences"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    id_etudiant = Column(String(20), ForeignKey("etudiants.id_etudiant"), nullable=False)
    id_qrcode   = Column(String(20), ForeignKey("qr_codes.id_qrcode"), nullable=True)
    date_scan   = Column(DateTime, default=datetime.utcnow, nullable=False)
    cours       = Column(String(100), nullable=True)
    scanner_par = Column(String(20), nullable=True)
    valide      = Column(Boolean, default=True)


# ── DTOs ─────────────────────────────────────────────────────
class ScanQRDTO(BaseModel):
    id_qrcode:   str
    id_etudiant: str
    cours:       Optional[str] = None

class PresenceReponse(BaseModel):
    id:              int
    id_etudiant:     str
    nom_etudiant:    str
    date_scan:       str
    cours:           Optional[str]
    total_presences: int
    message:         str


# ── IMPORTANT : routes fixes AVANT les routes dynamiques ─────
# Ordre FastAPI : /scan → /info-qr/{x} → /absences/stats
#                → /absences/{x} → /{x} → /


# ── 1. Scan QR — enregistrer présence globale ────────────────
@router.post(
    "/scan",
    response_model=PresenceReponse,
    status_code=status.HTTP_201_CREATED,
    summary="Scanner un QR code → enregistrer la présence globale",
)
async def scanner_qr(
    dto: ScanQRDTO,
    db = Depends(get_db),
    utilisateur: UtilisateurDomaine = Depends(get_current_user),
):
    """
    Appelé par Flutter à l'entrée du campus.
    Vérifie la solvabilité, gère l'anti-doublon,
    incrémente le compteur global de présences.
    """
    # 1. Vérifier que l'étudiant existe
    etudiant = await db.get(Etudiant, dto.id_etudiant)
    if not etudiant:
        raise HTTPException(
            status_code=404,
            detail=f"Étudiant '{dto.id_etudiant}' introuvable."
        )

    # 2. Vérifier que le QR code est actif (solvabilité)
    if dto.id_qrcode:
        qr = await db.get(QRCode, dto.id_qrcode)
        if not qr:
            raise HTTPException(status_code=404, detail="QR code introuvable.")
        # APRÈS — message adapté selon le statut
        statut_qr = qr.statut.value if hasattr(qr.statut, "value") else str(qr.statut)
        if statut_qr != "ACTIF":
            if statut_qr == "SUSPENDU":
                detail = "QR code suspendu manuellement — contacter l'administration."
            elif statut_qr == "EXPIRÉ":
                detail = "QR code expiré — régulariser la situation financière."
            else:
                detail = f"QR code non valide (statut : {statut_qr})."
            raise HTTPException(status_code=403, detail=detail)

    # 3. Anti-doublon : déjà enregistré aujourd'hui ?
    aujourd_hui = date.today()
    res_doublon = await db.execute(
        select(Presence).where(
            Presence.id_etudiant == dto.id_etudiant,
            func.date(Presence.date_scan) == aujourd_hui,
            Presence.valide == True,
        )
    )
    presence_existante = res_doublon.scalar_one_or_none()


    if presence_existante is not None:
        res_total = await db.execute(
            select(func.count()).where(
                Presence.id_etudiant == dto.id_etudiant,
                Presence.valide == True,
            )
        )
        total = res_total.scalar() or 0
        return JSONResponse(
            status_code=200,
            content={
                "id":              presence_existante.id,
                "id_etudiant":     dto.id_etudiant,
                "nom_etudiant":    f"{etudiant.prenom} {etudiant.nom}",
                "date_scan":       presence_existante.date_scan.strftime("%d/%m/%Y %H:%M"),
                "cours":           dto.cours,
                "total_presences": total,
                "message":         f"Déjà enregistré aujourd'hui. Total : {total} présence(s).",
            }
        )

    # 4. Enregistrer la nouvelle présence globale
    presence = Presence(
        id_etudiant = dto.id_etudiant,
        id_qrcode   = dto.id_qrcode or None,
        cours       = dto.cours,
        scanner_par = utilisateur.id_utilisateur,
        date_scan   =datetime.utcnow(),  # <-- Vraie valeur temporelle, avec les ()
        valide      = True,
    )
    db.add(presence)
    await db.flush()

    # 5. Compter le total des présences valides
    res_total = await db.execute(
        select(func.count()).where(
            Presence.id_etudiant == dto.id_etudiant,
            Presence.valide == True,
        )
    )
    total = res_total.scalar() or 0

    return PresenceReponse(
        id              = presence.id,
        id_etudiant     = dto.id_etudiant,
        nom_etudiant    = f"{etudiant.prenom} {etudiant.nom}",
        date_scan       = presence.date_scan.strftime("%d/%m/%Y %H:%M"),
        cours           = dto.cours,
        total_presences = total,
        message         = f"Présence enregistrée. Total : {total} présence(s).",
    )


# ── 2. Infos QR après scan — appelé avant /scan ──────────────
@router.get(
    "/info-qr/{id_qrcode}",
    summary="Infos complètes étudiant après scan QR",
)
async def info_apres_scan(
    id_qrcode: str,
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    """
    Appelé par Flutter juste après le scan.
    Retourne photo + infos étudiant + statut QR.
    """
    qr = await db.get(QRCode, id_qrcode)
    if not qr:
        raise HTTPException(
            status_code=404,
            detail=f"QR code '{id_qrcode}' introuvable."
        )

    etudiant = await db.get(Etudiant, qr.id_etudiant)
    if not etudiant:
        raise HTTPException(
            status_code=404,
            detail="Étudiant lié à ce QR code introuvable."
        )

    statut_qr = qr.statut.value if hasattr(qr.statut, "value") else str(qr.statut)

    return {
        "id_qrcode":     qr.id_qrcode,
        "statut_qr":     statut_qr,
        "valide_jusqua": qr.valide_jusqua,
        "etudiant": {
            "id":               etudiant.id_etudiant,
            "nom":              etudiant.nom,
            "prenom":           etudiant.prenom,
            "nom_complet":      f"{etudiant.prenom} {etudiant.nom}",
            "matricule":        etudiant.matricule,
            "specialite":       etudiant.code_specialite,
            "niveau":           etudiant.niveau,
            "annee_academique": etudiant.annee_academique,
            "sexe":             etudiant.sexe.value if hasattr(etudiant.sexe, "value") else str(etudiant.sexe),
            "telephone":        etudiant.telephone_etudiant,
            "email":            etudiant.email_etudiant,
            "photo":            etudiant.photo,
        }
    }


# ── 3. Stats absences globales ───────────────────────────────
@router.get(
    "/absences/stats",
    summary="Statistiques globales des présences",
)
async def stats_presences(
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    # Total de jours distincts avec au moins un scan
    res_total = await db.execute(
        select(func.count(func.distinct(
            func.date_trunc("day", Presence.date_scan)
        ))).where(Presence.valide == True)
    )
    total_seances = res_total.scalar() or 0

    # Présences valides par étudiant
    res = await db.execute(
        select(
            Presence.id_etudiant,
            func.count(Presence.id).label("nb_presences"),
        )
        .where(Presence.valide == True)
        .group_by(Presence.id_etudiant)
    )
    presences_par_etudiant = {
        row.id_etudiant: row.nb_presences for row in res.all()
    }

    res_et = await db.execute(select(Etudiant))
    etudiants = res_et.scalars().all()

    stats = []
    for e in etudiants:
        nb_presences = presences_par_etudiant.get(e.id_etudiant, 0)
        nb_absences  = max(0, total_seances - nb_presences)
        taux = round(nb_presences / total_seances * 100, 1) if total_seances > 0 else 0
        stats.append({
            "id_etudiant":   e.id_etudiant,
            "nom":           e.nom,
            "prenom":        e.prenom,
            "nom_complet":   f"{e.prenom} {e.nom}",
            "matricule":     e.matricule,
            "specialite":    e.code_specialite,
            "niveau":        e.niveau,
            "nb_presences":  nb_presences,
            "nb_absences":   nb_absences,
            "total_seances": total_seances,
            "taux_presence": taux,
            "alerte":        taux < 75 and total_seances > 0,
        })

    stats.sort(key=lambda x: x["taux_presence"])

    return {
        "total_seances":   total_seances,
        "total_etudiants": len(etudiants),
        "en_alerte":       sum(1 for s in stats if s["alerte"]),
        "etudiants":       stats,
    }


# ── 4. Détail absences d'un étudiant ─────────────────────────
@router.get(
    "/absences/{id_etudiant}",
    summary="Détail présences/absences d'un étudiant",
)
async def absences_etudiant(
    id_etudiant: str,
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    e = await db.get(Etudiant, id_etudiant)
    if not e:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")

    res = await db.execute(
        select(Presence)
        .where(Presence.id_etudiant == id_etudiant)
        .order_by(Presence.date_scan.desc())
    )
    presences = res.scalars().all()

    return {
        "id_etudiant":     id_etudiant,
        "nom_complet":     f"{e.prenom} {e.nom}",
        "matricule":       e.matricule,
        "specialite":      e.code_specialite,
        "total_presences": len([p for p in presences if p.valide]),
        "presences": [
            {
                "id":     p.id,
                "date":   p.date_scan.strftime("%d/%m/%Y"),
                "heure":  p.date_scan.strftime("%H:%M"),
                "cours":  p.cours or "Entrée campus",
                "valide": p.valide,
            }
            for p in presences
        ],
    }


# ── 5. Historique d'un étudiant ──────────────────────────────
@router.get(
    "/{id_etudiant}",
    summary="Historique des présences d'un étudiant",
)
async def presences_etudiant(
    id_etudiant: str,
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    res = await db.execute(
        select(Presence)
        .where(Presence.id_etudiant == id_etudiant)
        .order_by(Presence.date_scan.desc())
        .limit(50)
    )
    presences = res.scalars().all()
    return {
        "id_etudiant":     id_etudiant,
        "total_presences": len(presences),
        "presences": [
            {
                "id":       p.id,
                "date_scan": p.date_scan.strftime("%d/%m/%Y %H:%M"),
                "cours":    p.cours or "Entrée campus",
                "valide":   p.valide,
            }
            for p in presences
        ],
    }


# ── 6. Toutes les présences (admin) ──────────────────────────
@router.get("", summary="Toutes les présences (admin)")
async def toutes_presences(
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    res = await db.execute(
        select(Presence, Etudiant.nom, Etudiant.prenom)
        .join(Etudiant, Presence.id_etudiant == Etudiant.id_etudiant)
        .order_by(Presence.date_scan.desc())
        .limit(100)
    )
    return [
        {
            "id":           p.id,
            "id_etudiant":  p.id_etudiant,
            "nom_etudiant": f"{prenom} {nom}",
            "date_scan":    p.date_scan.strftime("%d/%m/%Y %H:%M"),
            "cours":        p.cours or "Entrée campus",
            "valide":       p.valide,
        }
        for p, nom, prenom in res.all()
    ]