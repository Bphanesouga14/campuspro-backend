import pytest


class TestLogin:

    def test_login_email_valide(self, client):
        """Email + mdp corrects → 200."""
        res = client.post("/api/v1/auth/login", json={
            "email":        "admin@gmail.com",
            "mot_de_passe": "01234567"
        })
        assert res.status_code == 200
        assert "message" in res.json()
        print(f"\n✅ Login OK : {res.json()['message']}")

    def test_login_mauvais_mot_de_passe(self, client):
        """Mauvais mot de passe → 401."""
        res = client.post("/api/v1/auth/login", json={
            "email":        "admin@gmail.com",
            "mot_de_passe": "mauvais_mdp"
        })
        assert res.status_code == 401
        print(f"\n✅ Mauvais mdp bloqué : {res.json()['detail']}")

    def test_login_email_inexistant(self, client):
        """Email inexistant → 401 ou 404."""
        res = client.post("/api/v1/auth/login", json={
            "email":        "inconnu@test.cm",
            "mot_de_passe": "test123"
        })
        assert res.status_code in [401, 404]
        print(f"\n✅ Email inconnu bloqué : {res.status_code}")

    def test_login_champs_vides(self, client):
        """Champs vides → 422."""
        res = client.post("/api/v1/auth/login", json={})
        assert res.status_code == 422
        print(f"\n✅ Champs vides → 422")

    def test_verifier_code_invalide(self, client):
        """Code 2FA invalide → 401."""
        res = client.post("/api/v1/auth/verifier", json={
            "email": "admin@gmail.com",
            "code":  "000000"
        })
        assert res.status_code in [400, 401]
        print(f"\n✅ Code invalide bloqué : {res.status_code}")

    def test_route_protegee_sans_token(self, client):
        """Route protégée sans token → 401 ou 403."""
        res = client.get("/api/v1/etudiants")
        assert res.status_code in [401, 403]
        print(f"\n✅ Route sans token bloquée : {res.status_code}")

    def test_route_protegee_token_invalide(self, client):
        """Token invalide → 401."""
        res = client.get("/api/v1/etudiants", headers={
            "Authorization": "Bearer token_faux_12345"
        })
        assert res.status_code == 401
        print(f"\n✅ Token invalide bloqué : {res.status_code}")