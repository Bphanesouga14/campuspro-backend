#Les erreurs métier nommées

# ============================================================
#  FICHIER : app/domain/exceptions.py
#
#  RÔLE : Définir toutes les erreurs métier du domaine.
#
#  POURQUOI DES EXCEPTIONS PERSONNALISÉES ?
#  En Python, on peut utiliser ValueError ou Exception partout.
#  Mais dans la Clean Architecture, on préfère des erreurs
#  qui ont un NOM MÉTIER précis.
#
#  AVANTAGE :
#  Au lieu de "ValueError: montant incorrect"
#  on lève    "PaiementExcessifError: 90000 > 75000 attendus"
#  → Le code devient lisible comme un texte métier.
#
#  COUCHE : Domaine (zéro dépendance externe)
# ============================================================


# ── CLASSE MÈRE ─────────────────────────────────────────────
# Toutes nos erreurs métier héritent de cette classe.
# Cela permet d'attraper n'importe quelle erreur métier
# avec un seul "except DomaineError".

class DomaineError(Exception):
    """Erreur de base pour toutes les erreurs métier du domaine SIGC."""
    pass


# ============================================================
#  ERREURS LIÉES À L'ÉTUDIANT
# ============================================================

class EtudiantDejaExistantError(DomaineError):
    """
    Levée quand on essaie de créer un étudiant
    avec un matricule ou un ID qui existe déjà.

    Exemple :
        raise EtudiantDejaExistantError("MAT-2024-INFO-001")
    """
    def __init__(self, matricule: str):
        super().__init__(
            f"Un étudiant avec le matricule '{matricule}' existe déjà."
        )
        self.matricule = matricule


class EtudiantIntrouvableError(DomaineError):
    """
    Levée quand on cherche un étudiant qui n'existe pas en base.

    Exemple :
        raise EtudiantIntrouvableError("ETU-2024-999")
    """
    def __init__(self, id_etudiant: str):
        super().__init__(
            f"Aucun étudiant trouvé avec l'identifiant '{id_etudiant}'."
        )
        self.id_etudiant = id_etudiant


class EtudiantSuppressionImpossibleError(DomaineError):
    """
    Levée quand on essaie de supprimer un étudiant qui a déjà
    des paiements, QR codes ou notifications liés en base.

    RÈGLE MÉTIER : Pour préserver l'historique financier,
    on ne supprime jamais un étudiant qui a un historique.

    Exemple :
        raise EtudiantSuppressionImpossibleError("ETU-2024-001")
    """
    def __init__(self, id_etudiant: str):
        super().__init__(
            f"Impossible de supprimer l'étudiant '{id_etudiant}' : "
            f"il a un historique de paiements, QR codes ou notifications. "
            f"Cet historique doit être conservé."
        )
        self.id_etudiant = id_etudiant


# ============================================================
#  ERREURS LIÉES AU PAIEMENT
# ============================================================

class PaiementExcessifError(DomaineError):
    """
    Levée quand le montant payé dépasse le montant attendu.

    RÈGLE MÉTIER : On ne peut pas payer plus que ce qui est dû.
    Si la tranche vaut 75 000 FCFA, on ne peut pas enregistrer
    un paiement de 90 000 FCFA pour cette même tranche.

    Exemple :
        raise PaiementExcessifError(
            montant_paye=90000,
            montant_attendu=75000
        )
    """
    def __init__(self, montant_paye: float, montant_attendu: float):
        super().__init__(
            f"Le montant payé ({montant_paye:,.0f} FCFA) dépasse "
            f"le montant attendu ({montant_attendu:,.0f} FCFA). "
            f"Opération refusée."
        )
        self.montant_paye    = montant_paye
        self.montant_attendu = montant_attendu


class PaiementDejaEffectueError(DomaineError):
    """
    Levée quand on essaie de payer une tranche déjà entièrement payée.

    RÈGLE MÉTIER : Une tranche dont le statut est PAYÉ
    ne peut plus recevoir de nouveau paiement.

    Exemple :
        raise PaiementDejaEffectueError("PAY-001", 1)
    """
    def __init__(self, id_paiement: str, numero_tranche: int):
        super().__init__(
            f"La tranche {numero_tranche} (ID: {id_paiement}) "
            f"est déjà entièrement payée. Aucune modification possible."
        )
        self.id_paiement    = id_paiement
        self.numero_tranche = numero_tranche


class PaiementIntrouvableError(DomaineError):
    """
    Levée quand on cherche un paiement qui n'existe pas.

    Exemple :
        raise PaiementIntrouvableError("PAY-999")
    """
    def __init__(self, id_paiement: str):
        super().__init__(
            f"Aucun paiement trouvé avec l'identifiant '{id_paiement}'."
        )
        self.id_paiement = id_paiement


class MontantNegatifError(DomaineError):
    """
    Levée quand on essaie d'enregistrer un montant négatif.

    RÈGLE MÉTIER : Aucun montant financier ne peut être négatif.
    """
    def __init__(self, montant: float):
        super().__init__(
            f"Le montant {montant:,.0f} FCFA est invalide. "
            f"Un montant ne peut pas être négatif."
        )
        self.montant = montant


# ============================================================
#  ERREURS LIÉES AU QR CODE
# ============================================================

class QRCodeNonAutoriseSError(DomaineError):
    """
    Levée quand on essaie de générer un QR code
    alors que la tranche 1 n'est pas encore entièrement payée.

    RÈGLE MÉTIER : Le QR code ne se génère QUE si la tranche 1
    est complètement payée (statut = PAYÉ).

    Exemple :
        raise QRCodeNonAutoriseSError("ETU-2024-001", statut="PARTIEL")
    """
    def __init__(self, id_etudiant: str, statut: str):
        super().__init__(
            f"Impossible de générer un QR code pour l'étudiant '{id_etudiant}'. "
            f"La tranche 1 doit être entièrement payée. Statut actuel : {statut}."
        )
        self.id_etudiant = id_etudiant
        self.statut      = statut


class QRCodeIntrouvableError(DomaineError):
    """
    Levée quand on cherche un QR code qui n'existe pas.
    """
    def __init__(self, id_etudiant: str):
        super().__init__(
            f"Aucun QR code actif trouvé pour l'étudiant '{id_etudiant}'."
        )
        self.id_etudiant = id_etudiant


# ============================================================
#  ERREURS LIÉES À LA SPÉCIALITÉ
# ============================================================

class SpecialiteIntrouvableError(DomaineError):
    """
    Levée quand on cherche une spécialité qui n'existe pas.
    """
    def __init__(self, id_specialite: str):
        super().__init__(
            f"Aucune spécialité trouvée avec l'identifiant '{id_specialite}'."
        )
        self.id_specialite = id_specialite


# ============================================================
#  ERREURS LIÉES À L'IMPORT EXCEL
# ============================================================

class ImportExcelError(DomaineError):
    """
    Levée lors d'une erreur pendant l'import du fichier Excel.

    Exemple :
        raise ImportExcelError("Feuille 'Etudiants' absente du fichier.")
    """
    def __init__(self, message: str, feuille: str = ""):
        details = f" (Feuille : {feuille})" if feuille else ""
        super().__init__(f"Erreur d'import Excel{details} : {message}")
        self.feuille = feuille


class FichierExcelInvalideError(DomaineError):
    """
    Levée quand le fichier uploadé n'est pas un fichier Excel valide.
    """
    def __init__(self, nom_fichier: str):
        super().__init__(
            f"Le fichier '{nom_fichier}' n'est pas un fichier Excel valide (.xlsx). "
            f"Veuillez fournir le fichier GestionScolaire_SIGC.xlsx."
        )
        self.nom_fichier = nom_fichier


# ============================================================
#  ERREURS LIÉES À L'AUTHENTIFICATION
# ============================================================

class UtilisateurDejaExistantError(DomaineError):
    """Levée quand on essaie de créer un compte avec un email déjà utilisé."""
    def __init__(self, email: str):
        super().__init__(f"Un compte existe déjà avec l'email '{email}'.")
        self.email = email


class UtilisateurIntrouvableError(DomaineError):
    """Levée quand on cherche un utilisateur qui n'existe pas."""
    def __init__(self, identifiant: str):
        super().__init__(f"Aucun utilisateur trouvé avec l'identifiant '{identifiant}'.")
        self.identifiant = identifiant


class IdentifiantsInvalidesError(DomaineError):
    """
    Levée lors d'une tentative de connexion avec un email ou
    un mot de passe incorrect.

    Message volontairement générique (ne précise pas lequel des deux
    est faux) pour ne pas aider un attaquant à deviner les emails valides.
    """
    def __init__(self):
        super().__init__("Email ou mot de passe incorrect.")


class CompteDesactiveError(DomaineError):
    """Levée quand un compte désactivé tente de se connecter."""
    def __init__(self):
        super().__init__("Ce compte a été désactivé. Contactez un administrateur.")
