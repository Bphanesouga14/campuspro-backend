#Traducteur Modèle SQLAlchemy ↔ Entité Domaine

#  RÔLE : Traduire entre deux "langages" :
#    - Modèle SQLAlchemy  (objet technique lié à la BDD)
#    - Entité Domaine     (objet métier pur)
#
#  POURQUOI CE FICHIER EXISTE-T-IL ?
#  Le Domaine ne connaît pas SQLAlchemy.
#  L'Infrastructure ne doit pas "contaminer" le Domaine.
#  Le Mapper fait le pont entre les deux mondes.
#
#  ANALOGIE :
#  Imaginez deux personnes qui parlent des langues différentes.
#  L'une parle "SQLAlchemy" (tables, colonnes, FK...).
#  L'autre parle "Domaine" (Matricule, Montant, Niveau...).
#  Le Mapper est l'interprète entre les deux.
#
#  DEUX DIRECTIONS :
#  modele_vers_domaine() → quand on LIT depuis la base
#  domaine_vers_modele() → quand on ÉCRIT vers la base
#
#  COUCHE : Infrastructure
# ============================================================

from decimal import Decimal

# Modèles SQLAlchemy (objets liés à la base de données)
from app.Infrastructure.database.models import (
    Specialite   as SpecialiteModele,
    Etudiant     as EtudiantModele,
    Paiement     as PaiementModele,
    QRCode       as QRCodeModele,
    Notification as NotificationModele,
    StatutPaiementEnum, StatutQREnum, StatutNotifEnum,
    TypeNotifEnum, SexeEnum, LienParentEnum,
)

# Entités Domaine (objets métier purs)
from app.Domain.entities import (
    SpecialiteDomaine,
    EtudiantDomaine,
    PaiementDomaine,
    QRCodeDomaine,
    NotificationDomaine,
)

# Value Objects et Enums du Domaine
from app.Domain.value_objects import (
    Matricule, Montant, Email, Telephone,
    Sexe, LienParent, StatutPaiement, StatutQRCode,
    TypeNotification, Niveau,
)


# ════════════════════════════════════════════════════════════
#  MAPPER : SPÉCIALITÉ
# ════════════════════════════════════════════════════════════

def specialite_modele_vers_domaine(m: SpecialiteModele) -> SpecialiteDomaine:
    """
    Traduit un objet SQLAlchemy Specialite
    en entité Domaine SpecialiteDomaine.

    Appelé quand on LIT une spécialité depuis PostgreSQL.
    """
    return SpecialiteDomaine(
        id_specialite    = m.id_specialite,
        code             = m.code,
        nom_specialite   = m.nom_specialite,
        departement      = m.departement,
        # Niveau(m.niveau) convertit l'entier 1 en Niveau.UN, 2 en Niveau.DEUX...
        niveau           = Niveau(m.niveau),
        duree_ans        = m.duree_ans,
        annee_academique = m.annee_academique,
        # Montant() construit le Value Object depuis le Decimal stocké en base
        tranche_1        = Montant(Decimal(str(m.tranche_1))),
        date_limite_t1   = m.date_limite_t1,
        tranche_2        = Montant(Decimal(str(m.tranche_2))),
        date_limite_t2   = m.date_limite_t2,
        tranche_3        = Montant(Decimal(str(m.tranche_3))),
        date_limite_t3   = m.date_limite_t3,
    )


def specialite_domaine_vers_modele(
    d: SpecialiteDomaine,
    modele_existant: SpecialiteModele = None,
) -> SpecialiteModele:
    """
    Traduit une entité Domaine SpecialiteDomaine
    en objet SQLAlchemy Specialite.

    Appelé quand on ÉCRIT une spécialité dans PostgreSQL.

    modele_existant : si fourni, on met à jour cet objet
                      (UPDATE). Sinon on crée un nouveau (INSERT).
    """
    # Si on a un modèle existant → UPDATE (on modifie ses attributs)
    # Sinon → INSERT (on crée un nouvel objet)
    m = modele_existant or SpecialiteModele()

    m.id_specialite    = d.id_specialite
    m.code             = d.code
    m.nom_specialite   = d.nom_specialite
    m.departement      = d.departement
    # .value extrait l'entier depuis l'enum : Niveau.UN.value → 1
    m.niveau           = d.niveau.value
    m.duree_ans        = d.duree_ans
    m.annee_academique = d.annee_academique
    # .valeur extrait le Decimal depuis le Value Object Montant
    m.tranche_1        = d.tranche_1.valeur
    m.date_limite_t1   = d.date_limite_t1
    m.tranche_2        = d.tranche_2.valeur
    m.date_limite_t2   = d.date_limite_t2
    m.tranche_3        = d.tranche_3.valeur
    m.date_limite_t3   = d.date_limite_t3
    m.total            = d.total.valeur

    return m


# ════════════════════════════════════════════════════════════
#  MAPPER : ÉTUDIANT
# ════════════════════════════════════════════════════════════

def etudiant_modele_vers_domaine(m: EtudiantModele) -> EtudiantDomaine:
    """
    Traduit un objet SQLAlchemy Etudiant en entité Domaine.
    Appelé quand on LIT un étudiant depuis PostgreSQL.
    """
    return EtudiantDomaine(
        id_etudiant  = m.id_etudiant,
        # Matricule() reconstruit le Value Object depuis le string stocké
        matricule    = Matricule(m.matricule),
        nom          = m.nom,
        prenom       = m.prenom,
        date_naissance = m.date_naissance,
        # SexeEnum "M" → Sexe.MASCULIN via la correspondance d'enum
        sexe         = Sexe(m.sexe.value if hasattr(m.sexe, 'value') else m.sexe),
        id_specialite    = m.id_specialite,
        code_specialite  = m.code_specialite,
        niveau           = Niveau(m.niveau),
        annee_academique = m.annee_academique,
        # Pour les champs optionnels : si None → None, sinon on construit le Value Object
        email_etudiant     = Email(m.email_etudiant) if m.email_etudiant else None,
        telephone_etudiant = Telephone(m.telephone_etudiant) if m.telephone_etudiant else None,
        nom_parent         = m.nom_parent,
        prenom_parent      = m.prenom_parent,
        lien_parent        = LienParent(m.lien_parent.value if hasattr(m.lien_parent, 'value') else m.lien_parent),
        telephone_parent   = Telephone(m.telephone_parent) if m.telephone_parent else None,
        email_parent       = Email(m.email_parent) if m.email_parent else None,
        # Les paiements sont chargés séparément (pas dans ce mapper)
        paiements          = [],
    )


def etudiant_domaine_vers_modele(
    d: EtudiantDomaine,
    modele_existant: EtudiantModele = None,
) -> EtudiantModele:
    """
    Traduit une entité Domaine EtudiantDomaine en objet SQLAlchemy.
    Appelé quand on ÉCRIT un étudiant dans PostgreSQL.
    """
    m = modele_existant or EtudiantModele()

    m.id_etudiant        = d.id_etudiant
    # str(d.matricule) appelle __str__ du Value Object → "MAT-2024-INFO-001"
    m.matricule          = str(d.matricule)
    m.nom                = d.nom
    m.prenom             = d.prenom
    m.date_naissance     = d.date_naissance
    # d.sexe.value → "M" ou "F"
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
#  MAPPER : PAIEMENT
# ════════════════════════════════════════════════════════════

def paiement_modele_vers_domaine(m: PaiementModele) -> PaiementDomaine:
    """Traduit un objet SQLAlchemy Paiement en entité Domaine."""
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
        # StatutPaiementEnum "PAYÉ" → StatutPaiement.PAYE
        statut          = StatutPaiement(
            m.statut.value if hasattr(m.statut, 'value') else m.statut
        ),
        qr_code_genere  = m.qr_code_genere,
        notif_envoyee   = m.notif_parent_envoyee,
        observations    = m.observations,
    )


def paiement_domaine_vers_modele(
    d: PaiementDomaine,
    modele_existant: PaiementModele = None,
) -> PaiementModele:
    """Traduit une entité Domaine PaiementDomaine en objet SQLAlchemy."""
    m = modele_existant or PaiementModele()

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
#  MAPPER : QR CODE
# ════════════════════════════════════════════════════════════

def qrcode_modele_vers_domaine(m: QRCodeModele) -> QRCodeDomaine:
    """Traduit un objet SQLAlchemy QRCode en entité Domaine."""
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


def qrcode_domaine_vers_modele(
    d: QRCodeDomaine,
    modele_existant: QRCodeModele = None,
) -> QRCodeModele:
    """Traduit une entité Domaine QRCodeDomaine en objet SQLAlchemy."""
    m = modele_existant or QRCodeModele()

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
#  MAPPER : NOTIFICATION
# ════════════════════════════════════════════════════════════

def notification_modele_vers_domaine(m: NotificationModele) -> NotificationDomaine:
    """Traduit un objet SQLAlchemy Notification en entité Domaine."""
    return NotificationDomaine(
        id_notification   = m.id_notification,
        id_paiement       = m.id_paiement,
        id_etudiant       = m.id_etudiant,
        nom_parent        = m.nom_parent,
        contact_parent    = m.contact_parent,
        type_notification = TypeNotification(
            m.type_notification.value if hasattr(m.type_notification, 'value') else m.type_notification
        ),
        message           = m.message,
        date_envoi        = m.date_envoi,
        canal             = m.canal,
        statut_envoi      = m.statut_envoi.value if hasattr(m.statut_envoi, 'value') else m.statut_envoi,
    )


def notification_domaine_vers_modele(
    d: NotificationDomaine,
    modele_existant: NotificationModele = None,
) -> NotificationModele:
    """Traduit une entité Domaine NotificationDomaine en objet SQLAlchemy."""
    m = modele_existant or NotificationModele()

    m.id_notification  = d.id_notification
    m.id_paiement      = d.id_paiement
    m.id_etudiant      = d.id_etudiant
    m.nom_parent       = d.nom_parent
    m.contact_parent   = d.contact_parent
    m.type_notification= TypeNotifEnum(d.type_notification.value)
    m.message          = d.message
    m.date_envoi       = d.date_envoi
    m.canal            = d.canal
    m.statut_envoi     = StatutNotifEnum(d.statut_envoi)

    return m
