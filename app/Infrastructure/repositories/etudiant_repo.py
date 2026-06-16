#implémente IEtudiantRepository


#  RÔLE : Implémenter IEtudiantRepository et ISpecialiteRepository
#         avec de vraies requêtes SQL via SQLAlchemy.
#
#  ANALOGIE : Le Domaine dit "je veux trouver_par_id()"
#  Ce fichier répond : "voici le vrai SELECT SQL derrière."
# ============================================================

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.Infrastructure.database.models import (
    Etudiant   as EtudiantModele,
    Specialite as SpecialiteModele,
)
from app.Domain.interfaces import IEtudiantRepository, ISpecialiteRepository
from app.Domain.entities import EtudiantDomaine, SpecialiteDomaine
from app.Infrastructure.database.mappers import (
    etudiant_modele_vers_domaine, etudiant_domaine_vers_modele,
    specialite_modele_vers_domaine, specialite_domaine_vers_modele,
)


class SQLAlchemyEtudiantRepository(IEtudiantRepository):
    """
    Implémentation concrète de IEtudiantRepository.
    Chaque méthode = une vraie requête SQL vers PostgreSQL.
    """

    def __init__(self, db: AsyncSession):
        # Session partagée avec tous les repos de la même requête HTTP
        self._db = db

    async def sauvegarder(self, etudiant: EtudiantDomaine) -> EtudiantDomaine:
        """INSERT ou UPDATE selon si l'étudiant existe déjà (upsert)."""
        # self._db.get() = SELECT WHERE id = ... (recherche par clé primaire)
        modele_existant = await self._db.get(EtudiantModele, etudiant.id_etudiant)
        if modele_existant:
            modele = etudiant_domaine_vers_modele(etudiant, modele_existant)
        else:
            modele = etudiant_domaine_vers_modele(etudiant)
            self._db.add(modele)   # Prépare l'INSERT
        await self._db.flush()     # Envoie le SQL (sans fermer la transaction)
        return etudiant_modele_vers_domaine(modele)

    async def trouver_par_id(self, id_etudiant: str) -> Optional[EtudiantDomaine]:
        """SELECT * FROM etudiants WHERE id_etudiant = '...' """
        modele = await self._db.get(EtudiantModele, id_etudiant)
        return etudiant_modele_vers_domaine(modele) if modele else None

    async def trouver_par_matricule(self, matricule: str) -> Optional[EtudiantDomaine]:
        """SELECT * FROM etudiants WHERE matricule = '...' """
        stmt = select(EtudiantModele).where(EtudiantModele.matricule == matricule)
        modele = (await self._db.execute(stmt)).scalar_one_or_none()
        return etudiant_modele_vers_domaine(modele) if modele else None

    async def lister_tous(
        self,
        niveau: Optional[int] = None,
        id_specialite: Optional[str] = None,
        annee_academique: Optional[str] = None,
    ) -> List[EtudiantDomaine]:
        """SELECT * FROM etudiants WHERE <filtres> ORDER BY nom, prenom"""
        stmt = select(EtudiantModele)
        conditions = []
        if niveau is not None:
            conditions.append(EtudiantModele.niveau == niveau)
        if id_specialite:
            conditions.append(EtudiantModele.id_specialite == id_specialite)
        if annee_academique:
            conditions.append(EtudiantModele.annee_academique == annee_academique)
        if conditions:
            stmt = stmt.where(and_(*conditions))  # and_() = AND en SQL
        stmt = stmt.order_by(EtudiantModele.nom, EtudiantModele.prenom)
        modeles = (await self._db.execute(stmt)).scalars().all()
        return [etudiant_modele_vers_domaine(m) for m in modeles]

    async def supprimer(self, id_etudiant: str) -> bool:
        """DELETE FROM etudiants WHERE id_etudiant = '...' """
        modele = await self._db.get(EtudiantModele, id_etudiant)
        if not modele:
            return False
        await self._db.delete(modele)
        await self._db.flush()
        return True

    async def existe(self, id_etudiant: str) -> bool:
        """Vérifie l'existence sans tout charger."""
        return await self._db.get(EtudiantModele, id_etudiant) is not None


class SQLAlchemySpecialiteRepository(ISpecialiteRepository):
    """Implémentation concrète de ISpecialiteRepository."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def sauvegarder(self, specialite: SpecialiteDomaine) -> SpecialiteDomaine:
        existant = await self._db.get(SpecialiteModele, specialite.id_specialite)
        if existant:
            modele = specialite_domaine_vers_modele(specialite, existant)
        else:
            modele = specialite_domaine_vers_modele(specialite)
            self._db.add(modele)
        await self._db.flush()
        return specialite_modele_vers_domaine(modele)

    async def trouver_par_id(self, id_specialite: str) -> Optional[SpecialiteDomaine]:
        modele = await self._db.get(SpecialiteModele, id_specialite)
        return specialite_modele_vers_domaine(modele) if modele else None

    async def lister_toutes(self, niveau: Optional[int] = None) -> List[SpecialiteDomaine]:
        stmt = select(SpecialiteModele)
        if niveau is not None:
            stmt = stmt.where(SpecialiteModele.niveau == niveau)
        stmt = stmt.order_by(SpecialiteModele.niveau, SpecialiteModele.code)
        modeles = (await self._db.execute(stmt)).scalars().all()
        return [specialite_modele_vers_domaine(m) for m in modeles]

    async def sauvegarder_toutes(self, specialites: List[SpecialiteDomaine]) -> List[SpecialiteDomaine]:
        return [await self.sauvegarder(sp) for sp in specialites]
