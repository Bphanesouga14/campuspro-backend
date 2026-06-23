#Cas d'usage : Tableau de bord (statistiques globales)

# ============================================================
#  FICHIER : app/Application/use_cases/dashboard_use_case.py
#
#  RÔLE : Calculer les statistiques globales de l'établissement
#         pour la direction (vue d'ensemble financière).
#
#  COUCHE : Application
# ============================================================

from app.Domain.interfaces import IEtudiantRepository, IPaiementRepository, ISpecialiteRepository
from app.Domain.value_objects import StatutPaiement
from app.Application.DTOs.schemas import TableauDeBordDTO


class TableauDeBordUseCase:
    """
    Calcule les indicateurs clés pour le tableau de bord de la direction :
    nombre d'étudiants, montants attendus/versés/restants, taux de
    recouvrement, nombre d'étudiants à jour / en retard.
    """

    def __init__(
        self,
        etudiant_repo:   IEtudiantRepository,
        paiement_repo:   IPaiementRepository,
        specialite_repo: ISpecialiteRepository,
    ):
        self._etudiant_repo   = etudiant_repo
        self._paiement_repo   = paiement_repo
        self._specialite_repo = specialite_repo

    async def executer(self) -> TableauDeBordDTO:
        etudiants    = await self._etudiant_repo.lister_tous()
        specialites  = await self._specialite_repo.lister_toutes()
        en_retard    = await self._paiement_repo.lister_en_retard()

        total_attendu = 0.0
        total_verse   = 0.0
        nb_a_jour     = 0
        nb_en_retard  = 0

        for etudiant in etudiants:
            paiements = await self._paiement_repo.lister_par_etudiant(etudiant.id_etudiant)
            etudiant.paiements = paiements

            total_attendu += float(etudiant.total_annuel_attendu.valeur)
            total_verse   += float(etudiant.cumul_verse.valeur)

            if etudiant.est_a_jour:
                nb_a_jour += 1
            else:
                nb_en_retard += 1

        total_reste = total_attendu - total_verse
        taux = (total_verse / total_attendu * 100) if total_attendu > 0 else 0.0

        return TableauDeBordDTO(
            nb_etudiants            = len(etudiants),
            total_attendu           = round(total_attendu, 2),
            total_verse             = round(total_verse, 2),
            total_reste             = round(total_reste, 2),
            taux_recouvrement       = round(taux, 2),
            nb_etudiants_a_jour     = nb_a_jour,
            nb_etudiants_en_retard  = nb_en_retard,
            nb_paiements_en_retard  = len(en_retard),
            nb_specialites          = len(specialites),
        )
