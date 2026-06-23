#Cas d'usage : Authentification (connexion, gestion des comptes)

# ============================================================
#  FICHIER : app/Application/use_cases/auth_use_cases.py
#
#  RÔLE : Cas d'usage liés à l'authentification et à la gestion
#         des comptes utilisateurs du personnel.
#
#  COUCHE : Application
#  NE CONNAÎT PAS : bcrypt, JWT, FastAPI (ces détails sont injectés
#  via les interfaces de service depuis l'Infrastructure)
# ============================================================

import uuid
from typing import List, Callable, Tuple

from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur
from app.Domain.interfaces import IUtilisateurRepository
from app.Domain.exceptions import (
    UtilisateurDejaExistantError,
    IdentifiantsInvalidesError,
    CompteDesactiveError,
)
from app.Application.DTOs.schemas import (
    UtilisateurCreerDTO,
    UtilisateurReponseDTO,
    TokenReponseDTO,
)


def _vers_dto(u: UtilisateurDomaine) -> UtilisateurReponseDTO:
    return UtilisateurReponseDTO(
        id_utilisateur = u.id_utilisateur,
        email          = u.email,
        nom            = u.nom,
        role           = u.role.value,
        actif          = u.actif,
    )


class CreerUtilisateurUseCase:
    """
    Crée un nouveau compte utilisateur (réservé aux admins, vérifié
    au niveau de la route via la dépendance require_roles).
    """

    def __init__(
        self,
        utilisateur_repo: IUtilisateurRepository,
        hasher_mot_de_passe: Callable[[str], str],
    ):
        self._repo = utilisateur_repo
        self._hasher = hasher_mot_de_passe

    async def executer(self, dto: UtilisateurCreerDTO) -> UtilisateurReponseDTO:
        existant = await self._repo.trouver_par_email(dto.email)
        if existant:
            raise UtilisateurDejaExistantError(dto.email)

        utilisateur = UtilisateurDomaine(
            id_utilisateur    = f"USR-{str(uuid.uuid4())[:8].upper()}",
            email             = dto.email,
            nom               = dto.nom,
            mot_de_passe_hash = self._hasher(dto.mot_de_passe),
            role              = RoleUtilisateur(dto.role),
            actif             = True,
        )
        sauvegarde = await self._repo.sauvegarder(utilisateur)
        return _vers_dto(sauvegarde)


class ConnexionUseCase:
    """
    Authentifie un utilisateur (email + mot de passe) et émet un token JWT.
    """

    def __init__(
        self,
        utilisateur_repo: IUtilisateurRepository,
        verifier_mot_de_passe: Callable[[str, str], bool],
        creer_token: Callable[[str, str, str], Tuple[str, int]],
    ):
        self._repo = utilisateur_repo
        self._verifier = verifier_mot_de_passe
        self._creer_token = creer_token

    async def executer(self, email: str, mot_de_passe: str) -> TokenReponseDTO:
        utilisateur = await self._repo.trouver_par_email(email.lower())

        # Message d'erreur volontairement identique que l'email existe ou non
        # (ne pas révéler quels emails ont un compte).
        if not utilisateur or not self._verifier(mot_de_passe, utilisateur.mot_de_passe_hash):
            raise IdentifiantsInvalidesError()

        if not utilisateur.actif:
            raise CompteDesactiveError()

        token, duree_secondes = self._creer_token(
            utilisateur.id_utilisateur, utilisateur.email, utilisateur.role.value
        )

        return TokenReponseDTO(
            access_token = token,
            expires_in   = duree_secondes,
            utilisateur  = _vers_dto(utilisateur),
        )


class ListerUtilisateursUseCase:
    """Liste tous les comptes utilisateurs (réservé aux admins)."""

    def __init__(self, utilisateur_repo: IUtilisateurRepository):
        self._repo = utilisateur_repo

    async def executer(self) -> List[UtilisateurReponseDTO]:
        utilisateurs = await self._repo.lister_tous()
        return [_vers_dto(u) for u in utilisateurs]
