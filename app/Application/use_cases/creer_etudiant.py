

#  RÔLE : Orchestrer la création d'un nouvel étudiant.
#
#  CE QUE CE CAS D'USAGE FAIT, DANS L'ORDRE :
#  1. Vérifie que le matricule n'existe pas déjà
#  2. Construit l'entité domaine EtudiantDomaine
#  3. Sauvegarde via le Repository
#  4. Retourne le DTO de sortie
#
#  CE QU'IL NE FAIT PAS :
#  - Pas de SQL direct (c'est le Repository qui s'en charge)
#  - Pas de validation HTTP (c'est Pydantic dans les schemas)
#  - Pas de règles métier complexes (c'est l'entité Domaine)
#
#  COUCHE : Application
# ============================================================

from decimal import Decimal
from app.Application.use_cases.etudiant_use_cases import _domaine_vers_reponse
from app.Domain.entities     import EtudiantDomaine
from app.Domain.interfaces   import IEtudiantRepository, IPaiementRepository
from app.Domain.value_objects import (
    Matricule, Email, Telephone, Sexe, LienParent, Niveau
)
from app.Domain.exceptions import (
    EtudiantDejaExistantError,
    SpecialiteIntrouvableError,
)
from app.Domain.interfaces   import ISpecialiteRepository
from app.Application.DTOs.schemas import EtudiantCreerDTO, EtudiantIn, EtudiantOut, EtudiantReponseDTO


class CreerEtudiantUseCase:
    def __init__(
        self,
        etudiant_repo: IEtudiantRepository,
        specialite_repo: ISpecialiteRepository,  # ← ajouter
        paiement_repo: IPaiementRepository,       # ← ajouter
    ):
        self._etudiant_repo    = etudiant_repo
        self._specialite_repo  = specialite_repo
        self._paiement_repo    = paiement_repo

    async def executer(self, dto: EtudiantCreerDTO) -> EtudiantReponseDTO:
        # ── Étape 1 : Vérifier que le matricule est unique ───
        existant = await self._etudiant_repo.trouver_par_matricule(dto.matricule)
        if existant:
            raise EtudiantDejaExistantError(dto.matricule)

        # ── Étape 2 : Construire l'entité Domaine ────────────
        etudiant = EtudiantDomaine(
            id_etudiant = dto.id_etudiant,
            # ... reste des champs existants inchangés ...
        )

        # ── Étape 3 : Sauvegarder en base ───────────────────
        etudiant_sauvegarde = await self._etudiant_repo.sauvegarder(etudiant)

        # ── Étape 4 : Générer automatiquement les 3 tranches ─
        # basées sur les montants définis dans la Specialite
        specialite = await self._specialite_repo.trouver_par_id(dto.id_specialite)
        if specialite:
            from app.Domain.entities import PaiementDomaine
            from app.Domain.value_objects import Montant, StatutPaiement
            import uuid

            tranches = [
                (1, specialite.tranche_1, specialite.date_limite_t1),
                (2, specialite.tranche_2, specialite.date_limite_t2),
                (3, specialite.tranche_3, specialite.date_limite_t3),
            ]
            for numero, montant, date_limite in tranches:
                paiement = PaiementDomaine(
                    id_paiement     = f"PAY-{uuid.uuid4().hex[:8].upper()}",
                    id_etudiant     = dto.id_etudiant,
                    id_specialite   = dto.id_specialite,
                    niveau          = dto.niveau,
                    numero_tranche  = numero,
                    montant_attendu = Montant(valeur=montant),
                    montant_paye    = Montant(valeur=0),
                    date_limite     = date_limite,
                    statut          = StatutPaiement.EN_ATTENTE,
                )
                await self._paiement_repo.sauvegarder(paiement)

        # ── Étape 5 : Retourner le DTO de réponse ───────────
        return _domaine_vers_reponse(etudiant_sauvegarde)

    def _vers_dto(self, etudiant: EtudiantDomaine) -> EtudiantOut:
        """
        Convertit une entité domaine en DTO de sortie.
        Méthode privée utilitaire.
        """
        return EtudiantOut(
            id_etudiant        = etudiant.id_etudiant,
            matricule          = str(etudiant.matricule),
            nom                = etudiant.nom,
            prenom             = etudiant.prenom,
            nom_complet        = etudiant.nom_complet,
            date_naissance     = etudiant.date_naissance,
            sexe               = etudiant.sexe.value,
            id_specialite      = etudiant.id_specialite,
            code_specialite    = etudiant.code_specialite,
            niveau             = etudiant.niveau.value,
            annee_academique   = etudiant.annee_academique,
            email_etudiant     = str(etudiant.email_etudiant) if etudiant.email_etudiant else None,
            telephone_etudiant = str(etudiant.telephone_etudiant) if etudiant.telephone_etudiant else None,
            nom_parent         = etudiant.nom_parent,
            prenom_parent      = etudiant.prenom_parent,
            lien_parent        = etudiant.lien_parent.value if etudiant.lien_parent else "",
            telephone_parent   = str(etudiant.telephone_parent) if etudiant.telephone_parent else "",
            email_parent       = str(etudiant.email_parent) if etudiant.email_parent else None,
            cumul_verse        = etudiant.cumul_verse.valeur,
            reste_global       = etudiant.reste_global.valeur,
            est_a_jour         = etudiant.est_a_jour,
        )
