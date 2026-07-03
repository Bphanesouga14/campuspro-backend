"""
Routes de gestion des présences par scan QR.
Conçu pour être appelé par l'application mobile Flutter.

Flux :
  Flutter scanne QR → lit les données JSON → appelle POST /presences/scan
  → le backend vérifie le QR, incrémente la présence, retourne la confirmation.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, select, func
from sqlalchemy.orm import relationship

from app.Infrastructure.database.session import get_db
from app.Infrastructure.database.models import Base, QRCode, Etudiant
from app.Presentation.security import get_current_user
from app.Domain.entities import UtilisateurDomaine

router = APIRouter(prefix="/presences", tags=["Présences (Flutter)"])


# ── Modèle Présence (table créée automatiquement) ────────────
class Presence(Base):
    __tablename__ = "presences"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    id_etudiant   = Column(String(20), ForeignKey("etudiants.id_etudiant"), nullable=False)
    id_qrcode     = Column(String(20), ForeignKey("qr_codes.id_qrcode"), nullable=True)
    date_scan     = Column(DateTime, default=datetime.utcnow, nullable=False)
    cours         = Column(String(100), nullable=True)   # ex: "Mathématiques S1"
    scanner_par   = Column(String(20), nullable=True)    # ID utilisateur qui a scanné
    valide        = Column(Boolean, default=True)


# ── DTOs ─────────────────────────────────────────────────────
class ScanQRDTO(BaseModel):
    id_qrcode:   str
    id_etudiant: str
    cours:       Optional[str] = None

class PresenceReponse(BaseModel):
    id:           int
    id_etudiant:  str
    nom_etudiant: str
    date_scan:    str
    cours:        Optional[str]
    total_presences: int
    message:      str


# ── Endpoint principal : enregistrer une présence ────────────
@router.post("/scan", response_model=PresenceReponse, status_code=status.HTTP_201_CREATED,
    summary="Scanner un QR code → enregistrer une présence",
    description="""
Appelé par l'application Flutter après le scan du QR code.

**Corps attendu :**
```json
{
  "id_qrcode":   "QR-001",
  "id_etudiant": "ETU-2024-001",
  "cours":       "Mathématiques S1"
}
```
Retourne la confirmation avec le total de présences de l'étudiant.
    """
)
async def scanner_qr(
    dto: ScanQRDTO,
    db = Depends(get_db),
    utilisateur: UtilisateurDomaine = Depends(get_current_user),
):
    # 1. Vérifier que l'étudiant existe
    etudiant = await db.get(Etudiant, dto.id_etudiant)
    if not etudiant:
        raise HTTPException(status_code=404, detail=f"Étudiant '{dto.id_etudiant}' introuvable.")

    # 2. Vérifier que le QR code est actif (si fourni)
    if dto.id_qrcode:
        qr = await db.get(QRCode, dto.id_qrcode)
        if not qr:
            raise HTTPException(status_code=404, detail="QR code introuvable.")
        if qr.statut.value != "ACTIF":
            raise HTTPException(
                status_code=400,
                detail=f"Ce QR code n'est plus valide (statut : {qr.statut.value})."
            )

    # 3. Enregistrer la présence
    presence = Presence(
        id_etudiant  = dto.id_etudiant,
        id_qrcode    = dto.id_qrcode or None,
        cours        = dto.cours,
        scanner_par  = utilisateur.id_utilisateur,
        date_scan    = datetime.utcnow(),
    )
    db.add(presence)
    await db.flush()

    # 4. Compter le total des présences de cet étudiant
    res = await db.execute(
        select(func.count()).where(Presence.id_etudiant == dto.id_etudiant)
    )
    total = res.scalar() or 0

    return PresenceReponse(
        id           = presence.id,
        id_etudiant  = dto.id_etudiant,
        nom_etudiant = f"{etudiant.prenom} {etudiant.nom}",
        date_scan    = presence.date_scan.strftime("%d/%m/%Y %H:%M"),
        cours        = dto.cours,
        total_presences = total,
        message      = f"Présence enregistrée pour {etudiant.prenom} {etudiant.nom}. Total : {total} présence(s).",
    )


@router.get("/{id_etudiant}", summary="Historique des présences d'un étudiant")
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
        "id_etudiant":      id_etudiant,
        "total_presences":  len(presences),
        "presences": [
            {
                "id":        p.id,
                "date_scan": p.date_scan.strftime("%d/%m/%Y %H:%M"),
                "cours":     p.cours,
                "valide":    p.valide,
            }
            for p in presences
        ]
    }


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
    rows = res.all()
    return [
        {
            "id":           p.id,
            "id_etudiant":  p.id_etudiant,
            "nom_etudiant": f"{prenom} {nom}",
            "date_scan":    p.date_scan.strftime("%d/%m/%Y %H:%M"),
            "cours":        p.cours,
        }
        for p, nom, prenom in rows
    ]



@router.get("/info-qr/{id_qrcode}", summary="Infos complètes après scan QR")
async def info_apres_scan(
    id_qrcode: str,
    db = Depends(get_db),
):
    """
    Appelé par Flutter immédiatement après le scan du QR code.
    Retourne toutes les infos de l'étudiant + sa photo.
    
    Cette route est PUBLIQUE (pas de token requis) pour que
    l'app mobile puisse l'appeler sans authentification.
    
    Réponse :
    {
      "id_qrcode": "QR-001",
      "statut_qr": "ACTIF",
      "valide_jusqua": "30/09/2025",
      "etudiant": {
        "id": "ETU-2024-001",
        "nom": "MBARGA Jean",
        "matricule": "MAT-2024-INFO-001",
        "specialite": "INFO1",
        "niveau": 1,
        "annee_academique": "2024-2025",
        "photo": "data:image/jpeg;base64,..."
      }
    }
    """
    from sqlalchemy import select
    from app.Infrastructure.database.models import QRCode, Etudiant

    # 1. Récupérer le QR code
    qr = await db.get(QRCode, id_qrcode)
    if not qr:
        raise HTTPException(
            status_code=404,
            detail=f"QR code '{id_qrcode}' introuvable."
        )

    # 2. Récupérer l'étudiant lié
    etudiant = await db.get(Etudiant, qr.id_etudiant)
    if not etudiant:
        raise HTTPException(
            status_code=404,
            detail="Étudiant lié à ce QR code introuvable."
        )

    return {
        "id_qrcode":    qr.id_qrcode,
        "statut_qr":    qr.statut.value if hasattr(qr.statut, "value") else str(qr.statut),
        "valide_jusqua": qr.valide_jusqua,
        "etudiant": {
            "id":               etudiant.id_etudiant,
            "nom":              etudiant.nom,
            "prenom":           etudiant.prenom,
            "nom_complet":      f"{etudiant.prenom} {etudiant.nom}",
            "matricule":        etudiant.matricule,
            "specialite":       etudiant.code_specialite,
            "departement":      etudiant.id_specialite,
            "niveau":           etudiant.niveau,
            "annee_academique": etudiant.annee_academique,
            "sexe":             etudiant.sexe.value if hasattr(etudiant.sexe, "value") else str(etudiant.sexe),
            "telephone":        etudiant.telephone_etudiant,
            "email":            etudiant.email_etudiant,
            "photo":            etudiant.photo,  # data URL base64 ou null
        }
    }

#Route pour obtenir les statistiques globales des présences

@router.get("/absences/stats", summary="Statistiques globales des présences")
async def stats_presences(
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    """
    Retourne les statistiques de présence pour tous les étudiants.
    Utilisé pour le tableau de bord des absences.
    """
    from sqlalchemy import select, func
    from app.Infrastructure.database.models import Etudiant

    # Total de séances enregistrées (nb de scans distincts par date)
    res_total = await db.execute(
        select(func.count(func.distinct(
            func.date_trunc("day", Presence.date_scan)
        )))
    )
    total_seances = res_total.scalar() or 0

    # Présences par étudiant
    res = await db.execute(
        select(
            Presence.id_etudiant,
            func.count(Presence.id).label("nb_presences"),
        )
        .group_by(Presence.id_etudiant)
    )
    presences_par_etudiant = {row.id_etudiant: row.nb_presences for row in res.all()}

    # Récupérer tous les étudiants
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

    # Trier : les plus absents en premier
    stats.sort(key=lambda x: x["taux_presence"])

    return {
        "total_seances":   total_seances,
        "total_etudiants": len(etudiants),
        "en_alerte":       sum(1 for s in stats if s["alerte"]),
        "etudiants":       stats,
    }



# Route pour obtenir le détail des absences d'un étudiant

@router.get("/absences/{id_etudiant}", summary="Détail absences d'un étudiant")
async def absences_etudiant(
    id_etudiant: str,
    db = Depends(get_db),
    _: UtilisateurDomaine = Depends(get_current_user),
):
    """Retourne le détail des présences et absences d'un étudiant."""
    from app.Infrastructure.database.models import Etudiant

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
        "id_etudiant":  id_etudiant,
        "nom_complet":  f"{e.prenom} {e.nom}",
        "matricule":    e.matricule,
        "specialite":   e.code_specialite,
        "presences": [
            {
                "id":       p.id,
                "date":     p.date_scan.strftime("%d/%m/%Y"),
                "heure":    p.date_scan.strftime("%H:%M"),
                "cours":    p.cours or "—",
                "valide":   p.valide,
            }
            for p in presences
        ],
        "total_presences": len(presences),
    }
