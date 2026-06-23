#Repository pour les comptes utilisateurs (authentification)

# ============================================================
#  FICHIER : app/Infrastructure/repositories/utilisateur_repo.py
#
#  RÔLE : Implémentation concrète de IUtilisateurRepository.
#         Toutes les opérations SQL sur la table "utilisateurs".
#
#  COUCHE : Infrastructure
# ============================================================

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.database.models import Utilisateur as UtilisateurModele, RoleEnum
from app.Domain.interfaces import IUtilisateurRepository
from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur


def _modele_vers_domaine(m: UtilisateurModele) -> UtilisateurDomaine:
    return UtilisateurDomaine(
        id_utilisateur    = m.id_utilisateur,
        email             = m.email,
        nom               = m.nom,
        mot_de_passe_hash = m.mot_de_passe_hash,
        role              = RoleUtilisateur(m.role.value if hasattr(m.role, "value") else m.role),
        actif             = m.actif,
        created_at        = m.created_at.isoformat() if m.created_at else None,
    )


def _domaine_vers_modele(
    d: UtilisateurDomaine,
    modele_existant: Optional[UtilisateurModele] = None,
) -> UtilisateurModele:
    m = modele_existant or UtilisateurModele()
    m.id_utilisateur    = d.id_utilisateur
    m.email             = d.email
    m.nom               = d.nom
    m.mot_de_passe_hash = d.mot_de_passe_hash
    m.role              = RoleEnum(d.role.value)
    m.actif             = d.actif
    return m


class SQLAlchemyUtilisateurRepository(IUtilisateurRepository):
    """Implémentation concrète de IUtilisateurRepository."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def sauvegarder(self, utilisateur: UtilisateurDomaine) -> UtilisateurDomaine:
        """Upsert par id_utilisateur."""
        modele_existant = await self._db.get(UtilisateurModele, utilisateur.id_utilisateur)
        modele = _domaine_vers_modele(utilisateur, modele_existant)
        if not modele_existant:
            self._db.add(modele)
        await self._db.flush()
        return _modele_vers_domaine(modele)

    async def trouver_par_id(self, id_utilisateur: str) -> Optional[UtilisateurDomaine]:
        modele = await self._db.get(UtilisateurModele, id_utilisateur)
        return _modele_vers_domaine(modele) if modele else None

    async def trouver_par_email(self, email: str) -> Optional[UtilisateurDomaine]:
        stmt = select(UtilisateurModele).where(UtilisateurModele.email == email)
        modele = (await self._db.execute(stmt)).scalar_one_or_none()
        return _modele_vers_domaine(modele) if modele else None

    async def lister_tous(self) -> List[UtilisateurDomaine]:
        stmt = select(UtilisateurModele).order_by(UtilisateurModele.nom)
        modeles = (await self._db.execute(stmt)).scalars().all()
        return [_modele_vers_domaine(m) for m in modeles]
