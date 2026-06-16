#implémente IPaiementRepository

# ============================================================
#  FICHIER : app/infrastructure/repositories/paiement_repo.py
#
#  RÔLE : Implémentation concrète de IPaiementRepository.
#         Toutes les opérations SQL sur la table "paiements".
#
#  COUCHE : Infrastructure
#  IMPLÉMENTE : app/domain/interfaces.py → IPaiementRepository
# ============================================================

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.database.models import (
    Paiement as PaiementModel,
    StatutPaiementEnum,
)
from app.Infrastructure.repositories.mappers import (
    paiement_model_vers_domaine,
    paiement_domaine_vers_model,
)
from app.Infrastructure.repositories.base_repo import BaseRepository
from app.Domain.interfaces import IPaiementRepository
from app.Domain.entities import PaiementDomaine


class SQLAlchemyPaiementRepository(BaseRepository, IPaiementRepository):
    """
    Repository concret pour les paiements.
    Implémente toutes les méthodes de IPaiementRepository.
    """

    async def sauvegarder(self, paiement: PaiementDomaine) -> PaiementDomaine:
        """
        Crée ou met à jour un paiement (upsert par id_paiement).

        IMPORTANT : C'est cette méthode qui est appelée après chaque versement.
        Elle sauvegarde le nouveau montant_paye et le nouveau statut.
        """
        model_existant = await self._session.get(
            PaiementModel,
            paiement.id_paiement
        )
        model = paiement_domaine_vers_model(paiement, model_existant)

        if not model_existant:
            self._session.add(model)

        await self._session.flush()
        return paiement_model_vers_domaine(model)

    async def trouver_par_id(self, id_paiement: str) -> Optional[PaiementDomaine]:
        """
        SELECT * FROM paiements WHERE id_paiement = ?
        """
        model = await self._session.get(PaiementModel, id_paiement)
        if not model:
            return None
        return paiement_model_vers_domaine(model)

    async def lister_par_etudiant(self, id_etudiant: str) -> List[PaiementDomaine]:
        """
        SELECT * FROM paiements
        WHERE id_etudiant = ?
        ORDER BY numero_tranche ASC

        Retourne les 3 tranches d'un étudiant triées dans l'ordre (1, 2, 3).
        C'est cette méthode qu'on appelle pour calculer
        le cumul_verse et le reste_global.
        """
        stmt = (
            select(PaiementModel)
            .where(PaiementModel.id_etudiant == id_etudiant)
            # On trie par numéro de tranche : 1 d'abord, puis 2, puis 3
            .order_by(PaiementModel.numero_tranche)
        )
        result  = await self._session.execute(stmt)
        modeles = result.scalars().all()

        return [paiement_model_vers_domaine(m) for m in modeles]

    async def lister_en_retard(self) -> List[PaiementDomaine]:
        """
        SELECT * FROM paiements
        WHERE statut = 'EN RETARD'
        ORDER BY date_limite ASC

        Retourne tous les paiements en retard, du plus ancien au plus récent.
        Utilisé pour générer la liste des relances à envoyer.
        """
        stmt = (
            select(PaiementModel)
            .where(PaiementModel.statut == StatutPaiementEnum.EN_RETARD)
            # On trie par date limite : les plus urgents en premier
            .order_by(PaiementModel.date_limite)
        )
        result  = await self._session.execute(stmt)
        modeles = result.scalars().all()

        return [paiement_model_vers_domaine(m) for m in modeles]

    async def sauvegarder_tous(
        self, paiements: List[PaiementDomaine]
    ) -> List[PaiementDomaine]:
        """
        Sauvegarde une liste de paiements en une opération.
        Utilisé lors de l'import Excel.
        """
        resultats = []
        for p in paiements:
            sauvegarde = await self.sauvegarder(p)
            resultats.append(sauvegarde)
        return resultats
