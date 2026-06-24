#implémente ISpecialiteRepository

# ============================================================
#  FICHIER : app/infrastructure/repositories/specialite_repo.py
#
#  RÔLE : Implémentation concrète de ISpecialiteRepository.
#         Toutes les opérations SQL sur la table "specialites".
#
#  COUCHE : Infrastructure
#  IMPLÉMENTE : app/domain/interfaces.py → ISpecialiteRepository
# ============================================================

from typing import List, Optional

# select = construire une requête SELECT en Python (pas en SQL brut)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Le modèle SQLAlchemy (table en base)
from app.Infrastructure.database.models import Specialite as SpecialiteModel
# Les mappeurs (traducteurs domaine ↔ SQLAlchemy)
from app.Infrastructure.repositories.mappers import (
    specialite_model_vers_domaine,
    specialite_domaine_vers_model,
)
# La classe mère commune
from app.Infrastructure.repositories.base_repo import BaseRepository
# Le contrat du Domaine à respecter
from app.Domain.interfaces import ISpecialiteRepository
from app.Domain.entities import SpecialiteDomaine


class SQLAlchemySpecialiteRepository(BaseRepository, ISpecialiteRepository):
    """
    Repository concret pour les spécialités.

    Hérite de :
    - BaseRepository   → fournit self._session
    - ISpecialiteRepository → impose les méthodes à implémenter

    Python dira une erreur si une méthode @abstractmethod
    n'est pas implémentée ici.
    """

    async def sauvegarder(self, specialite: SpecialiteDomaine) -> SpecialiteDomaine:
        """
        INSERT si nouvelle spécialité, UPDATE si elle existe déjà.
        C'est ce qu'on appelle un "upsert".
        """
        # Chercher si elle existe déjà en base
        # self._session.get(Modèle, clé_primaire) → SELECT rapide par PK
        model_existant = await self._session.get(
            SpecialiteModel,
            specialite.id_specialite
        )

        # Le mappeur crée ou met à jour le modèle SQLAlchemy
        model = specialite_domaine_vers_model(specialite, model_existant)

        if not model_existant:
            # Nouvelle spécialité → on l'ajoute à la session
            # La session va générer un INSERT lors du prochain flush/commit
            self._session.add(model)

        # flush() envoie les changements à PostgreSQL SANS les valider.
        # Utile pour obtenir les valeurs générées (ex: ID auto-incrémenté).
        # Le commit() final viendra depuis get_db() dans session.py.
        await self._session.flush()

        # Retourner l'entité domaine reconstruite depuis le modèle sauvegardé
        return specialite_model_vers_domaine(model)

    async def trouver_par_id(self, id_specialite: str) -> Optional[SpecialiteDomaine]:
        """
        Cherche une spécialité par son ID.
        Retourne None si elle n'existe pas (pas d'exception).
        """
        model = await self._session.get(SpecialiteModel, id_specialite)
        if not model:
            return None
        return specialite_model_vers_domaine(model)

    async def lister_toutes(self, niveau: Optional[int] = None) -> List[SpecialiteDomaine]:
        """
        Retourne toutes les spécialités, avec filtre optionnel par niveau.

        Équivalent SQL :
            SELECT * FROM specialites [WHERE niveau = ?]
            ORDER BY niveau, code
        """
        # select(SpecialiteModel) = SELECT * FROM specialites
        stmt = select(SpecialiteModel)

        # Si un filtre niveau est fourni → on ajoute WHERE
        if niveau is not None:
            stmt = stmt.where(SpecialiteModel.niveau == niveau)

        # ORDER BY niveau ASC, code ASC
        stmt = stmt.order_by(SpecialiteModel.niveau, SpecialiteModel.code)

        # execute() envoie la requête à PostgreSQL
        result = await self._session.execute(stmt)

        # scalars() → extrait les objets Python depuis le résultat SQL
        # all()     → récupère tous les résultats d'un coup (liste)
        modeles = result.scalars().all()

        # Convertir chaque modèle en entité domaine
        return [specialite_model_vers_domaine(m) for m in modeles]

    async def sauvegarder_toutes(
        self, specialites: List[SpecialiteDomaine]
    ) -> List[SpecialiteDomaine]:
        """
        Sauvegarde une liste de spécialités en une opération.
        Utilisé lors de l'import Excel pour traiter toutes les lignes.
        """
        resultats = []
        for sp in specialites:
            sauvegardee = await self.sauvegarder(sp)
            resultats.append(sauvegardee)
        return resultats
