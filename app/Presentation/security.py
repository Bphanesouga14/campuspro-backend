#Sécurité : extraction du JWT et contrôle d'accès par rôle

# ============================================================
#  FICHIER : app/Presentation/security.py
#
#  RÔLE : Fournir les dépendances FastAPI qui protègent les routes :
#
#  - get_current_user      → exige un token JWT valide (n'importe quel rôle)
#  - require_roles(*roles) → exige un token JWT valide ET un rôle autorisé
#
#  UTILISATION DANS UNE ROUTE :
#      @router.get("/etudiants")
#      async def lister(utilisateur = Depends(get_current_user)):
#          ...
#
#      @router.post("/etudiants")
#      async def creer(
#          dto: EtudiantCreerDTO,
#          utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN, RoleUtilisateur.SECRETAIRE)),
#      ):
#          ...
#
#  COUCHE : Présentation
# ============================================================

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur
from app.Infrastructure.database.session import get_db
from app.Infrastructure.repositories.utilisateur_repo import SQLAlchemyUtilisateurRepository
from app.Infrastructure.security.jwt_service import decoder_token

# tokenUrl pointe vers la route de login — utilisé par Swagger UI
# pour afficher le bouton "Authorize" avec un formulaire email/mot de passe.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UtilisateurDomaine:
    """
    Dépendance FastAPI : décode le token JWT envoyé dans le header
    `Authorization: Bearer <token>`, vérifie sa validité, et charge
    l'utilisateur correspondant depuis la base.

    Lève une 401 si le token est absent, invalide, expiré, ou si
    l'utilisateur n'existe plus / a été désactivé.
    """
    erreur_auth = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail      = "Identifiants invalides ou expirés.",
        headers     = {"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decoder_token(token)
        id_utilisateur = payload.get("sub")
        if not id_utilisateur:
            raise erreur_auth
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Le token a expiré, veuillez vous reconnecter.",
            headers     = {"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise erreur_auth

    repo = SQLAlchemyUtilisateurRepository(db)
    utilisateur = await repo.trouver_par_id(id_utilisateur)

    if not utilisateur:
        raise erreur_auth
    if not utilisateur.actif:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Ce compte a été désactivé.",
            headers     = {"WWW-Authenticate": "Bearer"},
        )

    return utilisateur


def require_roles(*roles_autorises: RoleUtilisateur):
    """
    Fabrique de dépendance : retourne une dépendance FastAPI qui exige
    que l'utilisateur connecté ait un des rôles fournis.

    Exemple : Depends(require_roles(RoleUtilisateur.ADMIN))
    """

    async def verifier(
        utilisateur: UtilisateurDomaine = Depends(get_current_user),
    ) -> UtilisateurDomaine:
        if not utilisateur.a_le_role(*roles_autorises):
            noms_roles = ", ".join(r.value for r in roles_autorises)
            raise HTTPException(
                status_code = status.HTTP_403_FORBIDDEN,
                detail      = f"Accès refusé. Rôle requis : {noms_roles}.",
            )
        return utilisateur

    return verifier
