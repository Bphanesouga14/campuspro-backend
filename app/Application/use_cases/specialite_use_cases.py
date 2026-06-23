#Cas d'usage : Spécialités (CRUD)

# ============================================================
#  FICHIER : app/Application/use_cases/specialite_use_cases.py
#
#  RÔLE : Cas d'usage liés aux spécialités/filières.
#
#  Avant cet ajout, les spécialités ne pouvaient être créées
#  que via l'import Excel — aucune route API ne permettait de
#  les lister, consulter ou créer individuellement.
#
#  COUCHE : Application
# ============================================================

from typing import List, Optional

from app.Domain.entities import SpecialiteDomaine
from app.Domain.value_objects import Montant, Niveau
from app.Domain.interfaces import ISpecialiteRepository
from app.Domain.exceptions import SpecialiteIntrouvableError
from app.Application.DTOs.schemas import SpecialiteCreerDTO, SpecialiteReponseDTO


def _specialite_vers_dto(s: SpecialiteDomaine) -> SpecialiteReponseDTO:
    """Convertit une entité Domaine SpecialiteDomaine en DTO de réponse."""
    return SpecialiteReponseDTO(
        id_specialite     = s.id_specialite,
        code              = s.code,
        nom_specialite    = s.nom_specialite,
        departement       = s.departement,
        niveau            = s.niveau.value,
        duree_ans         = s.duree_ans,
        annee_academique  = s.annee_academique,
        tranche_1         = float(s.tranche_1.valeur),
        date_limite_t1    = s.date_limite_t1,
        tranche_2         = float(s.tranche_2.valeur),
        date_limite_t2    = s.date_limite_t2,
        tranche_3         = float(s.tranche_3.valeur),
        date_limite_t3    = s.date_limite_t3,
        total             = float(s.total.valeur),
        groupe_academique = s.groupe_academique,
        mois_demarrage    = s.mois_demarrage,
    )


class ListerSpecialitesUseCase:
    """Liste toutes les spécialités, avec filtre optionnel par niveau."""

    def __init__(self, specialite_repo: ISpecialiteRepository):
        self._specialite_repo = specialite_repo

    async def executer(self, niveau: Optional[int] = None) -> List[SpecialiteReponseDTO]:
        specialites = await self._specialite_repo.lister_toutes(niveau=niveau)
        return [_specialite_vers_dto(s) for s in specialites]


class ObtenirSpecialiteUseCase:
    """Récupère le détail d'une spécialité par son ID."""

    def __init__(self, specialite_repo: ISpecialiteRepository):
        self._specialite_repo = specialite_repo

    async def executer(self, id_specialite: str) -> SpecialiteReponseDTO:
        specialite = await self._specialite_repo.trouver_par_id(id_specialite)
        if not specialite:
            raise SpecialiteIntrouvableError(id_specialite)
        return _specialite_vers_dto(specialite)


class CreerOuModifierSpecialiteUseCase:
    """
    Crée une nouvelle spécialité ou met à jour une spécialité existante
    (upsert par id_specialite — cohérent avec le comportement de l'import Excel).
    """

    def __init__(self, specialite_repo: ISpecialiteRepository):
        self._specialite_repo = specialite_repo

    async def executer(self, dto: SpecialiteCreerDTO) -> SpecialiteReponseDTO:
        specialite = SpecialiteDomaine(
            id_specialite    = dto.id_specialite,
            code             = dto.code,
            nom_specialite   = dto.nom_specialite,
            departement      = dto.departement,
            niveau           = Niveau(dto.niveau),
            duree_ans        = dto.duree_ans,
            annee_academique = dto.annee_academique,
            tranche_1        = Montant(dto.tranche_1),
            date_limite_t1   = dto.date_limite_t1,
            tranche_2        = Montant(dto.tranche_2),
            date_limite_t2   = dto.date_limite_t2,
            tranche_3        = Montant(dto.tranche_3),
            date_limite_t3   = dto.date_limite_t3,
        )
        sauvegardee = await self._specialite_repo.sauvegarder(specialite)
        return _specialite_vers_dto(sauvegardee)
