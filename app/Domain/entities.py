#Les objets principaux

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from app.Domain.value_objects import (
    Matricule, Montant, Email, Telephone,
    Sexe, LienParent, StatutPaiement, StatutQRCode,
    TypeNotification, Niveau, RoleUtilisateur
)
from app.Domain.exceptions import (
    PaiementExcessifError, PaiementDejaEffectueError,
    QRCodeNonAutoriseSError, MontantNegatifError,
)

@dataclass
class SpecialiteDomaine:
    """Filière/spécialité avec ses montants et règles calendaires."""
    id_specialite: str
    code: str
    nom_specialite: str
    departement: str
    niveau: Niveau
    duree_ans: int
    annee_academique: str
    tranche_1: Montant
    date_limite_t1: str
    tranche_2: Montant
    date_limite_t2: str
    tranche_3: Montant
    date_limite_t3: str

    @property
    def total(self) -> Montant:
        return self.tranche_1 + self.tranche_2 + self.tranche_3

    @property
    def mois_demarrage(self) -> str:
        return self.niveau.mois_demarrage()

    @property
    def groupe_academique(self) -> str:
        return self.niveau.groupe()


@dataclass
class PaiementDomaine:
    """
    Tranche de paiement avec règles métier :
    - Pas de dépassement du montant attendu
    - Tranche soldée non modifiable
    - QR code uniquement si tranche 1 entièrement payée
    """
    id_paiement: str
    id_etudiant: str
    id_specialite: str
    niveau: int
    numero_tranche: int
    montant_attendu: Montant
    montant_paye: Montant
    date_limite: str
    statut: StatutPaiement
    date_paiement: Optional[str] = None
    qr_code_genere: bool = False
    notif_envoyee: bool = False
    observations: Optional[str] = None

    @property
    def reste_a_payer(self) -> Montant:
        return self.montant_attendu - self.montant_paye

    @property
    def est_entierement_paye(self) -> bool:
        return self.montant_paye.valeur >= self.montant_attendu.valeur

    def enregistrer_versement(self, montant_verse: Montant, date: str) -> None:
        """Enregistre un versement physique avec toutes les règles métier."""
        if montant_verse.est_zero() or montant_verse.valeur < Decimal("0"):
            raise MontantNegatifError(float(montant_verse.valeur))
        if self.statut == StatutPaiement.PAYE:
            raise PaiementDejaEffectueError(self.id_paiement, self.numero_tranche)
        nouveau_total = Montant(self.montant_paye.valeur + montant_verse.valeur)
        if nouveau_total > self.montant_attendu:
            raise PaiementExcessifError(
                float(nouveau_total.valeur), float(self.montant_attendu.valeur)
            )
        self.montant_paye = nouveau_total
        self.date_paiement = date
        self._recalculer_statut()

    def _recalculer_statut(self) -> None:
        if self.montant_paye.valeur >= self.montant_attendu.valeur:
            self.statut = StatutPaiement.PAYE
        elif self.montant_paye.valeur > Decimal("0"):
            self.statut = StatutPaiement.PARTIEL

    def peut_generer_qr(self) -> bool:
        return self.numero_tranche == 1 and self.statut == StatutPaiement.PAYE

    def marquer_qr_genere(self) -> None:
        if not self.peut_generer_qr():
            raise QRCodeNonAutoriseSError(self.id_etudiant, self.statut.value)
        self.qr_code_genere = True


@dataclass
class EtudiantDomaine:
    """Entité centrale — agrège toutes les infos et paiements d'un étudiant."""
    id_etudiant: str
    matricule: Matricule
    nom: str
    prenom: str
    date_naissance: Optional[str]
    sexe: Sexe
    id_specialite: str
    code_specialite: str
    niveau: Niveau
    annee_academique: str
    email_etudiant: Optional[Email] = None
    telephone_etudiant: Optional[Telephone] = None
    nom_parent: str = ""
    prenom_parent: str = ""
    lien_parent: Optional[LienParent] = None
    telephone_parent: Optional[Telephone] = None
    email_parent: Optional[Email] = None
    paiements: List[PaiementDomaine] = field(default_factory=list)

    @property
    def nom_complet(self) -> str:
        return f"{self.nom} {self.prenom}"

    @property
    def cumul_verse(self) -> Montant:
        if not self.paiements:
            return Montant(Decimal("0"))
        return Montant(sum(p.montant_paye.valeur for p in self.paiements))

    @property
    def total_annuel_attendu(self) -> Montant:
        if not self.paiements:
            return Montant(Decimal("0"))
        return Montant(sum(p.montant_attendu.valeur for p in self.paiements))

    @property
    def reste_global(self) -> Montant:
        return self.total_annuel_attendu - self.cumul_verse

    @property
    def est_a_jour(self) -> bool:
        statuts_problematiques = {StatutPaiement.EN_RETARD, StatutPaiement.EN_ATTENTE, StatutPaiement.PARTIEL}
        return not any(p.statut in statuts_problematiques for p in self.paiements)

    def tranche(self, numero: int) -> Optional[PaiementDomaine]:
        for p in self.paiements:
            if p.numero_tranche == numero:
                return p
        return None

    def paiements_en_retard(self) -> List[PaiementDomaine]:
        return [p for p in self.paiements if p.statut == StatutPaiement.EN_RETARD]


@dataclass
class QRCodeDomaine:
    """QR code généré pour un étudiant à jour de paiement."""
    id_qrcode: str
    id_etudiant: str
    id_paiement: Optional[str]
    id_specialite: str
    niveau: int
    date_generation: str
    valide_jusqua: str
    statut: StatutQRCode = StatutQRCode.ACTIF
    qr_data: Optional[str] = None

    @property
    def est_valide(self) -> bool:
        return self.statut == StatutQRCode.ACTIF

    def suspendre(self) -> None:
        self.statut = StatutQRCode.SUSPENDU

    def expirer(self) -> None:
        self.statut = StatutQRCode.EXPIRE


@dataclass
class NotificationDomaine:
    """Notification envoyée au parent d'un étudiant."""
    id_notification: str
    id_paiement: str
    id_etudiant: str
    nom_parent: str
    contact_parent: str
    type_notification: TypeNotification
    message: str
    canal: str
    date_envoi: Optional[str] = None
    statut_envoi: str = "EN ATTENTE"

    @staticmethod
    def construire_message(
        nom_etudiant: str,
        numero_tranche: int,
        montant_paye: Montant,
        montant_attendu: Montant,
        date_paiement: str,
    ) -> str:
        reste = montant_attendu - montant_paye
        if reste.est_zero():
            return (
                f"Paiement reçu pour {nom_etudiant}. "
                f"Tranche {numero_tranche} : {montant_paye} payés. "
                f"Tranche soldée. QR Code valide généré."
            )
        return (
            f"Paiement partiel reçu pour {nom_etudiant}. "
            f"Tranche {numero_tranche} : {montant_paye} payés "
            f"sur {montant_attendu} attendus. "
            f"Reste : {reste}. Paiement effectué le {date_paiement}."
        )


@dataclass
class UtilisateurDomaine:
    """
    Compte utilisateur du système (authentification).

    RÈGLE MÉTIER : seul un compte ACTIF peut se connecter.
    Le mot de passe n'est JAMAIS stocké en clair — uniquement son hash.
    """
    id_utilisateur: str
    email: str
    nom: str
    mot_de_passe_hash: str
    role: RoleUtilisateur
    actif: bool = True
    created_at: Optional[str] = None

    def a_le_role(self, *roles: RoleUtilisateur) -> bool:
        """Vérifie si l'utilisateur a un des rôles donnés."""
        return self.role in roles
