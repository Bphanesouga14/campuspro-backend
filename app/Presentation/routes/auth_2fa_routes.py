"""
Authentification à double facteur (2FA) par email.

Flux :
  1. POST /auth/login     → vérifie email+mdp → envoie code 6 chiffres par email
  2. POST /auth/verifier  → vérifie le code → retourne le vrai token JWT
"""
import random
import string
from datetime import datetime, timedelta, timezone
datetime.now(timezone.utc)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, delete

from app.Infrastructure.database.session import get_db
from app.Infrastructure.database.models import (
    Utilisateur as UModele,
    CodeAuthentification
)
from app.Infrastructure.security.mot_de_passe import verifier_mot_de_passe
from app.Infrastructure.security.jwt_service import creer_token
from app.Infrastructure.services.qr_notification_services import NotificationServiceImpl
from app.core.config import settings

# Ligne 1 du fichier auth_2fa_routes.py
router = APIRouter(prefix="/auth", tags=["Authentification 2FA"])


class LoginDTO(BaseModel):
    email:       str
    mot_de_passe: str


class VerifierCodeDTO(BaseModel):
    email: str
    code:  str


def _generer_code() -> str:
    """Génère un code numérique à 6 chiffres."""
    return "".join(random.choices(string.digits, k=6))


async def _envoyer_code_email(email: str, nom: str, code: str):
    """Envoie le code 2FA par email de manière asynchrone."""
    import asyncio
    service = NotificationServiceImpl()
    message = (
        f"Bonjour {nom},\n\n"
        f"Votre code de connexion CampusPro est :\n\n"
        f"    {code}\n\n"
        f"Ce code est valable 10 minutes.\n"
        f"Si vous n'avez pas demandé ce code, ignorez cet email.\n\n"
        f"— L'équipe CampusPro"
    )
    await asyncio.to_thread(
        service._envoyer_email_sync,
        email,
        "🔐 Votre code de connexion CampusPro",
        message
    )


@router.post("/login", summary="Étape 1 : connexion → envoi du code 2FA")
async def login_etape1(dto: LoginDTO, db=Depends(get_db)):
    """
    Vérifie email + mot de passe.
    Si corrects → envoie un code à 6 chiffres par email.
    Retourne un message de confirmation (pas encore de token).
    """
    from sqlalchemy import select
    res = await db.execute(
        select(UModele).where(UModele.email == dto.email.lower())
    )
    u = res.scalar_one_or_none()

    # Message générique pour ne pas révéler si l'email existe
    if not u or not verifier_mot_de_passe(dto.mot_de_passe, u.mot_de_passe_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect."
        )

    if not u.actif:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ce compte a été désactivé."
        )

    # Supprimer les anciens codes de cet utilisateur
    await db.execute(
        delete(CodeAuthentification)
        .where(CodeAuthentification.id_utilisateur == u.id_utilisateur)
    )

    # Créer un nouveau code valable 10 minutes
    code = _generer_code()
    expiration = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)

    db.add(CodeAuthentification(
        id_utilisateur = u.id_utilisateur,
        code           = code,
        expire_a       = expiration,
    ))
    await db.flush()

    # Envoyer le code par email
    try:
        await _envoyer_code_email(u.email, u.nom, code)
    except Exception as e:
        print(f"[ERREUR EMAIL 2FA] {e}")
        # En développement : afficher le code dans le terminal
        print(f"[DEV] Code 2FA pour {u.email} : {code}")

    # Masquer partiellement l'email pour la réponse
    parts   = u.email.split("@")
    masque  = parts[0][:2] + "***@" + parts[1]

    return {
        "message":       f"Code envoyé à {masque}",
        "email_masque":  masque,
        "expire_dans":   "10 minutes",
    }


@router.post("/verifier", summary="Étape 2 : vérifier le code → obtenir le token")
async def login_etape2(dto: VerifierCodeDTO, db=Depends(get_db)):
    """
    Vérifie le code 2FA reçu par email.
    Si correct → retourne le token JWT + infos utilisateur.
    """
    res = await db.execute(
        select(UModele).where(UModele.email == dto.email.lower())
    )
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable.")

    # Chercher le code valide
    res2 = await db.execute(
        select(CodeAuthentification)
        .where(
            CodeAuthentification.id_utilisateur == u.id_utilisateur,
            CodeAuthentification.utilise == False,
            CodeAuthentification.expire_a >= datetime.utcnow(),
        )
        .order_by(CodeAuthentification.created_at.desc())
        .limit(1)
    )
    code_db = res2.scalar_one_or_none()

    if not code_db or code_db.code != dto.code.strip():
        raise HTTPException(
            status_code=401,
            detail="Code incorrect ou expiré. Recommencez la connexion."
        )

    # Marquer le code comme utilisé
    code_db.utilise = True
    await db.flush()

    # Générer le token JWT
    token, duree = creer_token(u.id_utilisateur, u.email, u.role.value)

    return {
        "access_token": token,
        "token_type":   "bearer",
        "expires_in":   duree,
        "utilisateur": {
            "id_utilisateur": u.id_utilisateur,
            "email":          u.email,
            "nom":            u.nom,
            "role":           u.role.value if hasattr(u.role, "value") else u.role,
            "actif":          u.actif,
            "photo":          getattr(u, "photo", None),
        }
    }