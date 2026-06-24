

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
from app.Domain.entities     import EtudiantDomaine
from app.Domain.interfaces   import IEtudiantRepository
from app.Domain.value_objects import (
    Matricule, Email, Telephone, Sexe, LienParent, Niveau
)
from app.Domain.exceptions import (
    EtudiantDejaExistantError,
    SpecialiteIntrouvableError,
)
from app.Domain.interfaces   import ISpecialiteRepository
from app.Application.DTOs.schemas import EtudiantIn, EtudiantOut


class CreerEtudiantUseCase:
    """
    Cas d'usage : Créer un nouvel étudiant.

    On injecte les dépendances dans le constructeur.
    "Injecter" = passer en paramètre au lieu de créer ici.
    Ainsi, on peut facilement remplacer le vrai Repository
    par un faux (mock) lors des tests.
    """

    def __init__(
        self,
        etudiant_repo:   IEtudiantRepository,
        specialite_repo: ISpecialiteRepository,
    ):
        # On stocke les repositories comme attributs privés
        # Le "_" devant le nom indique que c'est privé (convention Python)
        self._etudiant_repo   = etudiant_repo
        self._specialite_repo = specialite_repo

    async def executer(self, donnees: EtudiantIn) -> EtudiantOut:
        """
        Point d'entrée du cas d'usage.
        Reçoit un DTO "In", retourne un DTO "Out".

        async def = méthode asynchrone (nécessaire pour les
        opérations d'accès à la base de données).
        """

        # ── Étape 1 : Vérifier que le matricule est unique ───
        # On appelle le repository pour chercher en base
        existant = await self._etudiant_repo.trouver_par_matricule(
            donnees.matricule
        )
        if existant:
            # Si un étudiant existe déjà avec ce matricule → erreur métier
            raise EtudiantDejaExistantError(donnees.matricule)

        # ── Étape 2 : Vérifier que la spécialité existe ──────
        specialite = await self._specialite_repo.trouver_par_id(
            donnees.id_specialite
        )
        if not specialite:
            raise SpecialiteIntrouvableError(donnees.id_specialite)

        # ── Étape 3 : Construire l'entité domaine ────────────
        # On convertit les strings du DTO en Value Objects du domaine
        # C'est ici que la validation métier (format, règles) s'applique

        matricule = Matricule(donnees.matricule)
        # Si le format est invalide → Matricule lève ValueError

        sexe = Sexe.MASCULIN if donnees.sexe == "M" else Sexe.FEMININ

        niveau = Niveau(donnees.niveau)
        # Niveau(6) lèverait une erreur car 6 n'est pas dans l'Enum

        # Construire les Value Objects optionnels
        email_etudiant = (
            Email(donnees.email_etudiant)
            if donnees.email_etudiant else None
        )
        tel_etudiant = (
            Telephone(donnees.telephone_etudiant)
            if donnees.telephone_etudiant else None
        )
        tel_parent = Telephone(donnees.telephone_parent)
        email_parent = (
            Email(donnees.email_parent)
            if donnees.email_parent else None
        )

        # Convertir le lien parent en Enum
        lien_map = {"Père": LienParent.PERE, "Mère": LienParent.MERE, "Tuteur": LienParent.TUTEUR}
        lien = lien_map.get(donnees.lien_parent, LienParent.TUTEUR)

        # Construire l'entité domaine complète
        etudiant = EtudiantDomaine(
            id_etudiant        = donnees.id_etudiant,
            matricule          = matricule,
            nom                = donnees.nom.upper(),    # Convention : NOM en majuscules
            prenom             = donnees.prenom.capitalize(),
            date_naissance     = donnees.date_naissance,
            sexe               = sexe,
            id_specialite      = donnees.id_specialite,
            code_specialite    = donnees.code_specialite,
            niveau             = niveau,
            annee_academique   = donnees.annee_academique,
            email_etudiant     = email_etudiant,
            telephone_etudiant = tel_etudiant,
            nom_parent         = donnees.nom_parent.upper(),
            prenom_parent      = donnees.prenom_parent.capitalize(),
            lien_parent        = lien,
            telephone_parent   = tel_parent,
            email_parent       = email_parent,
            paiements          = [],   # Pas de paiements à la création
        )

        # ── Étape 4 : Sauvegarder via le Repository ──────────
        # On ne sait pas si c'est PostgreSQL ou autre chose.
        # On appelle juste le contrat défini dans les interfaces.
        etudiant_sauvegarde = await self._etudiant_repo.sauvegarder(etudiant)

        # ── Étape 5 : Construire et retourner le DTO de sortie
        return self._vers_dto(etudiant_sauvegarde)

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
