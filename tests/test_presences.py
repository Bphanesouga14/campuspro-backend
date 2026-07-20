import pytest


class TestInfoQR:

    def test_info_qr_inexistant(self, client, headers):
        """QR inexistant → 404."""
        res = client.get(
            "/api/v1/presences/info-qr/QR-FAKE-999",
            headers=headers
        )
        assert res.status_code == 404
        print(f"\n✅ QR inexistant → 404")

    def test_info_qr_sans_token(self, client):
        """Sans token → 401."""
        res = client.get("/api/v1/presences/info-qr/QR-2024-001")
        assert res.status_code in [401, 403]
        print(f"\n✅ Sans token bloqué : {res.status_code}")

    def test_info_qr_premier_actif(self, client, headers):
        """Premier QR actif en base → infos complètes."""
        res_liste = client.get("/api/v1/qrcodes", headers=headers)
        if res_liste.status_code != 200:
            print(f"\n⚠ Impossible de lister les QR codes")
            return
        qrcodes = res_liste.json()
        actifs = [
            qr for qr in qrcodes
            if qr.get("statut", qr.get("statut_qr", "")) == "ACTIF"
        ]
        if not actifs:
            print(f"\n⚠ Aucun QR actif en base")
            return
        id_qr = actifs[0].get("id_qrcode", actifs[0].get("id"))
        res = client.get(
            f"/api/v1/presences/info-qr/{id_qr}",
            headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert "etudiant"  in data
        assert "statut_qr" in data
        assert data["statut_qr"] == "ACTIF"
        print(f"\n✅ QR actif : {data['etudiant']['nom_complet']}")


class TestScanPresence:

    def test_scan_sans_token(self, client):
        """Sans token → 401."""
        res = client.post("/api/v1/presences/scan", json={
            "id_qrcode":   "QR-2024-001",
            "id_etudiant": "ETU-2024-001"
        })
        assert res.status_code in [401, 403]
        print(f"\n✅ Scan sans token bloqué : {res.status_code}")

    def test_scan_corps_vide(self, client, headers):
        """Corps vide → 422."""
        res = client.post(
            "/api/v1/presences/scan",
            json={},
            headers=headers
        )
        assert res.status_code == 422
        print(f"\n✅ Corps vide → 422")

    def test_scan_qr_inexistant(self, client, headers):
        """QR inexistant → 404."""
        res = client.post("/api/v1/presences/scan", json={
            "id_qrcode":   "QR-FAKE-999",
            "id_etudiant": "ETU-2024-001"
        }, headers=headers)
        assert res.status_code in [404, 400]
        print(f"\n✅ QR inexistant bloqué : {res.status_code}")

    def test_scan_qr_inactif_refuse(self, client, headers):
        """QR INACTIF → 403."""
        res_liste = client.get("/api/v1/qrcodes", headers=headers)
        if res_liste.status_code != 200:
            return
        inactifs = [
            qr for qr in res_liste.json()
            if qr.get("statut", qr.get("statut_qr", "")) == "INACTIF"
        ]
        if not inactifs:
            print(f"\n⚠ Aucun QR inactif en base")
            return
        qr = inactifs[0]
        res = client.post("/api/v1/presences/scan", json={
            "id_qrcode":   qr.get("id_qrcode", qr.get("id")),
            "id_etudiant": qr.get("id_etudiant"),
        }, headers=headers)
        assert res.status_code == 403
        print(f"\n✅ QR inactif → 403 : {res.json()['detail']}")

    def test_scan_qr_actif_et_anti_doublon(self, client, headers):
        """QR ACTIF → présence enregistrée + anti-doublon."""
        res_liste = client.get("/api/v1/qrcodes", headers=headers)
        if res_liste.status_code != 200:
            return
        actifs = [
            qr for qr in res_liste.json()
            if qr.get("statut", qr.get("statut_qr", "")) == "ACTIF"
        ]
        if not actifs:
            print(f"\n⚠ Aucun QR actif — crée d'abord un paiement soldé")
            return
        qr = actifs[0]
        payload = {
            "id_qrcode":   qr.get("id_qrcode", qr.get("id")),
            "id_etudiant": qr.get("id_etudiant"),
        }
        # Premier scan
        res1 = client.post(
            "/api/v1/presences/scan",
            json=payload, headers=headers
        )
        assert res1.status_code in [200, 201]
        total1 = res1.json()["total_presences"]
        print(f"\n✅ Premier scan OK — total : {total1}")

        # Deuxième scan — anti-doublon
        res2 = client.post(
            "/api/v1/presences/scan",
            json=payload, headers=headers
        )
        assert res2.status_code in [200, 201]
        total2 = res2.json()["total_presences"]
        assert total2 == total1
        print(f"\n✅ Anti-doublon OK — total reste {total2}")


class TestStatsPresences:

    def test_stats_structure(self, client, headers):
        """Stats présences → structure correcte."""
        res = client.get(
            "/api/v1/presences/absences/stats",
            headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert "total_seances"   in data
        assert "total_etudiants" in data
        assert "en_alerte"       in data
        assert "etudiants"       in data
        print(f"\n✅ Stats OK — {data['total_etudiants']} étudiants, "
              f"{data['en_alerte']} en alerte")

    def test_taux_entre_0_et_100(self, client, headers):
        """Taux de présence entre 0 et 100."""
        res = client.get(
            "/api/v1/presences/absences/stats",
            headers=headers
        )
        assert res.status_code == 200
        for e in res.json()["etudiants"]:
            assert 0 <= e["taux_presence"] <= 100
        print(f"\n✅ Tous les taux sont valides")

    def test_stats_sans_token(self, client):
        """Sans token → 401."""
        res = client.get("/api/v1/presences/absences/stats")
        assert res.status_code in [401, 403]
        print(f"\n✅ Stats sans token bloquées : {res.status_code}")