#Génération et décodage des tokens JWT

# ============================================================
#  FICHIER : app/Infrastructure/security/jwt_service.py
#
#  RÔLE : Créer et décoder les tokens JWT (JSON Web Token).
#
#  C'EST QUOI UN JWT ?
#  Un jeton signé numériquement qui prouve "je suis bien
#  l'utilisateur USR-001, avec le rôle ADMIN, et ce jeton est
#  valide jusqu'à telle heure". Le serveur peut vérifier la
#  signature sans avoir besoin d'interroger la base à chaque
#  requête pour valider la session.
#
#  STRUCTURE DU PAYLOAD (le contenu du jeton) :
#  {
#    "sub": "USR-001",       → l'identifiant de l'utilisateur
#    "email": "...",
#    "role": "ADMIN",
#    "exp": 1234567890       → timestamp d'expiration
#  }
#
#  COUCHE : Infrastructure
# ============================================================

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.core.config import settings


def creer_token(
    id_utilisateur: str,
    email: str,
    role: str,
    duree_minutes: Optional[int] = None,
) -> tuple[str, int]:
    """
    Crée un token JWT signé pour un utilisateur.
    Retourne (token, durée_de_validité_en_secondes).
    """
    duree = duree_minutes or settings.JWT_EXPIRATION_MINUTES
    expiration = datetime.now(timezone.utc) + timedelta(minutes=duree)

    payload = {
        "sub":   id_utilisateur,
        "email": email,
        "role":  role,
        "exp":   expiration,
        "iat":   datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, duree * 60


def decoder_token(token: str) -> dict:
    """
    Décode et vérifie un token JWT.
    Lève jwt.ExpiredSignatureError si expiré,
    jwt.InvalidTokenError (ou sous-classe) si invalide/falsifié.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
