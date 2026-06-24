#Les petits types métier


#  RÔLE : Définir les "Value Objects" du domaine.
#
#  C'EST QUOI UN VALUE OBJECT ?
#  C'est un petit objet qui représente une valeur métier
#  avec ses propres règles de validation.
#
#  EXEMPLE CONCRET :
#  Un simple string "abc" peut être un matricule.
#  Mais un Matricule (Value Object) sait lui-même
#  si sa valeur est valide ou non.
#
#  RÈGLE CLÉ : Un Value Object est IMMUABLE.
#  Une fois créé, on ne peut plus le modifier.
#  Si on veut changer la valeur → on crée un nouveau.
#
#  COUCHE : Domaine (zéro dépendance externe)
# ============================================================

import re
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum



#  VALUE OBJECT : Matricule

@dataclass(frozen=True)
class Matricule:
    """
    Représente le matricule unique d'un étudiant.
    FORMAT ATTENDU : MAT-AAAA-CODE-NNN
    Exemples valides : MAT-2024-INFO-001, MAT-2025-GEST-042
    """
    valeur: str

    def __post_init__(self):
        # Règle 1 : ne peut pas être vide
        if not self.valeur or not self.valeur.strip():
            raise ValueError("Le matricule ne peut pas être vide.")

        # Règle 2 : doit respecter le format MAT-AAAA-CODE-NNN
        # ^ = début    \d{4} = 4 chiffres    [A-Z]+ = lettres maj    $ = fin
        pattern = r"^MAT-\d{4}-[A-Z]+-\d{3}$"
        if not re.match(pattern, self.valeur):
            raise ValueError(
                f"Format de matricule invalide : '{self.valeur}'. "
                f"Format attendu : MAT-AAAA-CODE-NNN (ex: MAT-2024-INFO-001)"
            )

    def __str__(self) -> str:
        return self.valeur


# ============================================================
#  VALUE OBJECT : Montant
# ============================================================
@dataclass(frozen=True)
class Montant:
    """
    Représente un montant financier en FCFA.

    Pourquoi Decimal et pas float ?
    Les flottants ont des erreurs d'arrondi en Python.
    75000.1 + 75000.2 peut donner 150000.30000000001.
    Decimal évite ce problème pour les calculs financiers.
    """
    valeur: Decimal

    def __post_init__(self):
        # Convertir en Decimal si on reçoit un int ou float
        # object.__setattr__ est nécessaire car frozen=True
        if not isinstance(self.valeur, Decimal):
            object.__setattr__(self, "valeur", Decimal(str(self.valeur)))
        # Règle : un montant ne peut pas être négatif
        if self.valeur < Decimal("0"):
            raise ValueError(f"Un montant ne peut pas être négatif : {self.valeur} FCFA")

    def __add__(self, autre: "Montant") -> "Montant":
        # Permet d'écrire : montant1 + montant2
        return Montant(self.valeur + autre.valeur)

    def __sub__(self, autre: "Montant") -> "Montant":
        # Permet d'écrire : montant1 - montant2
        return Montant(self.valeur - autre.valeur)

    def __ge__(self, autre: "Montant") -> bool:
        return self.valeur >= autre.valeur

    def __le__(self, autre: "Montant") -> bool:
        return self.valeur <= autre.valeur

    def __gt__(self, autre: "Montant") -> bool:
        return self.valeur > autre.valeur

    def est_zero(self) -> bool:
        return self.valeur == Decimal("0")

    def __str__(self) -> str:
        # Affiche "75 000 FCFA"
        return f"{self.valeur:,.0f} FCFA".replace(",", " ")


# ============================================================
#  VALUE OBJECT : Email
# ============================================================
@dataclass(frozen=True)
class Email:
    """Adresse email valide. Doit contenir @ et un domaine."""
    valeur: str

    def __post_init__(self):
        if not self.valeur:
            raise ValueError("L'adresse email ne peut pas être vide.")
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(pattern, self.valeur):
            raise ValueError(f"Adresse email invalide : '{self.valeur}'")

    def __str__(self) -> str:
        return self.valeur


# ============================================================
#  VALUE OBJECT : Telephone
# ============================================================
@dataclass(frozen=True)
class Telephone:
    """
    Numéro de téléphone camerounais.
    Formats acceptés : 677000001, +237677000001
    """
    valeur: str

    def __post_init__(self):
        if not self.valeur:
            raise ValueError("Le numéro de téléphone ne peut pas être vide.")
        # Nettoyer espaces et tirets
        nettoye = re.sub(r"[\s\-]", "", self.valeur)
        object.__setattr__(self, "valeur", nettoye)
        # Vérifier le format camerounais
        pattern = r"^(\+?237)?6\d{8}$"
        if not re.match(pattern, self.valeur):
            raise ValueError(
                f"Numéro de téléphone invalide : '{self.valeur}'. "
                f"Exemple valide : 677000001 ou +237677000001"
            )

    def __str__(self) -> str:
        return self.valeur


# ============================================================
#  ENUMS DU DOMAINE
#  Ces Enums représentent des concepts métier, pas techniques.
# ============================================================

class Sexe(Enum):
    """Le sexe d'un étudiant."""
    MASCULIN = "M"
    FEMININ  = "F"


class LienParent(Enum):
    """Le lien entre le parent/tuteur et l'étudiant."""
    PERE   = "Père"
    MERE   = "Mère"
    TUTEUR = "Tuteur"


class RoleUtilisateur(Enum):
    """
    Rôle d'un utilisateur du système (authentification).

    - ADMIN      : accès complet, y compris gestion des comptes utilisateurs
    - SECRETAIRE : gère les étudiants, spécialités, l'import Excel
    - CAISSIER   : enregistre les versements de paiement, consulte les QR codes
    """
    ADMIN      = "ADMIN"
    SECRETAIRE = "SECRETAIRE"
    CAISSIER   = "CAISSIER"


class StatutPaiement(Enum):
    """
    Statut d'une tranche de paiement.
    Transitions autorisées :
      EN_ATTENTE → PARTIEL → PAYE
      EN_ATTENTE → EN_RETARD
      PARTIEL    → EN_RETARD
    """
    EN_ATTENTE = "EN ATTENTE"
    PARTIEL    = "PARTIEL"
    PAYE       = "PAYÉ"
    EN_RETARD  = "EN RETARD"


class StatutQRCode(Enum):
    """Statut d'un QR code."""
    ACTIF    = "ACTIF"
    EXPIRE   = "EXPIRÉ"
    SUSPENDU = "SUSPENDU"


class TypeNotification(Enum):
    """Type de message envoyé au parent."""
    CONFIRMATION = "CONFIRMATION PAIEMENT"
    PARTIEL      = "PAIEMENT PARTIEL"
    RELANCE      = "RELANCE RETARD"
    RAPPEL       = "RAPPEL PAIEMENT"


class Niveau(Enum):
    """
    Niveaux académiques avec leur groupe de démarrage.

    RÈGLE MÉTIER :
    - Niveaux 1 et 2 → démarrent en OCTOBRE (même groupe)
    - Niveau 3       → démarre en FÉVRIER (après N1 et N2)
    - Niveaux 4 et 5 → démarrent en AVRIL  (après N3)
    """
    UN     = 1
    DEUX   = 2
    TROIS  = 3
    QUATRE = 4
    CINQ   = 5

    def groupe(self) -> str:
        """Retourne le groupe académique du niveau."""
        if self.value in (1, 2):
            return "Groupe A"
        elif self.value == 3:
            return "Groupe B"
        else:
            return "Groupe C"

    def mois_demarrage(self) -> str:
        """Retourne le mois de démarrage académique."""
        if self.value in (1, 2):
            return "Octobre"
        elif self.value == 3:
            return "Février"
        else:
            return "Avril"
