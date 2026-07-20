import pytest


class TestEtudiants:

    def test_liste_etudiants(self, client, headers):
        """Liste étudiants → 200."""
        res = client.get("/api/v1/etudiants", headers=headers)
        assert res.status_code == 200
        assert isinstance(res.json(), list)
        print(f"\n✅ Liste étudiants : {len(res.json())} étudiants")

    def test_etudiant_existant(self, client, headers):
        """Récupérer la liste puis tester le premier étudiant."""
        res_liste = client.get("/api/v1/etudiants", headers=headers)
        assert res_liste.status_code == 200
        etudiants = res_liste.json()
        if not etudiants:
            print(f"\n⚠ Aucun étudiant en base")
            return
        id_premier = etudiants[0]["id_etudiant"]
        res = client.get(f"/api/v1/etudiants/{id_premier}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "id_etudiant" in data
        assert "nom"         in data
        print(f"\n✅ Étudiant trouvé : {data['nom']} {data['prenom']}")

    def test_etudiant_inexistant(self, client, headers):
        """Étudiant inexistant → 404."""
        res = client.get(
            "/api/v1/etudiants/ETU-INEXISTANT-999",
            headers=headers
        )
        assert res.status_code == 404
        print(f"\n✅ Étudiant inexistant → 404")

    def test_etudiants_sans_token(self, client):
        """Sans token → 401 ou 403."""
        res = client.get("/api/v1/etudiants")
        assert res.status_code in [401, 403]
        print(f"\n✅ Sans token bloqué : {res.status_code}")

    def test_dashboard(self, client, headers):
        """Dashboard → 200."""
        res = client.get("/api/v1/dashboard", headers=headers)
        assert res.status_code == 200
        print(f"\n✅ Dashboard OK")