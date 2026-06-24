

#
#  RÔLE : Classe mère commune à tous les repositories.
#
#  POURQUOI UNE CLASSE MÈRE ?
#  Tous nos repositories ont besoin de la même chose :
#  une session de base de données.
#  Au lieu de répéter self._session dans chaque fichier,
#  on le met UNE SEULE FOIS ici et tous les autres en héritent.
#
#  PRINCIPE : DRY — Don't Repeat Yourself (Ne te répète pas).
#
#  COUCHE : Infrastructure
# ============================================================

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """
    Classe mère de tous les repositories SQLAlchemy.

    Contient uniquement la session de base de données,
    partagée par toutes les opérations du repository.
    """

    def __init__(self, session: AsyncSession):
        # La session est injectée depuis l'extérieur (par FastAPI).
        # Le repository ne crée JAMAIS lui-même la session.
        # C'est l'injection de dépendance qui s'en charge.
        self._session = session
