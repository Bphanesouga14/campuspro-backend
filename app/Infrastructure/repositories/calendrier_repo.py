#Repository pour le calendrier académique des niveaux

# ============================================================
#  FICHIER : app/Infrastructure/repositories/calendrier_repo.py
#
#  RÔLE : Lire/écrire la table "calendrier_niveaux".
#
#  C'est une table de RÉFÉRENCE pure (pas de règles métier
#  complexes), donc on travaille directement avec le modèle
#  SQLAlchemy sans passer par une entité Domaine dédiée —
#  contrairement à Etudiant/Paiement qui ont des règles métier.
#
#  COUCHE : Infrastructure
# ============================================================

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.database.models import CalendrierNiveau


class SQLAlchemyCalendrierRepository:
    """Repository concret pour le calendrier académique des niveaux."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def lister_tous(self) -> List[CalendrierNiveau]:
        """Retourne toutes les lignes du calendrier, triées par niveau."""
        stmt = select(CalendrierNiveau).order_by(CalendrierNiveau.niveau)
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def trouver_par_niveau(self, niveau: int) -> Optional[CalendrierNiveau]:
        stmt = select(CalendrierNiveau).where(CalendrierNiveau.niveau == niveau)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def sauvegarder(
        self,
        niveau: int,
        groupe: str,
        demarrage_academique: str,
        tranche_1_limite: str,
        tranche_2_limite: str,
        tranche_3_limite: str,
        condition_demarrage: str,
        mois_debut: str,
        mois_fin: str,
    ) -> CalendrierNiveau:
        """Upsert par niveau (utilisé par l'import Excel)."""
        existant = await self.trouver_par_niveau(niveau)
        cible = existant or CalendrierNiveau(niveau=niveau)

        cible.groupe               = groupe
        cible.demarrage_academique = demarrage_academique
        cible.tranche_1_limite     = tranche_1_limite
        cible.tranche_2_limite     = tranche_2_limite
        cible.tranche_3_limite     = tranche_3_limite
        cible.condition_demarrage  = condition_demarrage
        cible.mois_debut           = mois_debut
        cible.mois_fin             = mois_fin

        if not existant:
            self._db.add(cible)

        await self._db.flush()
        return cible
