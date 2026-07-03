#DTOs : ce qui entre et sort de l'API

from __future__ import annotations
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
import re


class SpecialiteReponseDTO(BaseModel):
    """Réponse API pour une spécialité."""
    id_specialite: str
    code: str
    nom_specialite: str
    departement: str
    niveau: int
    duree_ans: int
    annee_academique: str
    tranche_1: float
    date_limite_t1: str
    tranche_2: float
    date_limite_t2: str
    tranche_3: float
    date_limite_t3: str
    total: float
    groupe_academique: str
    mois_demarrage: str
    model_config = {"from_attributes": True}


class SpecialiteCreerDTO(BaseModel):
    """Données reçues pour créer ou modifier une spécialité."""
    id_specialite: str = Field(..., examples=["SP-001"])
    code: str = Field(..., examples=["INFO1"])
    nom_specialite: str
    departement: str
    niveau: int = Field(..., ge=1, le=5)
    duree_ans: int = Field(1, ge=1)
    annee_academique: str = Field(..., examples=["2024-2025"])
    tranche_1: Decimal = Field(..., ge=0)
    date_limite_t1: str = Field(..., examples=["31/10/2024"])
    tranche_2: Decimal = Field(..., ge=0)
    date_limite_t2: str = Field(..., examples=["31/01/2025"])
    tranche_3: Decimal = Field(..., ge=0)
    date_limite_t3: str = Field(..., examples=["30/04/2025"])

    @field_validator("annee_academique")
    @classmethod
    def valider_annee(cls, v):
        if not re.match(r"^\d{4}-\d{4}$", v):
            raise ValueError(f"Format d'année invalide '{v}'. Exemple : 2024-2025")
        return v


class CalendrierNiveauDTO(BaseModel):
    """Réponse API pour une ligne du calendrier académique d'un niveau."""
    niveau: int
    groupe: str
    demarrage_academique: str
    tranche_1_limite: str
    tranche_2_limite: str
    tranche_3_limite: str
    condition_demarrage: str
    mois_debut: str
    mois_fin: str
    model_config = {"from_attributes": True}


class TableauDeBordDTO(BaseModel):
    """Réponse API pour le tableau de bord global."""
    nb_etudiants: int
    total_attendu: float
    total_verse: float
    total_reste: float
    taux_recouvrement: float = Field(..., description="Pourcentage du total attendu déjà versé")
    nb_etudiants_a_jour: int
    nb_etudiants_en_retard: int
    nb_paiements_en_retard: int
    nb_specialites: int


class EtudiantCreerDTO(BaseModel):
    """Données reçues pour créer un étudiant (formulaire ou import Excel)."""
    id_etudiant: str = Field(..., examples=["ETU-2024-001"])
    matricule: str = Field(..., description="Format MAT-AAAA-CODE-NNN", examples=["MAT-2024-INFO-001"])
    nom: str
    prenom: str
    date_naissance: Optional[str] = None
    sexe: str
    id_specialite: str
    code_specialite: str
    niveau: int = Field(..., ge=1, le=5)
    annee_academique: str = Field(..., examples=["2024-2025"])
    email_etudiant: Optional[str] = None
    telephone_etudiant: Optional[str] = None
    nom_parent: str
    prenom_parent: str
    lien_parent: str = Field(..., description="Père, Mère ou Tuteur")
    telephone_parent: str
    email_parent: Optional[str] = None

    @field_validator("sexe")
    @classmethod
    def valider_sexe(cls, v):
        if v.upper() not in ("M", "F"):
            raise ValueError("Le sexe doit être 'M' ou 'F'")
        return v.upper()

    @field_validator("annee_academique")
    @classmethod
    def valider_annee(cls, v):
        if not re.match(r"^\d{4}-\d{4}$", v):
            raise ValueError(f"Format d'année invalide '{v}'. Exemple : 2024-2025")
        return v


class EtudiantModifierDTO(BaseModel):
    """
    Données reçues pour modifier un étudiant existant (PUT).
    Tous les champs sont optionnels : seuls les champs fournis sont mis à jour.
    """
    nom: Optional[str] = None
    prenom: Optional[str] = None
    date_naissance: Optional[str] = None
    sexe: Optional[str] = None
    id_specialite: Optional[str] = None
    code_specialite: Optional[str] = None
    niveau: Optional[int] = Field(None, ge=1, le=5)
    annee_academique: Optional[str] = None
    email_etudiant: Optional[str] = None
    telephone_etudiant: Optional[str] = None
    nom_parent: Optional[str] = None
    prenom_parent: Optional[str] = None
    lien_parent: Optional[str] = None
    telephone_parent: Optional[str] = None
    email_parent: Optional[str] = None

    @field_validator("sexe")
    @classmethod
    def valider_sexe(cls, v):
        if v is not None and v.upper() not in ("M", "F"):
            raise ValueError("Le sexe doit être 'M' ou 'F'")
        return v.upper() if v else v


class EtudiantReponseDTO(BaseModel):
    """Réponse API pour un étudiant — données complètes + montants calculés."""
    id_etudiant: str
    matricule: str
    nom: str
    prenom: str
    nom_complet: str
    date_naissance: Optional[str]
    sexe: str
    id_specialite: str
    code_specialite: str
    niveau: int
    annee_academique: str
    email_etudiant: Optional[str] = None
    telephone_etudiant: Optional[str] = None
    nom_parent: str
    prenom_parent: str
    lien_parent: str
    telephone_parent: str
    email_parent: Optional[str] = None
    cumul_verse: float
    total_annuel_attendu: float
    reste_global: float
    est_a_jour: bool
    photo:              Optional[str] = None   # ← AJOUTER cette ligne
    model_config = {"from_attributes": True}


class EtudiantDetailDTO(EtudiantReponseDTO):
    """Détail complet : hérite de EtudiantReponseDTO + paiements + QR codes."""
    paiements: List["PaiementReponseDTO"] = []
    qr_codes: List["QRCodeReponseDTO"] = []


class VersementDTO(BaseModel):
    """Données du caissier pour enregistrer un paiement physique."""
    montant: Decimal = Field(..., gt=0, description="Montant versé en FCFA")
    date_paiement: str = Field(..., examples=["15/10/2024"])
    observations: Optional[str] = None

    @field_validator("date_paiement")
    @classmethod
    def valider_date(cls, v):
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", v):
            raise ValueError(f"Format de date invalide '{v}'. Format attendu : DD/MM/YYYY")
        return v


class PaiementReponseDTO(BaseModel):
    """Réponse API pour une tranche de paiement."""
    id_paiement: str
    id_etudiant: str
    id_specialite: str
    niveau: int
    numero_tranche: int
    montant_attendu: float
    montant_paye: float
    reste_a_payer: float
    date_paiement: Optional[str]
    date_limite: str
    statut: str
    qr_code_genere: bool
    notif_parent_envoyee: bool
    observations: Optional[str]
    model_config = {"from_attributes": True}


class HistoriquePaiementsDTO(BaseModel):
    """Vue d'ensemble financière + détail des tranches d'un étudiant."""
    id_etudiant: str
    nom_complet: str
    cumul_verse: float
    total_annuel_attendu: float
    reste_global: float
    est_a_jour: bool
    paiements: List[PaiementReponseDTO]


class QRCodeReponseDTO(BaseModel):
    """Réponse API pour un QR code."""
    id_qrcode: str
    id_etudiant: str
    id_specialite: str
    niveau: int
    date_generation: str
    valide_jusqua: str
    statut: str
    est_valide: bool
    qr_data: Optional[str] = None
    model_config = {"from_attributes": True}


class NotificationReponseDTO(BaseModel):
    """Réponse API pour une notification parent."""
    id_notification: str
    id_paiement: str
    id_etudiant: str
    nom_parent: str
    contact_parent: str
    type_notification: str
    message: str
    date_envoi: Optional[str]
    canal: str
    statut_envoi: str
    model_config = {"from_attributes": True}


class ResultatFeuilleDTO(BaseModel):
    """Résultat de l'import d'une seule feuille Excel."""
    feuille: str
    inseres: int
    mis_a_jour: int
    erreurs: int
    details: List[str] = []


class ImportExcelReponseDTO(BaseModel):
    """Résultat complet de l'import du fichier Excel — toutes feuilles."""
    succes: bool
    message: str
    total_lignes: int
    resultats: List[ResultatFeuilleDTO]


# ════════════════════════════════════════════════════════════
#  DTOs : AUTHENTIFICATION
# ════════════════════════════════════════════════════════════

class UtilisateurCreerDTO(BaseModel):
    """Données reçues pour créer un compte utilisateur (réservé aux admins)."""
    email: str = Field(..., examples=["secretaire@ecole.cm"])
    nom: str = Field(..., examples=["Jeanne Fotso"])
    mot_de_passe: str = Field(..., min_length=8, description="Minimum 8 caractères")
    role: str = Field(..., description="ADMIN, SECRETAIRE ou CAISSIER")

    @field_validator("email")
    @classmethod
    def valider_email(cls, v):
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError(f"Adresse email invalide : '{v}'")
        return v.lower()

    @field_validator("role")
    @classmethod
    def valider_role(cls, v):
        if v.upper() not in ("ADMIN", "SECRETAIRE", "CAISSIER"):
            raise ValueError("Le rôle doit être ADMIN, SECRETAIRE ou CAISSIER")
        return v.upper()


class UtilisateurReponseDTO(BaseModel):
    """Réponse API pour un compte utilisateur (sans le hash du mot de passe)."""
    id_utilisateur: str
    email: str
    nom: str
    role: str
    actif: bool
    photo: Optional[str] = None   # ← ajouter ici
    model_config = {"from_attributes": True}


class TokenReponseDTO(BaseModel):
    """Réponse API après une connexion réussie."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Durée de validité du token, en secondes")
    utilisateur: UtilisateurReponseDTO


EtudiantDetailDTO.model_rebuild()
