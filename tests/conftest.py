"""
Configuration globale des tests CampusPro.
Utilise PyJWT (même bibliothèque que le backend) pour générer le token.
"""

import warnings
import pytest

import pytest
import os
import jwt                        # ← PyJWT (pas jose)
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv()



# Remplace aussi dans generer_token_test()
def generer_token_test():
    import jwt, os
    from dotenv import load_dotenv
    load_dotenv()
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
    ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")
    payload = {
        "sub":  "USR-D5BCA7E4",
        "role": "ADMIN",
        "exp":  datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def pytest_configure(config):
    """Filtre les DeprecationWarning de SQLAlchemy et datetime."""
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="sqlalchemy"
    )
    warnings.filterwarnings(
        "ignore",
        message=".*utcnow.*",
        category=DeprecationWarning,
    )


@pytest.fixture(scope="session")
def client():
    """Client HTTP avec startup complet."""
    from main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def token():
    """Token JWT admin valide sans 2FA."""
    return generer_token_test()


@pytest.fixture(scope="session")
def headers(token):
    """Headers Authorization avec token valide."""
    return {"Authorization": f"Bearer {token}"}




@pytest.fixture(scope="session", autouse=True)
def ignorer_warnings_async():
    """Ignore les warnings de fermeture async SQLAlchemy."""
    warnings.filterwarnings(
        "ignore",
        category=pytest.PytestUnraisableExceptionWarning
    )


    # Tous les tests avec affichage détaillé
'''pytest tests/ -v'''

'''$env:PYTHONIOENCODING = "utf-8"
pytest tests/ -v --tb=short'''

'''pytest tests/ -v -s'''
'''pytest tests/ -v -s --tb=short'''

# Un seul fichier
'''pytest tests/test_presences.py -v -s'''

# Une seule classe
'''pytest tests/test_presences.py::TestScanPresence -v -s'''

# Un seul test
'''pytest tests/test_presences.py::TestScanPresence::test_scan_valide_puis_anti_doublon -v -s'''