#Route d'import Excel



#  RÔLE : Endpoint HTTP pour l'upload et l'import du fichier Excel.
#
#  ROUTE DÉFINIE :
#  POST /api/v1/import/excel → Upload + import du fichier SIGC
#
#  COMMENT FONCTIONNE L'UPLOAD DE FICHIER EN FASTAPI ?
#  Le client envoie le fichier au format "multipart/form-data"
#  (le même format qu'un formulaire HTML avec <input type="file">).
#  FastAPI le reçoit via UploadFile.
#
#  COUCHE : Présentation
# ============================================================

# UploadFile = objet FastAPI représentant un fichier uploadé
# File = décorateur pour déclarer qu'un paramètre est un fichier
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from app.Application.use_cases.import_use_cases import ImporterExcelUseCase
from app.Application.DTOs.schemas import ImportExcelReponseDTO
from app.Domain.exceptions import FichierExcelInvalideError, ImportExcelError
from app.Presentation.dependencies import get_importer_excel_uc


router = APIRouter(tags=["Import Excel"])


# ============================================================
#  ROUTE UNIQUE : Importer le fichier Excel
#  POST /api/v1/import/excel
# ============================================================
@router.post(
    "/import/excel",
    response_model=ImportExcelReponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Importer le fichier Excel SIGC en base de données",
    description="""
Upload et importe le fichier **GestionScolaire_SIGC.xlsx** en base PostgreSQL.

**Ordre d'import (respecte les dépendances) :**
1. Spécialités
2. Étudiants
3. Paiements
4. QR Codes
5. Notifications

**Comportement :**
- Si un enregistrement existe déjà → mise à jour (UPDATE)
- Si un enregistrement est nouveau → insertion (INSERT)
- Si une ligne est en erreur → elle est ignorée, les autres continuent

**Réponse :**
```json
{
  "succes": true,
  "message": "Import terminé avec succès",
  "total_lignes": 42,
  "resultats": [
    {"feuille": "Specialites", "inseres": 10, "mis_a_jour": 0, "erreurs": 0},
    {"feuille": "Etudiants",   "inseres": 10, "mis_a_jour": 0, "erreurs": 0},
    ...
  ]
}
```
    """,
)
async def importer_excel(
    # UploadFile = le fichier envoyé par le client
    # File(...) = champ obligatoire (les ... signifient "requis")
    # description = texte affiché dans Swagger
    fichier: UploadFile = File(
        ...,
        description="Fichier GestionScolaire_SIGC.xlsx"
    ),
    use_case: ImporterExcelUseCase = Depends(get_importer_excel_uc),
):
    """
    Reçoit le fichier Excel, lit son contenu en bytes,
    et passe ces bytes au use case pour traitement.

    La route ne sait pas comment lire Excel.
    Elle délègue tout au use case ImporterExcelUseCase.
    """

    # ── Étape 1 : Lire le contenu du fichier en mémoire ─────
    # await fichier.read() lit tous les bytes du fichier uploadé
    # C'est comme faire Ctrl+A puis Copier sur le fichier
    contenu = await fichier.read()

    # ── Étape 2 : Vérification basique de la taille ─────────
    # Un fichier vide = problème
    if len(contenu) == 0:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "Le fichier est vide.",
        )

    # ── Étape 3 : Appeler le use case ───────────────────────
    try:
        return await use_case.executer(
            fichier_bytes = contenu,
            nom_fichier   = fichier.filename or "fichier.xlsx",
        )

    except FichierExcelInvalideError as e:
        # Le fichier n'est pas un Excel valide
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = str(e),
        )
    except ImportExcelError as e:
        # Erreur générale pendant l'import
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail      = str(e),
        )
