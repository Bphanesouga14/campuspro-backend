"""
Tests des paiements et QR codes — URLs correctes.
"""
import pytest


class TestPaiements:

    def test_retards_paiements(self, client, headers):
        """Liste des paiements en retard → 200."""
        res = client.get("/api/v1/paiements/retards", headers=headers)
        assert res.status_code == 200
        print(f"\n[OK] Retards paiements : {res.status_code}")

    def test_recu_pdf_inexistant(self, client, headers):
        """Reçu PDF paiement inexistant → 404."""
        res = client.get(
            "/api/v1/paiements/PAI-INEXISTANT-999/recu",
            headers=headers
        )
        assert res.status_code in [404, 422]
        print(f"\n[OK] Reçu inexistant → {res.status_code}")

    def test_payer_paiement_inexistant(self, client, headers):
        """Payer un paiement inexistant → 404."""
        res = client.post(
            "/api/v1/paiements/PAI-INEXISTANT-999/payer",
            json={"montant": 50000},
            headers=headers
        )
        assert res.status_code in [404, 422]
        print(f"\n[OK] Payer inexistant → {res.status_code}")

    def test_retards_sans_token(self, client):
        """Sans token → 401 ou 403."""
        res = client.get("/api/v1/paiements/retards")
        assert res.status_code in [401, 403]
        print(f"\n[OK] Retards sans token bloque : {res.status_code}")

    def test_payer_corps_vide(self, client, headers):
        """Corps vide → 422."""
        res = client.post(
            "/api/v1/paiements/PAI-001/payer",
            json={},
            headers=headers
        )
        assert res.status_code in [404, 422]
        print(f"\n[OK] Corps vide → {res.status_code}")

    def test_payer_premier_paiement(self, client, headers):
        """Tente un versement sur le premier paiement trouvé."""
        res_et = client.get("/api/v1/etudiants", headers=headers)
        if res_et.status_code != 200 or not res_et.json():
            print(f"\n[WARN] Aucun etudiant en base")
            return
        etudiants = res_et.json()

        # Chercher les paiements via retards
        res_retards = client.get(
            "/api/v1/paiements/retards", headers=headers)
        if res_retards.status_code != 200:
            print(f"\n[WARN] Route retards inaccessible")
            return

        retards = res_retards.json()
        # Accepter liste ou dict avec clé 'etudiants'
        if isinstance(retards, dict):
            retards = retards.get("etudiants", retards.get("paiements", []))

        if not retards:
            print(f"\n[WARN] Aucun paiement en retard")
            return

        premier = retards[0] if isinstance(retards, list) else None
        if not premier:
            print(f"\n[WARN] Structure retards inattendue")
            return

        id_pai = premier.get("id_paiement", premier.get("id", ""))
        if not id_pai:
            print(f"\n[WARN] Pas d'id_paiement dans : {list(premier.keys())}")
            return

        res = client.post(
            f"/api/v1/paiements/{id_pai}/payer",
            json={"montant": 1000},
            headers=headers
        )
        assert res.status_code in [200, 201, 400, 404, 422]
        print(f"\n[OK] Test paiement : {res.status_code}")


class TestQRCodes:

    def test_qr_code_etudiant_existant(self, client, headers):
        """QR code premier étudiant → 200 ou 404 si insolvable."""
        res_et = client.get("/api/v1/etudiants", headers=headers)
        assert res_et.status_code == 200
        etudiants = res_et.json()
        if not etudiants:
            print(f"\n[WARN] Aucun etudiant")
            return
        id_et = etudiants[0].get("id_etudiant")
        res = client.get(
            f"/api/v1/etudiants/{id_et}/qr-code",
            headers=headers
        )
        assert res.status_code in [200, 404]
        if res.status_code == 200:
            data = res.json()
            statut = data.get("statut", data.get("statut_qr", ""))
            print(f"\n[OK] QR code etudiant : statut={statut}")
        else:
            print(f"\n[WARN] Etudiant insolvable ou sans QR : 404")

    def test_qr_code_sans_token(self, client):
        """Sans token → 401 ou 403."""
        res = client.get("/api/v1/etudiants/ETU-2024-001/qr-code")
        assert res.status_code in [401, 403]
        print(f"\n[OK] QR sans token bloque : {res.status_code}")

    def test_qr_code_etudiant_inexistant(self, client, headers):
        """QR code étudiant inexistant → 404."""
        res = client.get(
            "/api/v1/etudiants/ETU-INEXISTANT-999/qr-code",
            headers=headers
        )
        assert res.status_code in [404, 422]
        print(f"\n[OK] QR etudiant inexistant → {res.status_code}")

    def test_qr_image_etudiant(self, client, headers):
        """Image QR code premier étudiant → 200 ou 404."""
        res_et = client.get("/api/v1/etudiants", headers=headers)
        if res_et.status_code != 200 or not res_et.json():
            return
        id_et = res_et.json()[0].get("id_etudiant")
        res = client.get(
            f"/api/v1/etudiants/{id_et}/qr-code/image",
            headers=headers
        )
        assert res.status_code in [200, 404]
        if res.status_code == 200:
            assert res.headers.get("content-type", "").startswith("image")
            print(f"\n[OK] Image QR OK : {res.headers['content-type']}")
        else:
            print(f"\n[WARN] Pas d'image QR : 404")

    def test_carte_etudiant_pdf(self, client, headers):
        """Carte étudiant PDF premier étudiant → 200 ou 404."""
        res_et = client.get("/api/v1/etudiants", headers=headers)
        if res_et.status_code != 200 or not res_et.json():
            return
        id_et = res_et.json()[0].get("id_etudiant")
        res = client.get(
            f"/api/v1/etudiants/{id_et}/carte",
            headers=headers
        )
        assert res.status_code in [200, 404, 500]
        if res.status_code == 200:
            ct = res.headers.get("content-type", "")
            assert "pdf" in ct
            print(f"\n[OK] Carte PDF OK : {len(res.content)} octets")
        else:
            print(f"\n[WARN] Carte PDF : {res.status_code}")

    def test_qr_actif_scan_accepte(self, client, headers):
        """
        Trouve un QR actif via l'endpoint qr-code
        et vérifie qu'il peut être scanné.
        """
        res_et = client.get("/api/v1/etudiants", headers=headers)
        if res_et.status_code != 200:
            return

        for etudiant in res_et.json():
            id_et = etudiant.get("id_etudiant")
            res_qr = client.get(
                f"/api/v1/etudiants/{id_et}/qr-code",
                headers=headers
            )
            if res_qr.status_code != 200:
                continue

            data   = res_qr.json()
            statut = data.get("statut", data.get("statut_qr", ""))
            id_qr  = data.get("id_qrcode", data.get("id", ""))

            if statut != "ACTIF" or not id_qr:
                continue

            # Scanner ce QR actif
            res_scan = client.post(
                "/api/v1/presences/scan",
                json={"id_qrcode": id_qr, "id_etudiant": id_et},
                headers=headers
            )
            assert res_scan.status_code in [200, 201]
            data_scan = res_scan.json()
            assert "total_presences" in data_scan
            print(f"\n[OK] Scan QR actif : {data_scan['message']}")
            return

        print(f"\n[WARN] Aucun QR actif trouve pour tester le scan")

    def test_qr_inactif_scan_refuse(self, client, headers):
        """
        Trouve un QR inactif via l'endpoint qr-code
        et vérifie que le scan est refusé (403).
        """
        res_et = client.get("/api/v1/etudiants", headers=headers)
        if res_et.status_code != 200:
            return

        for etudiant in res_et.json():
            id_et = etudiant.get("id_etudiant")
            res_qr = client.get(
                f"/api/v1/etudiants/{id_et}/qr-code",
                headers=headers
            )
            if res_qr.status_code != 200:
                continue

            data   = res_qr.json()
            statut = data.get("statut", data.get("statut_qr", ""))
            id_qr  = data.get("id_qrcode", data.get("id", ""))

            if statut != "INACTIF" or not id_qr:
                continue

            # Scanner ce QR inactif
            res_scan = client.post(
                "/api/v1/presences/scan",
                json={"id_qrcode": id_qr, "id_etudiant": id_et},
                headers=headers
            )
            assert res_scan.status_code == 403
            print(f"\n[OK] QR inactif refuse → 403")
            return

        print(f"\n[WARN] Aucun QR inactif trouve pour tester")