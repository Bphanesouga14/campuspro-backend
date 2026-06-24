


#  RÔLE : Traduire entre les deux "langages" du projet.
#
#  LE PROBLÈME :
#  La couche Domaine utilise des entités avec des Value Objects :
#    EtudiantDomaine(matricule=Matricule("MAT-2024-INFO-001"), ...)
#
#  La couche Infrastructure utilise des modèles SQLAlchemy :
#    EtudiantModel(matricule="MAT-2024-INFO-001", ...)
#
#  Ces deux représentations sont DIFFÉRENTES ON PURPOSE :
#  - L'entité domaine contient les règles métier
#  - Le modèle SQLAlchemy décrit comment stocker en base
#
#  Les Mappeurs font le pont dans les deux sens :
#    domaine_vers_model()  → pour INSERT / UPDATE en base
#    model_vers_domaine()  → pour reconstruire l'entité après SELECT
#
#  COUCHE : Infrastructure (connaît les deux mondes)
# ============================================================

from decimal import Decimal

# Modèles SQLAlchemy (Infrastructure)
from app.Infrastructure.database.models import (
    Specialite   as SpecialiteModel,
    Etudiant     as EtudiantModel,
    Paiement     as PaiementModel,
    QRCode       as QRCodeModel,
    Notification as NotificationModel,
    StatutPaiementEnum, StatutQREnum, StatutNotifEnum,
    TypeNotifEnum, SexeEnum, LienParentEnum,
)

# Entités du Domaine
from app.Domain.entities import (
    SpecialiteDomaine, EtudiantDomaine,
    PaiementDomaine, QRCodeDomaine, NotificationDomaine,
)

# Value Objects du Domaine
from app.Domain.value_objects import (
    Matricule, Montant, Email, Telephone,
    Sexe, LienParent, StatutPaiement, StatutQRCode,
    TypeNotification, Niveau,
)


# ════════════════════════════════════════════════════════════
#  MAPPEURS SPÉCIALITÉ
# ════════════════════════════════════════════════════════════

def specialite_model_vers_domaine(m: SpecialiteModel) -> SpecialiteDomaine:
    """
    Convertit un modèle SQLAlchemy Specialite
    en entité domaine SpecialiteDomaine.
    Appelé après un SELECT en base.
    """
    return SpecialiteDomaine(
        id_specialite    = m.id_specialite,
        code             = m.code,
        nom_specialite   = m.nom_specialite,
        departement      = m.departement,
        # Niveau(int) reconstruit l'Enum depuis la valeur entière stockée
        niveau           = Niveau(m.niveau),
        duree_ans        = m.duree_ans,
        annee_academique = m.annee_academique,
        # Montant(Decimal) reconstruit le Value Object depuis le Numeric SQL
        tranche_1        = Montant(Decimal(str(m.tranche_1))),
        date_limite_t1   = m.date_limite_t1,
        tranche_2        = Montant(Decimal(str(m.tranche_2))),
        date_limite_t2   = m.date_limite_t2,
        tranche_3        = Montant(Decimal(str(m.tranche_3))),
        date_limite_t3   = m.date_limite_t3,
    )


def specialite_domaine_vers_model(
    d: SpecialiteDomaine,
    model_existant: SpecialiteModel = None,
) -> SpecialiteModel:
    """
    Convertit une entité domaine SpecialiteDomaine
    en modèle SQLAlchemy Specialite.
    Appelé avant un INSERT ou UPDATE en base.

    model_existant = si on MET À JOUR une ligne existante,
    on passe le modèle déjà chargé pour ne pas créer un doublon.
    """
    # Si on met à jour → on modifie le modèle existant
    # Si on crée → on crée un nouveau modèle
    m = model_existant or SpecialiteModel()

    m.id_specialite    = d.id_specialite
    m.code             = d.code
    m.nom_specialite   = d.nom_specialite
    m.departement      = d.departement
    # .value → extrait l'entier depuis l'Enum (Niveau.UN → 1)
    m.niveau           = d.niveau.value
    m.duree_ans        = d.duree_ans
    m.annee_academique = d.annee_academique
    # .valeur → extrait le Decimal depuis le Value Object Montant
    m.tranche_1        = d.tranche_1.valeur
    m.date_limite_t1   = d.date_limite_t1
    m.tranche_2        = d.tranche_2.valeur
    m.date_limite_t2   = d.date_limite_t2
    m.tranche_3        = d.tranche_3.valeur
    m.date_limite_t3   = d.date_limite_t3
    m.total            = d.total.valeur

    return m


# ════════════════════════════════════════════════════════════
#  MAPPEURS ÉTUDIANT
# ════════════════════════════════════════════════════════════

def etudiant_model_vers_domaine(m: EtudiantModel) -> EtudiantDomaine:
    """
    Convertit un modèle SQLAlchemy Etudiant
    en entité domaine EtudiantDomaine.

    On reconstruit chaque Value Object depuis sa valeur brute.
    Si une valeur est absente (None) → on met None dans le domaine.
    """
    return EtudiantDomaine(
        id_etudiant        = m.id_etudiant,
        # Matricule() revalide le format au passage
        matricule          = Matricule(m.matricule),
        nom                = m.nom,
        prenom             = m.prenom,
        date_naissance     = m.date_naissance,
        # SexeEnum est l'enum SQLAlchemy, Sexe est l'enum Domaine
        # .value extrait "M" ou "F", Sexe() reconstruit l'enum domaine
        sexe               = Sexe(m.sexe.value if hasattr(m.sexe, 'value') else m.sexe),
        id_specialite      = m.id_specialite,
        code_specialite    = m.code_specialite,
        niveau             = Niveau(m.niveau),
        annee_academique   = m.annee_academique,
        # Email(str) ou None si absent
        email_etudiant     = Email(m.email_etudiant) if m.email_etudiant else None,
        telephone_etudiant = Telephone(m.telephone_etudiant) if m.telephone_etudiant else None,
        nom_parent         = m.nom_parent,
        prenom_parent      = m.prenom_parent,
        lien_parent        = LienParent(m.lien_parent.value if hasattr(m.lien_parent, 'value') else m.lien_parent),
        telephone_parent   = Telephone(m.telephone_parent) if m.telephone_parent else None,
        email_parent       = Email(m.email_parent) if m.email_parent else None,
        # Les paiements sont chargés séparément (évite le chargement inutile)
        paiements          = [],
    )


def etudiant_domaine_vers_model(
    d: EtudiantDomaine,
    model_existant: EtudiantModel = None,
) -> EtudiantModel:
    """
    Convertit une entité domaine EtudiantDomaine
    en modèle SQLAlchemy Etudiant.
    """
    m = model_existant or EtudiantModel()

    m.id_etudiant        = d.id_etudiant
    # str() appelle __str__ du Value Object → retourne la valeur brute
    m.matricule          = str(d.matricule)
    m.nom                = d.nom
    m.prenom             = d.prenom
    m.date_naissance     = d.date_naissance
    # SexeEnum("M") → crée l'enum SQLAlchemy depuis la valeur
    m.sexe               = SexeEnum(d.sexe.value)
    m.id_specialite      = d.id_specialite
    m.code_specialite    = d.code_specialite
    m.niveau             = d.niveau.value
    m.annee_academique   = d.annee_academique
    m.email_etudiant     = str(d.email_etudiant) if d.email_etudiant else None
    m.telephone_etudiant = str(d.telephone_etudiant) if d.telephone_etudiant else None
    m.nom_parent         = d.nom_parent
    m.prenom_parent      = d.prenom_parent
    m.lien_parent        = LienParentEnum(d.lien_parent.value) if d.lien_parent else LienParentEnum.TUTEUR
    m.telephone_parent   = str(d.telephone_parent) if d.telephone_parent else None
    m.email_parent       = str(d.email_parent) if d.email_parent else None

    return m


# ════════════════════════════════════════════════════════════
#  MAPPEURS PAIEMENT
# ════════════════════════════════════════════════════════════

def paiement_model_vers_domaine(m: PaiementModel) -> PaiementDomaine:
    """
    Convertit un modèle SQLAlchemy Paiement
    en entité domaine PaiementDomaine.
    """
    return PaiementDomaine(
        id_paiement     = m.id_paiement,
        id_etudiant     = m.id_etudiant,
        id_specialite   = m.id_specialite,
        niveau          = m.niveau,
        numero_tranche  = m.numero_tranche,
        montant_attendu = Montant(Decimal(str(m.montant_attendu))),
        montant_paye    = Montant(Decimal(str(m.montant_paye or 0))),
        date_paiement   = m.date_paiement,
        date_limite     = m.date_limite,
        statut          = StatutPaiement(
            m.statut.value if hasattr(m.statut, 'value') else m.statut
        ),
        qr_code_genere  = bool(m.qr_code_genere),
        notif_envoyee   = bool(m.notif_parent_envoyee),
        observations    = m.observations,
    )


def paiement_domaine_vers_model(
    d: PaiementDomaine,
    model_existant: PaiementModel = None,
) -> PaiementModel:
    """
    Convertit une entité domaine PaiementDomaine
    en modèle SQLAlchemy Paiement.
    """
    m = model_existant or PaiementModel()

    m.id_paiement          = d.id_paiement
    m.id_etudiant          = d.id_etudiant
    m.id_specialite        = d.id_specialite
    m.niveau               = d.niveau
    m.numero_tranche       = d.numero_tranche
    m.montant_attendu      = d.montant_attendu.valeur
    m.montant_paye         = d.montant_paye.valeur
    m.date_paiement        = d.date_paiement
    m.date_limite          = d.date_limite
    m.statut               = StatutPaiementEnum(d.statut.value)
    m.qr_code_genere       = d.qr_code_genere
    m.notif_parent_envoyee = d.notif_envoyee
    m.observations         = d.observations

    return m


# ════════════════════════════════════════════════════════════
#  MAPPEURS QR CODE
# ════════════════════════════════════════════════════════════

def qr_model_vers_domaine(m: QRCodeModel) -> QRCodeDomaine:
    return QRCodeDomaine(
        id_qrcode       = m.id_qrcode,
        id_etudiant     = m.id_etudiant,
        id_paiement     = m.id_paiement,
        id_specialite   = m.id_specialite,
        niveau          = m.niveau,
        date_generation = m.date_generation,
        valide_jusqua   = m.valide_jusqua,
        statut          = StatutQRCode(
            m.statut.value if hasattr(m.statut, 'value') else m.statut
        ),
        qr_data         = m.qr_data,
    )


def qr_domaine_vers_model(
    d: QRCodeDomaine,
    model_existant: QRCodeModel = None,
) -> QRCodeModel:
    m = model_existant or QRCodeModel()
    m.id_qrcode       = d.id_qrcode
    m.id_etudiant     = d.id_etudiant
    m.id_paiement     = d.id_paiement
    m.id_specialite   = d.id_specialite
    m.niveau          = d.niveau
    m.date_generation = d.date_generation
    m.valide_jusqua   = d.valide_jusqua
    m.statut          = StatutQREnum(d.statut.value)
    m.qr_data         = d.qr_data
    return m


# ════════════════════════════════════════════════════════════
#  MAPPEURS NOTIFICATION
# ════════════════════════════════════════════════════════════

def notif_model_vers_domaine(m: NotificationModel) -> NotificationDomaine:
    return NotificationDomaine(
        id_notification   = m.id_notification,
        id_paiement       = m.id_paiement,
        id_etudiant       = m.id_etudiant,
        nom_parent        = m.nom_parent,
        contact_parent    = m.contact_parent,
        type_notification = TypeNotification(
            m.type_notification.value if hasattr(m.type_notification, 'value')
            else m.type_notification
        ),
        message           = m.message,
        date_envoi        = m.date_envoi,
        canal             = m.canal,
        statut_envoi      = m.statut_envoi.value if hasattr(m.statut_envoi, 'value') else str(m.statut_envoi),
    )


def notif_domaine_vers_model(
    d: NotificationDomaine,
    model_existant: NotificationModel = None,
) -> NotificationModel:
    m = model_existant or NotificationModel()
    m.id_notification   = d.id_notification
    m.id_paiement       = d.id_paiement
    m.id_etudiant       = d.id_etudiant
    m.nom_parent        = d.nom_parent
    m.contact_parent    = d.contact_parent
    m.type_notification = TypeNotifEnum(d.type_notification.value)
    m.message           = d.message
    m.date_envoi        = d.date_envoi
    m.canal             = d.canal
    m.statut_envoi      = StatutNotifEnum(d.statut_envoi) if isinstance(d.statut_envoi, str) else StatutNotifEnum(d.statut_envoi.value)
    return m
