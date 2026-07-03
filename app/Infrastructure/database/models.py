
import enum                    # Pour créer des listes de choix fixes (ex: M/F)
from datetime import datetime  

from sqlalchemy import (
    Column,      
    String,      
    Integer,    
    Numeric,     
    Boolean,    
    Text,       
    DateTime,    
    ForeignKey,  
    UniqueConstraint,  # Règle : deux lignes ne peuvent pas avoir les mêmes valeurs
    Enum as SAEnum,    # Type liste de choix fixes (stocké en base)
)
from sqlalchemy.orm import relationship, DeclarativeBase
# relationship → permet de naviguer entre tables liées (ex: etudiant.paiements)
# DeclarativeBase → la "classe mère" dont héritent tous nos modèles


# ============================================================
#  BASE — La classe mère de tous les modèles
# ============================================================
# Tous nos modèles vont "hériter" de Base.

class Base(DeclarativeBase):
    pass  # Rien à ajouter ici, c'est juste un socle commun


# ============================================================
#  ENUMS — Listes de valeurs autorisées
# ============================================================
# Un Enum = une liste de choix fixes.
# Exemple : le statut d'un paiement ne peut être QUE l'un de ces 4 mots.
# Si on essaie de mettre autre chose → PostgreSQL refusera.

class StatutPaiementEnum(str, enum.Enum):
    # str = on peut comparer avec une chaîne normale ("PAYÉ" == StatutPaiementEnum.PAYE)
    PAYE       = "PAYÉ"        # La tranche est entièrement payée
    EN_ATTENTE = "EN ATTENTE"  # Rien n'a encore été payé
    EN_RETARD  = "EN RETARD"   # La date limite est dépassée
    PARTIEL    = "PARTIEL"     # Une partie seulement a été payée


class StatutQREnum(str, enum.Enum):
    ACTIF    = "ACTIF"     # QR code valide, peut être scanné
    EXPIRE   = "EXPIRÉ"    # QR code périmé
    SUSPENDU = "SUSPENDU"  # QR code désactivé manuellement


class StatutNotifEnum(str, enum.Enum):
    ENVOYE     = "ENVOYÉ"      # Notification bien envoyée au parent
    EN_ATTENTE = "EN ATTENTE"  # En attente d'envoi
    ECHOUE     = "ÉCHOUÉ"      # Erreur lors de l'envoi


class TypeNotifEnum(str, enum.Enum):
    CONFIRMATION = "CONFIRMATION PAIEMENT"  # Paiement reçu avec succès
    PARTIEL      = "PAIEMENT PARTIEL"       # Paiement reçu, mais incomplet
    RELANCE      = "RELANCE RETARD"         # Rappel : paiement en retard
    RAPPEL       = "RAPPEL PAIEMENT"        # Rappel avant la date limite


class SexeEnum(str, enum.Enum):
    M = "M"  # Masculin
    F = "F"  # Féminin


class LienParentEnum(str, enum.Enum):
    PERE   = "Père"    # Le parent est le père
    MERE   = "Mère"    # Le parent est la mère
    TUTEUR = "Tuteur"  # Un tuteur légal


class RoleEnum(str, enum.Enum):
    ADMIN      = "ADMIN"
    SECRETAIRE = "SECRETAIRE"
    CAISSIER   = "CAISSIER"


# ============================================================
#  MODÈLE 1 : Specialite
#  Table PostgreSQL : "specialites"
#  Feuille Excel correspondante : "Specialites"
# ============================================================
class Specialite(Base):

    # __tablename__ = le vrai nom de la table dans PostgreSQL
    __tablename__ = "specialites"

    # ── COLONNES ────────────────────────────────────────────

    # primary_key=True → c'est l'identifiant unique de chaque ligne
    # Comme le numéro de ligne dans Excel, mais personnalisé ("SP-001")
    id_specialite    = Column(String(20), primary_key=True)

    # unique=True → deux spécialités ne peuvent pas avoir le même code
    # nullable=False → cette colonne est OBLIGATOIRE (ne peut pas être vide)
    code             = Column(String(10),  nullable=False, unique=True)

    nom_specialite   = Column(String(100), nullable=False)
    departement      = Column(String(50),  nullable=False)

    # Le niveau : 1, 2, 3, 4 ou 5
    niveau           = Column(Integer,     nullable=False)

    # Durée en années (généralement 1 an par niveau)
    duree_ans        = Column(Integer,     nullable=False, default=1)
    # default=1 → si on ne précise pas, la valeur par défaut est 1

    # Exemple : "2024-2025"
    annee_academique = Column(String(10),  nullable=False)

    # Montants des 3 tranches en FCFA
    # Numeric(12, 2) → jusqu'à 12 chiffres dont 2 décimales (ex: 75000.00)
    tranche_1        = Column(Numeric(12, 2), nullable=False)
    date_limite_t1   = Column(String(10),     nullable=False)  # Format : "31/10/2024"

    tranche_2        = Column(Numeric(12, 2), nullable=False)
    date_limite_t2   = Column(String(10),     nullable=False)

    tranche_3        = Column(Numeric(12, 2), nullable=False)
    date_limite_t3   = Column(String(10),     nullable=False)

    # Total = tranche_1 + tranche_2 + tranche_3 (calculé et stocké)
    total            = Column(Numeric(12, 2), nullable=False)

    # Colonnes de traçabilité : quand l'enregistrement a été créé/modifié
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # onupdate=datetime.utcnow → se met à jour automatiquement à chaque modification

    # ── RELATIONS ───────────────────────────────────────────
    # "Une spécialité peut avoir PLUSIEURS étudiants"
    # back_populates="specialite" → depuis un Etudiant, on peut faire etudiant.specialite
    etudiants = relationship("Etudiant", back_populates="specialite")
    paiements = relationship("Paiement", back_populates="specialite")


# ============================================================
#  MODÈLE 2 : Etudiant
#  Table PostgreSQL : "etudiants"
#  Feuille Excel correspondante : "Etudiants"
# ============================================================
class Etudiant(Base):

    __tablename__ = "etudiants"

    # ── COLONNES IDENTITÉ ───────────────────────────────────

    id_etudiant  = Column(String(20), primary_key=True)
    # Exemple : "ETU-2024-001"

    # unique=True → deux étudiants ne peuvent pas avoir le même matricule
    matricule    = Column(String(30), nullable=False, unique=True)
    # Exemple : "MAT-2024-INFO-001"

    nom          = Column(String(60), nullable=False)   # Exemple : "MBARGA"
    prenom       = Column(String(60), nullable=False)   # Exemple : "Jean"

    # nullable=True → la date de naissance peut être absente
    date_naissance = Column(String(10), nullable=True)  # Format : "15/03/2005"

    # SAEnum = Enum stocké dans PostgreSQL
    # Seules les valeurs "M" ou "F" seront acceptées
    sexe           = Column(SAEnum(SexeEnum), nullable=False)

    # ── COLONNES SCOLARITÉ ──────────────────────────────────

    # ForeignKey("specialites.id_specialite") →
    # Cette valeur DOIT exister dans la table "specialites"
    # Si la spécialité n'existe pas → PostgreSQL refusera l'insertion
    id_specialite   = Column(String(20), ForeignKey("specialites.id_specialite"), nullable=False)
    code_specialite = Column(String(10), nullable=False)  # Exemple : "INFO1"
    niveau          = Column(Integer,    nullable=False)  # 1, 2, 3, 4 ou 5
    annee_academique= Column(String(10), nullable=False)  # Exemple : "2024-2025"

    # ── CONTACT ÉTUDIANT ────────────────────────────────────

    # nullable=True → ces infos peuvent être absentes
    email_etudiant     = Column(String(120), nullable=True)
    telephone_etudiant = Column(String(20),  nullable=True)

    # ── PARENT / TUTEUR ─────────────────────────────────────
    # Ces colonnes servent à notifier le parent lors des paiements

    nom_parent    = Column(String(60), nullable=False)
    prenom_parent = Column(String(60), nullable=False)

    # Seules les valeurs "Père", "Mère", "Tuteur" sont autorisées
    lien_parent   = Column(SAEnum(LienParentEnum), nullable=False)

    # Le téléphone du parent est obligatoire (pour les notifications SMS)
    telephone_parent = Column(String(20),  nullable=False)
    email_parent     = Column(String(120), nullable=True)

    # Photo de l'étudiant (base64 ou URL)
    photo            = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── RELATIONS ───────────────────────────────────────────

    # "Un étudiant appartient à UNE spécialité"
    specialite    = relationship("Specialite",   back_populates="etudiants")

    # "Un étudiant peut avoir PLUSIEURS paiements"
    # order_by → les paiements sont triés par numéro de tranche (1, 2, 3)
    paiements     = relationship(
        "Paiement",
        back_populates="etudiant",
        order_by="Paiement.numero_tranche"
    )

    # "Un étudiant peut avoir PLUSIEURS QR codes" (un par période)
    qr_codes      = relationship("QRCode",       back_populates="etudiant")

    # "Un étudiant peut avoir PLUSIEURS notifications" (envoyées à son parent)
    notifications = relationship("Notification", back_populates="etudiant")

    # ── PROPRIÉTÉS CALCULÉES ────────────────────────────────
    # Ces propriétés ne sont PAS des colonnes en base.
    # Elles sont calculées à la volée à partir des paiements liés.
    # @property → s'utilise comme un attribut : etudiant.cumul_verse

    @property
    def nom_complet(self) -> str:
        # Concatène nom + prénom
        return f"{self.nom} {self.prenom}"

    @property
    def cumul_verse(self) -> float:
        # Additionne tous les montants payés sur toutes les tranches
        return sum(float(p.montant_paye or 0) for p in self.paiements)

    @property
    def reste_global(self) -> float:
        # Total attendu pour l'année - ce qui a déjà été versé
        total_attendu = sum(float(p.montant_attendu or 0) for p in self.paiements)
        return total_attendu - self.cumul_verse


# ============================================================
#  MODÈLE 3 : Paiement
#  Table PostgreSQL : "paiements"
#  Feuille Excel correspondante : "Paiements"
# ============================================================
class Paiement(Base):

    __tablename__ = "paiements"

    # ── CONTRAINTE UNIQUE COMPOSITE ─────────────────────────
    # Un même étudiant ne peut pas avoir deux fois la tranche 1
    # (ou la tranche 2, ou la tranche 3).
    # Si on essaie d'insérer un doublon → PostgreSQL refusera.
    __table_args__ = (
        UniqueConstraint(
            "id_etudiant",
            "numero_tranche",
            name="uq_etudiant_tranche"
            # name= → nom de la contrainte dans PostgreSQL
        ),
    )

    id_paiement  = Column(String(20), primary_key=True)  # Exemple : "PAY-001"

    # Ces deux ForeignKey garantissent l'intégrité :
    # On ne peut pas enregistrer un paiement pour un étudiant
    # ou une spécialité qui n'existe pas en base.
    id_etudiant   = Column(String(20), ForeignKey("etudiants.id_etudiant"),      nullable=False)
    id_specialite = Column(String(20), ForeignKey("specialites.id_specialite"),  nullable=False)

    niveau         = Column(Integer, nullable=False)  # Niveau de l'étudiant concerné
    numero_tranche = Column(Integer, nullable=False)  # 1, 2 ou 3

    # Montant que l'étudiant DOIT payer pour cette tranche
    montant_attendu = Column(Numeric(12, 2), nullable=False)

    # Montant réellement reçu à la caisse (peut être inférieur → paiement PARTIEL)
    # default=0 → au départ, rien n'a été payé
    montant_paye    = Column(Numeric(12, 2), nullable=False, default=0)

    # Date réelle du paiement (remplie quand l'argent est reçu)
    # nullable=True → vide tant que rien n'est payé
    date_paiement = Column(String(10), nullable=True)

    # Date limite pour payer cette tranche (vient du calendrier des niveaux)
    date_limite   = Column(String(10), nullable=False)

    # Statut automatiquement mis à jour lors des paiements
    # default=EN_ATTENTE → toute nouvelle tranche commence "EN ATTENTE"
    statut = Column(
        SAEnum(StatutPaiementEnum),
        nullable=False,
        default=StatutPaiementEnum.EN_ATTENTE
    )

    # True si un QR code a été généré pour cet étudiant suite à ce paiement
    qr_code_genere        = Column(Boolean, nullable=False, default=False)

    # True si la notification a été envoyée au parent
    notif_parent_envoyee  = Column(Boolean, nullable=False, default=False)

    # Notes libres (ex: "Versement en 2 fois", "Reçu N°1234")
    observations = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── RELATIONS ───────────────────────────────────────────

    etudiant   = relationship("Etudiant",   back_populates="paiements")
    specialite = relationship("Specialite", back_populates="paiements")

    # Un paiement peut avoir plusieurs notifications (rappels, confirmations…)
    notifications = relationship("Notification", back_populates="paiement")

    # Un paiement peut déclencher la création d'un QR code
    qr_codes      = relationship("QRCode",       back_populates="paiement")

    # ── PROPRIÉTÉ CALCULÉE ──────────────────────────────────

    @property
    def reste_a_payer(self) -> float:
        # Ce qui reste à payer pour CETTE tranche uniquement
        return float(self.montant_attendu or 0) - float(self.montant_paye or 0)


# ============================================================
#  MODÈLE 4 : QRCode
#  Table PostgreSQL : "qr_codes"
#  Feuille Excel correspondante : "QR_Codes"
# ============================================================
class QRCode(Base):

    __tablename__ = "qr_codes"

    id_qrcode = Column(String(20), primary_key=True)  # Exemple : "QR-2024-001"

    # L'étudiant auquel appartient ce QR code
    id_etudiant   = Column(String(20), ForeignKey("etudiants.id_etudiant"),  nullable=False)

    # Le paiement qui a déclenché la génération du QR code
    # nullable=True → dans de rares cas, on peut créer un QR sans paiement précis
    id_paiement   = Column(String(20), ForeignKey("paiements.id_paiement"),  nullable=True)

    id_specialite = Column(String(20), nullable=False)
    niveau        = Column(Integer,    nullable=False)

    date_generation = Column(String(10), nullable=False)  # Date de création du QR
    valide_jusqua   = Column(String(10), nullable=False)  # Date d'expiration

    # ACTIF / EXPIRÉ / SUSPENDU
    statut = Column(SAEnum(StatutQREnum), nullable=False, default=StatutQREnum.ACTIF)

    # Données encodées à l'intérieur du QR code (format JSON en texte)
    # Exemple : {"matricule": "MAT-2024-INFO-001", "nom": "MBARGA Jean", ...}
    qr_data = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # ── RELATIONS ───────────────────────────────────────────

    etudiant = relationship("Etudiant", back_populates="qr_codes")
    paiement = relationship("Paiement", back_populates="qr_codes")


# ============================================================
#  MODÈLE 5 : Notification
#  Table PostgreSQL : "notifications"
#  Feuille Excel correspondante : "Notifications"
# ============================================================
class Notification(Base):

    __tablename__ = "notifications"

    id_notification = Column(String(20), primary_key=True)  # Exemple : "NOTIF-001"

    # Le paiement qui a déclenché cette notification
    id_paiement = Column(String(20), ForeignKey("paiements.id_paiement"), nullable=False)

    # L'étudiant concerné
    id_etudiant = Column(String(20), ForeignKey("etudiants.id_etudiant"), nullable=False)

    # Informations du parent (copiées ici pour garder un historique,
    # même si l'étudiant change de contact plus tard)
    nom_parent     = Column(String(60), nullable=False)
    contact_parent = Column(String(20), nullable=False)  # Numéro ou email

    # Type de message envoyé
    type_notification = Column(SAEnum(TypeNotifEnum), nullable=False)

    # Le texte complet du message envoyé au parent
    message    = Column(Text, nullable=False)

    # Date d'envoi (vide si pas encore envoyé)
    date_envoi = Column(String(10), nullable=True)

    # Canal utilisé : "Email", "SMS" ou "Email+SMS"
    canal = Column(String(20), nullable=False)

    # Résultat de l'envoi
    statut_envoi = Column(
        SAEnum(StatutNotifEnum),
        nullable=False,
        default=StatutNotifEnum.EN_ATTENTE
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    # ── RELATIONS ───────────────────────────────────────────

    etudiant = relationship("Etudiant", back_populates="notifications")
    paiement = relationship("Paiement", back_populates="notifications")


# ============================================================
#  MODÈLE 6 : CalendrierNiveau
#  Table PostgreSQL : "calendrier_niveaux"
#  Feuille Excel correspondante : "Calendrier_Niveaux"
# ============================================================
class CalendrierNiveau(Base):

    __tablename__ = "calendrier_niveaux"

    # Ici on utilise un ID entier auto-incrémenté
    # (PostgreSQL génère 1, 2, 3… automatiquement)
    id     = Column(Integer, primary_key=True, autoincrement=True)

    # unique=True → on ne peut pas avoir deux lignes pour le même niveau
    niveau = Column(Integer, nullable=False, unique=True)

    # Exemple : "Groupe A (N1 & N2)"
    groupe = Column(String(30), nullable=False)

    # Exemple : "Octobre"
    demarrage_academique = Column(String(20), nullable=False)

    # Dates limites des 3 tranches pour ce niveau
    tranche_1_limite = Column(String(30), nullable=False)  # Exemple : "31 Octobre"
    tranche_2_limite = Column(String(30), nullable=False)
    tranche_3_limite = Column(String(30), nullable=False)

    # Règle de démarrage pour ce niveau
    # Exemple : "Après validation N1 & N2"
    condition_demarrage = Column(Text, nullable=False)

    mois_debut = Column(String(15), nullable=False)  # Exemple : "Octobre"
    mois_fin   = Column(String(15), nullable=False)  # Exemple : "Mars"


# ============================================================
#  MODÈLE 7 : Utilisateur
#  Table PostgreSQL : "utilisateurs"
#  Authentification — comptes du personnel (pas des étudiants/parents)
# ============================================================
class Utilisateur(Base):

    __tablename__ = "utilisateurs"

    id_utilisateur = Column(String(20), primary_key=True)  # Exemple : "USR-001"

    # unique=True → un seul compte par email
    email = Column(String(120), nullable=False, unique=True)

    nom = Column(String(100), nullable=False)

    # Hash bcrypt — JAMAIS le mot de passe en clair
    mot_de_passe_hash = Column(String(255), nullable=False)

    role = Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.CAISSIER)

    # Un compte désactivé ne peut plus se connecter (sans le supprimer)
    actif = Column(Boolean, nullable=False, default=True)

    # Photo de profil (base64)
    photo = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)






class CodeAuthentification(Base):
    """
    Codes 2FA temporaires envoyés par email lors de la connexion.
    Expirés après 10 minutes, supprimés après utilisation.
    """
    __tablename__ = "codes_auth"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    id_utilisateur  = Column(String(20), ForeignKey("utilisateurs.id_utilisateur"), nullable=False)
    code            = Column(String(6), nullable=False)
    expire_a        = Column(DateTime, nullable=False)
    utilise         = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)