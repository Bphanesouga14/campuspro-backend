


#  RÔLE : Cas d'usage de lecture (consultation).
#
#  Contient deux cas d'usage simples :
#  - ListerEtudiantsUseCase  → retourne la liste filtrée
#  - ObtenirEtudiantUseCase  → retourne un étudiant en détail
#
#  Ces cas d'usage sont plus simples car ils ne modifient
#  rien : ils lisent, transforment et retournent.
#
#  COUCHE : Application
# ============================================================

from typing import List, Optional
from decimal import Decimal

from app.Domain.interfaces    import IEtudiantRepository, IPaiementRepository, IQRCodeRepository
from app.Domain.entities      import EtudiantDomaine
from app.Domain.exceptions    import EtudiantIntrouvableError
from app.Application.DTOs.schemas import (
    EtudiantOut, EtudiantDetailOut, PaiementOut, QRCodeOut
)


class ListerEtudiantsUseCase:
    """
    Cas d'usage : Lister les étudiants avec filtres optionnels.

    Ce cas d'usage est simple car il ne fait que :
    1. Demander au repository la liste filtrée
    2. Convertir chaque entité en DTO
    3. Retourner la liste
    """

    def __init__(self, etudiant_repo: IEtudiantRepository):
        self._etudiant_repo = etudiant_repo

    async def executer(
        self,
        niveau:           Optional[int] = None,
        id_specialite:    Optional[str] = None,
        annee_academique: Optional[str] = None,
    ) -> List[EtudiantOut]:
        """
        Retourne la liste des étudiants.
        Si aucun filtre → retourne tous les étudiants.
        Si filtres → retourne uniquement ceux qui correspondent.
        """

        # Demande au repository (on ne sait pas si c'est PostgreSQL ou autre)
        etudiants = await self._etudiant_repo.lister_tous(
            niveau           = niveau,
            id_specialite    = id_specialite,
            annee_academique = annee_academique,
        )

        # Convertir chaque entité domaine en DTO de sortie
        # "List comprehension" = façon compacte d'écrire une boucle en Python
        return [self._vers_dto(e) for e in etudiants]

    def _vers_dto(self, etudiant: EtudiantDomaine) -> EtudiantOut:
        """Convertit une entité domaine en DTO de sortie."""
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
            email_etudiant     = str(etudiant.email_etudiant)     if etudiant.email_etudiant     else None,
            telephone_etudiant = str(etudiant.telephone_etudiant) if etudiant.telephone_etudiant else None,
            nom_parent         = etudiant.nom_parent,
            prenom_parent      = etudiant.prenom_parent,
            lien_parent        = etudiant.lien_parent.value if etudiant.lien_parent else "",
            telephone_parent   = str(etudiant.telephone_parent)   if etudiant.telephone_parent   else "",
            email_parent       = str(etudiant.email_parent)       if etudiant.email_parent       else None,
            cumul_verse        = etudiant.cumul_verse.valeur,
            reste_global       = etudiant.reste_global.valeur,
            est_a_jour         = etudiant.est_a_jour,
        )


class ObtenirEtudiantUseCase:
    """
    Cas d'usage : Obtenir le détail complet d'un étudiant.

    Retourne l'étudiant avec :
    - Toutes ses informations personnelles
    - La liste de toutes ses tranches de paiement
    - La liste de ses QR codes
    - Le cumul versé et le reste global
    """

    def __init__(
        self,
        etudiant_repo: IEtudiantRepository,
        paiement_repo: IPaiementRepository,
        qr_repo:       IQRCodeRepository,
    ):
        self._etudiant_repo = etudiant_repo
        self._paiement_repo = paiement_repo
        self._qr_repo       = qr_repo

    async def executer(self, id_etudiant: str) -> EtudiantDetailOut:
        """
        Retourne le détail complet d'un étudiant.
        Lève EtudiantIntrouvableError si l'ID est inconnu.
        """

        # ── Chercher l'étudiant ───────────────────────────────
        etudiant = await self._etudiant_repo.trouver_par_id(id_etudiant)
        if not etudiant:
            raise EtudiantIntrouvableError(id_etudiant)

        # ── Charger ses paiements ─────────────────────────────
        paiements = await self._paiement_repo.lister_par_etudiant(id_etudiant)

        # ── Charger ses QR codes ──────────────────────────────
        qr_codes  = await self._qr_repo.lister_par_etudiant(id_etudiant)

        # ── Attacher les paiements à l'entité ─────────────────
        # Cela permet à cumul_verse et reste_global de se calculer
        etudiant.paiements = paiements

        # ── Construire le DTO détaillé ────────────────────────
        return EtudiantDetailOut(
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
            email_etudiant     = str(etudiant.email_etudiant)     if etudiant.email_etudiant     else None,
            telephone_etudiant = str(etudiant.telephone_etudiant) if etudiant.telephone_etudiant else None,
            nom_parent         = etudiant.nom_parent,
            prenom_parent      = etudiant.prenom_parent,
            lien_parent        = etudiant.lien_parent.value if etudiant.lien_parent else "",
            telephone_parent   = str(etudiant.telephone_parent)   if etudiant.telephone_parent   else "",
            email_parent       = str(etudiant.email_parent)       if etudiant.email_parent       else None,
            cumul_verse        = etudiant.cumul_verse.valeur,
            reste_global       = etudiant.reste_global.valeur,
            est_a_jour         = etudiant.est_a_jour,
            # Convertir chaque paiement en DTO
            paiements = [
                PaiementOut(
                    id_paiement    = p.id_paiement,
                    id_etudiant    = p.id_etudiant,
                    id_specialite  = p.id_specialite,
                    niveau         = p.niveau,
                    numero_tranche = p.numero_tranche,
                    montant_attendu= p.montant_attendu.valeur,
                    montant_paye   = p.montant_paye.valeur,
                    reste_a_payer  = p.reste_a_payer.valeur,
                    date_paiement  = p.date_paiement,
                    date_limite    = p.date_limite,
                    statut         = p.statut.value,
                    qr_code_genere = p.qr_code_genere,
                    notif_envoyee  = p.notif_envoyee,
                    observations   = p.observations,
                )
                for p in paiements
            ],
            # Convertir chaque QR code en DTO
            qr_codes = [
                QRCodeOut(
                    id_qrcode      = q.id_qrcode,
                    id_etudiant    = q.id_etudiant,
                    id_specialite  = q.id_specialite,
                    niveau         = q.niveau,
                    date_generation= q.date_generation,
                    valide_jusqua  = q.valide_jusqua,
                    statut         = q.statut.value,
                    est_valide     = q.est_valide,
                    qr_data        = q.qr_data,
                )
                for q in qr_codes
            ],
        )
