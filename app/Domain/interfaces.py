# Les contrats

# ============================================================
#  FICHIER : app/domain/interfaces.py
#
#  RÔLE : Définir les CONTRATS (interfaces) que la couche
#         Infrastructure devra obligatoirement respecter.
#
#  C'EST QUOI UNE INTERFACE ?
#  C'est une liste de méthodes que quelqu'un DOIT implémenter.
#  Comme un cahier des charges.
#
#  EXEMPLE CONCRET :
#  Le domaine dit : "Je veux pouvoir sauvegarder un étudiant,
#  le retrouver par son ID, le lister... mais JE NE SAIS PAS
#  si c'est PostgreSQL, MySQL ou un fichier texte."
#
#  → Le domaine définit le CONTRAT (ici)
#  → L'Infrastructure l'implémente (dans repositories/)
#
#  Ce mécanisme s'appelle "Inversion de dépendance" :
#  l'Infrastructure dépend du Domaine, jamais l'inverse.
#
#  En Python on utilise ABC (Abstract Base Class)
#  pour créer des interfaces.
#
#  COUCHE : Domaine (zéro dépendance externe)
# ============================================================

# ABC = Abstract Base Class : permet de définir des méthodes
# que les classes filles DOIVENT obligatoirement implémenter
from abc import ABC, abstractmethod
from typing import List, Optional

# On importe nos entités domaine
from app.Domain.entities import (
    EtudiantDomaine,
    PaiementDomaine,
    SpecialiteDomaine,
    QRCodeDomaine,
    NotificationDomaine,
    UtilisateurDomaine,
)


# ============================================================
#  INTERFACE : IEtudiantRepository
# ============================================================
class IEtudiantRepository(ABC):
    """
    Contrat pour la gestion des étudiants en base de données.

    La couche Infrastructure DOIT implémenter toutes ces méthodes.
    La couche Application utilise cette interface sans savoir
    si c'est PostgreSQL, MySQL ou autre chose derrière.
    """

    @abstractmethod
    async def sauvegarder(self, etudiant: EtudiantDomaine) -> EtudiantDomaine:
        """
        Crée ou met à jour un étudiant en base.
        Retourne l'étudiant sauvegardé (avec son ID généré si nouveau).
        """
        ...
        # Les "..." signifient "pas d'implémentation ici"
        # La classe fille (Repository) doit fournir le vrai code

    @abstractmethod
    async def trouver_par_id(self, id_etudiant: str) -> Optional[EtudiantDomaine]:
        """
        Cherche un étudiant par son ID.
        Retourne None s'il n'existe pas (pas d'exception).
        """
        ...

    @abstractmethod
    async def trouver_par_matricule(self, matricule: str) -> Optional[EtudiantDomaine]:
        """
        Cherche un étudiant par son matricule unique.
        Utile pour vérifier les doublons avant création.
        """
        ...

    @abstractmethod
    async def lister_tous(
        self,
        niveau: Optional[int] = None,
        id_specialite: Optional[str] = None,
        annee_academique: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[EtudiantDomaine]:
        """
        Liste les étudiants avec des filtres optionnels.
        Si aucun filtre → retourne tous les étudiants.
        skip/limit permettent la pagination (limit=None → pas de limite).
        """
        ...

    @abstractmethod
    async def supprimer(self, id_etudiant: str) -> bool:
        """
        Supprime un étudiant par son ID.
        Retourne True si supprimé, False s'il n'existait pas.
        """
        ...

    @abstractmethod
    async def existe(self, id_etudiant: str) -> bool:
        """
        Vérifie si un étudiant existe sans le charger complètement.
        Plus rapide qu'un trouver_par_id juste pour vérifier.
        """
        ...


# ============================================================
#  INTERFACE : IPaiementRepository
# ============================================================
class IPaiementRepository(ABC):
    """Contrat pour la gestion des paiements en base de données."""

    @abstractmethod
    async def sauvegarder(self, paiement: PaiementDomaine) -> PaiementDomaine:
        """Crée ou met à jour un paiement."""
        ...

    @abstractmethod
    async def trouver_par_id(self, id_paiement: str) -> Optional[PaiementDomaine]:
        """Cherche un paiement par son ID."""
        ...

    @abstractmethod
    async def lister_par_etudiant(self, id_etudiant: str) -> List[PaiementDomaine]:
        """
        Retourne toutes les tranches d'un étudiant,
        triées par numéro de tranche (1, 2, 3).
        """
        ...

    @abstractmethod
    async def lister_en_retard(self) -> List[PaiementDomaine]:
        """
        Retourne tous les paiements dont le statut est EN_RETARD.
        Utilisé pour les rappels aux parents.
        """
        ...

    @abstractmethod
    async def sauvegarder_tous(self, paiements: List[PaiementDomaine]) -> List[PaiementDomaine]:
        """
        Sauvegarde une liste de paiements en une seule opération.
        Utilisé lors de l'import Excel (plusieurs lignes d'un coup).
        """
        ...


# ============================================================
#  INTERFACE : ISpecialiteRepository
# ============================================================
class ISpecialiteRepository(ABC):
    """Contrat pour la gestion des spécialités en base de données."""

    @abstractmethod
    async def sauvegarder(self, specialite: SpecialiteDomaine) -> SpecialiteDomaine:
        ...

    @abstractmethod
    async def trouver_par_id(self, id_specialite: str) -> Optional[SpecialiteDomaine]:
        ...

    @abstractmethod
    async def lister_toutes(self, niveau: Optional[int] = None) -> List[SpecialiteDomaine]:
        ...

    @abstractmethod
    async def sauvegarder_toutes(self, specialites: List[SpecialiteDomaine]) -> List[SpecialiteDomaine]:
        """Sauvegarde en lot — utilisé lors de l'import Excel."""
        ...


# ============================================================
#  INTERFACE : IQRCodeRepository
# ============================================================
class IQRCodeRepository(ABC):
    """Contrat pour la gestion des QR codes en base de données."""

    @abstractmethod
    async def sauvegarder(self, qr_code: QRCodeDomaine) -> QRCodeDomaine:
        ...

    @abstractmethod
    async def trouver_actif_par_etudiant(self, id_etudiant: str) -> Optional[QRCodeDomaine]:
        """
        Retourne le QR code ACTIF d'un étudiant.
        Un étudiant ne peut avoir qu'un seul QR actif à la fois.
        """
        ...

    @abstractmethod
    async def trouver_dernier_par_etudiant(self, id_etudiant: str) -> Optional[QRCodeDomaine]:
        ...

    @abstractmethod
    async def lister_par_etudiant(self, id_etudiant: str) -> List[QRCodeDomaine]:
        """Retourne tout l'historique des QR codes d'un étudiant."""
        ...


# ============================================================
#  INTERFACE : INotificationRepository
# ============================================================
class INotificationRepository(ABC):
    """Contrat pour la gestion des notifications en base de données."""

    @abstractmethod
    async def sauvegarder(self, notification: NotificationDomaine) -> NotificationDomaine:
        ...

    @abstractmethod
    async def lister_par_etudiant(self, id_etudiant: str) -> List[NotificationDomaine]:
        ...

    @abstractmethod
    async def lister_non_envoyees(self) -> List[NotificationDomaine]:
        """
        Retourne les notifications en attente d'envoi.
        Utilisé par le service d'envoi automatique.
        """
        ...


# ============================================================
#  INTERFACE : INotificationService
# ============================================================
class INotificationService(ABC):
    """
    Contrat pour l'envoi réel des notifications (Email/SMS).

    ATTENTION : Ce n'est pas un Repository (pas de base de données).
    C'est un SERVICE EXTERNE.
    L'Infrastructure implémentera ça avec SMTP pour les emails
    et une API SMS pour les SMS.
    """

    @abstractmethod
    async def envoyer_email(
        self,
        destinataire: str,
        sujet: str,
        message: str,
    ) -> bool:
        """
        Envoie un email. Retourne True si envoyé avec succès.
        """
        ...

    @abstractmethod
    async def envoyer_sms(
        self,
        numero: str,
        message: str,
    ) -> bool:
        """
        Envoie un SMS. Retourne True si envoyé avec succès.
        """
        ...


# ============================================================
#  INTERFACE : IQRCodeService
# ============================================================
class IQRCodeService(ABC):
    """
    Contrat pour la génération d'images QR code.
    L'Infrastructure utilisera la bibliothèque 'qrcode'.
    """

    @abstractmethod
    async def generer(
        self,
        donnees: dict,
        id_etudiant: str,
    ) -> str:
        """
        Génère un QR code à partir des données fournies.
        Retourne le chemin vers l'image générée (ou base64).
        """
        ...


# ============================================================
#  INTERFACE : IUtilisateurRepository
# ============================================================
class IUtilisateurRepository(ABC):
    """Contrat pour la gestion des comptes utilisateurs (authentification)."""

    @abstractmethod
    async def sauvegarder(self, utilisateur: UtilisateurDomaine) -> UtilisateurDomaine:
        """Crée ou met à jour un utilisateur."""
        ...

    @abstractmethod
    async def trouver_par_id(self, id_utilisateur: str) -> Optional[UtilisateurDomaine]:
        ...

    @abstractmethod
    async def trouver_par_email(self, email: str) -> Optional[UtilisateurDomaine]:
        """Utilisé pour la connexion (login) et pour vérifier les doublons."""
        ...

    @abstractmethod
    async def lister_tous(self) -> List[UtilisateurDomaine]:
        ...
