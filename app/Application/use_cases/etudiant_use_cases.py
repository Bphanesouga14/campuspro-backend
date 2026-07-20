

#  RÔLE : Cas d'usage liés aux étudiants.
#
#  UN CAS D'USAGE = UNE ACTION UTILISATEUR PRÉCISE.
#  Chaque classe répond à une seule question :
#  "Que se passe-t-il quand l'utilisateur fait X ?"
#
#  RÈGLE D'OR : Un use case NE CONTIENT PAS de SQL.
#  Il parle aux interfaces (IEtudiantRepository...)
#  et laisse l'Infrastructure gérer le vrai stockage.
#
#  COUCHE : Application
#  DÉPEND DE : Domaine (entités, interfaces, exceptions)
#  NE CONNAÎT PAS : SQLAlchemy, FastAPI, openpyxl
# ============================================================

from decimal import Decimal
from typing import List, Optional

# On importe les entités et value objects du Domaine
from app.Domain.entities import EtudiantDomaine
from app.Domain.value_objects import (
    Matricule, Montant, Email, Telephone,
    Sexe, LienParent, Niveau
)

# On importe les INTERFACES — jamais les repositories directement
from app.Domain.interfaces import (
    IEtudiantRepository,
    IPaiementRepository,
    IQRCodeRepository,
    ISpecialiteRepository,
)

# On importe les exceptions du Domaine
from app.Domain.exceptions import (
    EtudiantDejaExistantError,
    EtudiantIntrouvableError,
)

# On importe les DTOs de la couche Application
from app.Application.DTOs.schemas import (
    EtudiantCreerDTO,
    EtudiantModifierDTO,
    EtudiantReponseDTO,
    EtudiantDetailDTO,
    PaiementReponseDTO,
    QRCodeReponseDTO,
    HistoriquePaiementsDTO,
)


# ── Fonction utilitaire ──────────────────────────────────────
# Convertit une EtudiantDomaine en EtudiantReponseDTO
# (traduit l'objet domaine en données JSON-compatibles)
def _domaine_vers_reponse(etudiant: EtudiantDomaine) -> EtudiantReponseDTO:
    """
    Traduit une entité Domaine en DTO de réponse.
    C'est ici qu'on "aplatit" les Value Objects en types simples.
    Exemple : Matricule("MAT-2024-INFO-001") → "MAT-2024-INFO-001"
    """
    return EtudiantReponseDTO(
        id_etudiant          = etudiant.id_etudiant,
        # str(etudiant.matricule) appelle __str__ du Value Object
        matricule            = str(etudiant.matricule),
        nom                  = etudiant.nom,
        prenom               = etudiant.prenom,
        # Propriété calculée de l'entité
        nom_complet          = etudiant.nom_complet,
        date_naissance       = etudiant.date_naissance,
        sexe                 = etudiant.sexe.value,        # "M" ou "F"
        id_specialite        = etudiant.id_specialite,
        code_specialite      = etudiant.code_specialite,
        niveau               = etudiant.niveau.value,      # 1, 2, 3...
        annee_academique     = etudiant.annee_academique,
        # str(email) ou None si absent
        email_etudiant       = str(etudiant.email_etudiant) if etudiant.email_etudiant else None,
        telephone_etudiant   = str(etudiant.telephone_etudiant) if etudiant.telephone_etudiant else None,
        nom_parent           = etudiant.nom_parent,
        prenom_parent        = etudiant.prenom_parent,
        lien_parent          = etudiant.lien_parent.value if etudiant.lien_parent else "",
        telephone_parent     = str(etudiant.telephone_parent) if etudiant.telephone_parent else "",
        email_parent         = str(etudiant.email_parent) if etudiant.email_parent else None,
        # float() convertit le Montant en nombre simple pour JSON
        cumul_verse          = float(etudiant.cumul_verse.valeur),
        total_annuel_attendu = float(etudiant.total_annuel_attendu.valeur),
        reste_global         = float(etudiant.reste_global.valeur),
        est_a_jour           = etudiant.est_a_jour,
        photo                = getattr(etudiant, "photo", None),   # ← AJOUTER
    )


# ============================================================
#  CAS D'USAGE 1 : CreerEtudiantUseCase
# ============================================================
class CreerEtudiantUseCase:
    """
    Gère la création d'un nouvel étudiant.

    SCÉNARIO :
    1. Le secrétaire remplit le formulaire d'inscription
    2. L'API reçoit les données (EtudiantCreerDTO)
    3. Ce use case :
       a. Vérifie que le matricule n'est pas déjà pris
       b. Construit l'entité Domaine (avec validation)
       c. Sauvegarde en base via le repository
       d. Retourne le DTO de réponse
    """

    def __init__(
            self,
            etudiant_repo: IEtudiantRepository,
            specialite_repo: ISpecialiteRepository,
            paiement_repo: IPaiementRepository,
        ):
            self._etudiant_repo   = etudiant_repo
            self._specialite_repo = specialite_repo
            self._paiement_repo   = paiement_repo

    async def executer(self, dto: EtudiantCreerDTO) -> EtudiantReponseDTO:
        """
        Point d'entrée du use case.
        Reçoit le DTO → applique la logique → retourne le résultat.
        'async' car les opérations de base de données sont asynchrones.
        """

        # ── Étape 1 : Vérifier que le matricule est unique ───
        # On demande au repository si cet étudiant existe déjà
        existant = await self._etudiant_repo.trouver_par_matricule(dto.matricule)
        if existant:
            # Si oui → on lève une exception métier du Domaine
            raise EtudiantDejaExistantError(dto.matricule)

        # ── Étape 2 : Construire l'entité Domaine ───────────
        # On convertit les données brutes (strings du DTO)
        # en objets du Domaine (Value Objects avec validation)
        try:
            etudiant = EtudiantDomaine(
                id_etudiant      = dto.id_etudiant,
                # Matricule() valide le format automatiquement
                # Si invalide → lève ValueError avec message clair
                matricule        = Matricule(dto.matricule),
                nom              = dto.nom.upper(),      # Standardisation : NOM en majuscules
                prenom           = dto.prenom.capitalize(),  # Prénom avec 1ère lettre en maj
                date_naissance   = dto.date_naissance,
                # Sexe("M") → Sexe.MASCULIN
                sexe             = Sexe(dto.sexe),
                id_specialite    = dto.id_specialite,
                code_specialite  = dto.code_specialite,
                # Niveau(1) → Niveau.UN (avec les règles de groupe)
                niveau           = Niveau(dto.niveau),
                annee_academique = dto.annee_academique,
                # Email et Telephone valident leur format
                email_etudiant   = Email(dto.email_etudiant) if dto.email_etudiant else None,
                telephone_etudiant = Telephone(dto.telephone_etudiant) if dto.telephone_etudiant else None,
                nom_parent       = dto.nom_parent.upper(),
                prenom_parent    = dto.prenom_parent.capitalize(),
                lien_parent      = LienParent(dto.lien_parent),
                telephone_parent = Telephone(dto.telephone_parent),
                email_parent     = Email(dto.email_parent) if dto.email_parent else None,
                # Pas de paiements à la création : liste vide
                paiements        = [],
            )
        except ValueError as e:
            # ValueError vient des Value Objects (Matricule, Email, etc.)
            # On le retransmet comme erreur claire
            raise ValueError(f"Données invalides : {e}")

        # ── Étape 3 : Sauvegarder en base ───────────────────
        etudiant_sauvegarde = await self._etudiant_repo.sauvegarder(etudiant)

        # ── Étape 4 : Générer automatiquement les 3 tranches ─
        # basées sur les montants définis dans la Specialite
        # ── Étape 4 : Générer automatiquement les 3 tranches ─
        # ── Étape 4 : Générer automatiquement les 3 tranches ─
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
                    montant_attendu = montant,              # ← déjà un Montant, pas de conversion
                    montant_paye    = Montant(valeur=0),
                    date_limite     = date_limite,
                    statut          = StatutPaiement.EN_ATTENTE,
                )
                await self._paiement_repo.sauvegarder(paiement)

        # ── Étape 5 : Retourner le DTO de réponse ───────────
        return _domaine_vers_reponse(etudiant_sauvegarde)


# ============================================================
#  CAS D'USAGE 2 : TrouverEtudiantUseCase
# ============================================================
class TrouverEtudiantUseCase:
    """
    Récupère le détail complet d'un étudiant avec ses paiements et QR codes.

    SCÉNARIO :
    Le secrétaire clique sur un étudiant dans la liste
    → on charge toutes ses informations + ses paiements + ses QR codes.
    """

    def __init__(
        self,
        etudiant_repo: IEtudiantRepository,
        paiement_repo: IPaiementRepository,
        qr_repo:       IQRCodeRepository,
    ):
        # Ce use case a besoin de 3 repositories différents
        self._etudiant_repo = etudiant_repo
        self._paiement_repo = paiement_repo
        self._qr_repo       = qr_repo

    async def executer(self, id_etudiant: str) -> EtudiantDetailDTO:

        # ── Étape 1 : Charger l'étudiant ────────────────────
        etudiant = await self._etudiant_repo.trouver_par_id(id_etudiant)
        if not etudiant:
            # Étudiant non trouvé → exception métier du Domaine
            raise EtudiantIntrouvableError(id_etudiant)

        # ── Étape 2 : Charger ses paiements ─────────────────
        paiements = await self._paiement_repo.lister_par_etudiant(id_etudiant)
        # On attache les paiements à l'entité pour que
        # cumul_verse et reste_global soient calculés correctement
        etudiant.paiements = paiements

        # ── Étape 3 : Charger ses QR codes ──────────────────
        qr_codes = await self._qr_repo.lister_par_etudiant(id_etudiant)

        # ── Étape 4 : Construire le DTO de détail ───────────
        # On part du DTO de base et on ajoute les listes
        base = _domaine_vers_reponse(etudiant)

        return EtudiantDetailDTO(
            **base.model_dump(),  # Tous les champs de base (nom, matricule, etc.)
            paiements = [
                PaiementReponseDTO(
                    id_paiement          = p.id_paiement,
                    id_etudiant          = p.id_etudiant,
                    id_specialite        = p.id_specialite,
                    niveau               = p.niveau,
                    numero_tranche       = p.numero_tranche,
                    montant_attendu      = float(p.montant_attendu.valeur),
                    montant_paye         = float(p.montant_paye.valeur),
                    reste_a_payer        = float(p.reste_a_payer.valeur),
                    date_paiement        = p.date_paiement,
                    date_limite          = p.date_limite,
                    statut               = p.statut.value,
                    qr_code_genere       = p.qr_code_genere,
                    notif_parent_envoyee = p.notif_envoyee,
                    observations         = p.observations,
                )
                for p in paiements
                # "for p in paiements" = on répète pour chaque paiement
            ],
            qr_codes = [
                QRCodeReponseDTO(
                    id_qrcode       = q.id_qrcode,
                    id_etudiant     = q.id_etudiant,
                    id_specialite   = q.id_specialite,
                    niveau          = q.niveau,
                    date_generation = q.date_generation,
                    valide_jusqua   = q.valide_jusqua,
                    statut          = q.statut.value,
                    est_valide      = q.est_valide,
                    qr_data         = q.qr_data,
                )
                for q in qr_codes
            ],
        )


# ============================================================
#  CAS D'USAGE 3 : ListerEtudiantsUseCase
# ============================================================
class ListerEtudiantsUseCase:
    """
    Liste les étudiants avec des filtres optionnels.

    SCÉNARIO :
    La secrétaire veut voir tous les étudiants de niveau 1
    de l'année 2024-2025 → elle filtre par niveau et année.
    """

    def __init__(
        self,
        etudiant_repo: IEtudiantRepository,
        paiement_repo: IPaiementRepository,
    ):
        self._etudiant_repo = etudiant_repo
        self._paiement_repo = paiement_repo

    async def executer(
        self,
        niveau:           Optional[int] = None,
        id_specialite:    Optional[str] = None,
        annee_academique: Optional[str] = None,
        skip:             int = 0,
        limit:            Optional[int] = None,
    ) -> List[EtudiantReponseDTO]:

        # Demander la liste au repository avec les filtres
        etudiants = await self._etudiant_repo.lister_tous(
            niveau           = niveau,
            id_specialite    = id_specialite,
            annee_academique = annee_academique,
            skip             = skip,
            limit            = limit,
        )

        resultats = []
        for etudiant in etudiants:
            # Pour chaque étudiant, on charge ses paiements
            # afin de calculer cumul_verse et reste_global
            paiements = await self._paiement_repo.lister_par_etudiant(
                etudiant.id_etudiant
            )
            etudiant.paiements = paiements
            resultats.append(_domaine_vers_reponse(etudiant))

        return resultats


# ============================================================
#  CAS D'USAGE 4 : HistoriquePaiementsEtudiantUseCase
# ============================================================
class HistoriquePaiementsEtudiantUseCase:
    """
    Retourne le résumé financier complet d'un étudiant.

    SCÉNARIO :
    Un parent appelle l'école pour demander l'état des paiements
    de son enfant → on lui retourne le cumul versé,
    le reste à payer et le détail tranche par tranche.
    """

    def __init__(
        self,
        etudiant_repo: IEtudiantRepository,
        paiement_repo: IPaiementRepository,
    ):
        self._etudiant_repo = etudiant_repo
        self._paiement_repo = paiement_repo

    async def executer(self, id_etudiant: str) -> HistoriquePaiementsDTO:

        # Vérifier que l'étudiant existe
        etudiant = await self._etudiant_repo.trouver_par_id(id_etudiant)
        if not etudiant:
            raise EtudiantIntrouvableError(id_etudiant)

        # Charger tous ses paiements
        paiements = await self._paiement_repo.lister_par_etudiant(id_etudiant)
        etudiant.paiements = paiements

        return HistoriquePaiementsDTO(
            id_etudiant          = etudiant.id_etudiant,
            nom_complet          = etudiant.nom_complet,
            cumul_verse          = float(etudiant.cumul_verse.valeur),
            total_annuel_attendu = float(etudiant.total_annuel_attendu.valeur),
            reste_global         = float(etudiant.reste_global.valeur),
            est_a_jour           = etudiant.est_a_jour,
            paiements            = [
                PaiementReponseDTO(
                    id_paiement          = p.id_paiement,
                    id_etudiant          = p.id_etudiant,
                    id_specialite        = p.id_specialite,
                    niveau               = p.niveau,
                    numero_tranche       = p.numero_tranche,
                    montant_attendu      = float(p.montant_attendu.valeur),
                    montant_paye         = float(p.montant_paye.valeur),
                    reste_a_payer        = float(p.reste_a_payer.valeur),
                    date_paiement        = p.date_paiement,
                    date_limite          = p.date_limite,
                    statut               = p.statut.value,
                    qr_code_genere       = p.qr_code_genere,
                    notif_parent_envoyee = p.notif_envoyee,
                    observations         = p.observations,
                )
                for p in paiements
            ],
        )


# ============================================================
#  CAS D'USAGE 5 : ModifierEtudiantUseCase
# ============================================================
class ModifierEtudiantUseCase:
    """
    Modifie un étudiant existant.

    SCÉNARIO :
    Une faute de frappe dans le nom, un changement de spécialité,
    une mise à jour du contact parent... Seuls les champs fournis
    dans le DTO sont modifiés ; les autres restent inchangés.
    """

    def __init__(self, etudiant_repo: IEtudiantRepository):
        self._etudiant_repo = etudiant_repo

    async def executer(self, id_etudiant: str, dto: EtudiantModifierDTO) -> EtudiantReponseDTO:
        etudiant = await self._etudiant_repo.trouver_par_id(id_etudiant)
        if not etudiant:
            raise EtudiantIntrouvableError(id_etudiant)

        # On applique uniquement les champs fournis (exclude_unset=True)
        donnees = dto.model_dump(exclude_unset=True)

        if "nom" in donnees:
            etudiant.nom = donnees["nom"].upper()
        if "prenom" in donnees:
            etudiant.prenom = donnees["prenom"].capitalize()
        if "date_naissance" in donnees:
            etudiant.date_naissance = donnees["date_naissance"]
        if "sexe" in donnees:
            etudiant.sexe = Sexe(donnees["sexe"])
        if "id_specialite" in donnees:
            etudiant.id_specialite = donnees["id_specialite"]
        if "code_specialite" in donnees:
            etudiant.code_specialite = donnees["code_specialite"]
        if "niveau" in donnees:
            etudiant.niveau = Niveau(donnees["niveau"])
        if "annee_academique" in donnees:
            etudiant.annee_academique = donnees["annee_academique"]
        if "email_etudiant" in donnees:
            etudiant.email_etudiant = Email(donnees["email_etudiant"]) if donnees["email_etudiant"] else None
        if "telephone_etudiant" in donnees:
            etudiant.telephone_etudiant = Telephone(donnees["telephone_etudiant"]) if donnees["telephone_etudiant"] else None
        if "nom_parent" in donnees:
            etudiant.nom_parent = donnees["nom_parent"].upper()
        if "prenom_parent" in donnees:
            etudiant.prenom_parent = donnees["prenom_parent"].capitalize()
        if "lien_parent" in donnees:
            etudiant.lien_parent = LienParent(donnees["lien_parent"])
        if "telephone_parent" in donnees:
            etudiant.telephone_parent = Telephone(donnees["telephone_parent"]) if donnees["telephone_parent"] else None
        if "email_parent" in donnees:
            etudiant.email_parent = Email(donnees["email_parent"]) if donnees["email_parent"] else None

        try:
            etudiant_sauvegarde = await self._etudiant_repo.sauvegarder(etudiant)
        except ValueError as e:
            raise ValueError(f"Données invalides : {e}")

        return _domaine_vers_reponse(etudiant_sauvegarde)


# ============================================================
#  CAS D'USAGE 6 : SupprimerEtudiantUseCase
# ============================================================
class SupprimerEtudiantUseCase:
    """
    Supprime un étudiant.

    ATTENTION : à utiliser avec précaution — supprime aussi
    (via les contraintes de clé étrangère / cascade applicative)
    l'historique de paiements lié si la base l'exige.
    """

    def __init__(self, etudiant_repo: IEtudiantRepository):
        self._etudiant_repo = etudiant_repo

    async def executer(self, id_etudiant: str) -> None:
        supprime = await self._etudiant_repo.supprimer(id_etudiant)
        if not supprime:
            raise EtudiantIntrouvableError(id_etudiant)
