"""
Tests des QR codes via la route /etudiants/{id}/qr-code.
"""
import pytest


def get_premier_etudiant(client, headers):
    """Retourne le premier étudiant en base."""
    res = client.get("/api/v1/etudiants", headers=headers)
    if res.status_code != 200 or not res.json():
        return None
    return res.json()[0]


def get_qr_etudiant(client, headers, id_etudiant):
    """Retourne le QR code d'un étudiant."""
    res = client.get(
        f"/api/v1/etudiants/{id_etudiant}/qr-code",
        headers=headers
    )
    return res


class TestListeQRCodes:

    def test_qr_premier_etudiant(self, client, headers):
        """QR code du premier étudiant → 200 ou 404."""
        etudiant = get_premier_etudiant(client, headers)
        if not etudiant:
            print("\n[WARN] Aucun etudiant en base")
            return
        id_et = etudiant["id_etudiant"]
        res = get_qr_etudiant(client, headers, id_et)
        assert res.status_code in [200, 404]
        if res.status_code == 200:
            data = res.json()
            assert "id_qrcode" in data or "id" in data
            statut = data.get("statut", data.get("statut_qr", ""))
            print(f"\n[OK] QR etudiant {id_et} : statut={statut}")
        else:
            print(f"\n[WARN] Etudiant {id_et} sans QR (insolvable)")

    def test_qr_sans_token(self, client):
        """Sans token → 401 ou 403."""
        res = client.get(
            "/api/v1/etudiants/ETU-2024-001/qr-code"
        )
        assert res.status_code in [401, 403]
        print(f"\n[OK] QR sans token bloque : {res.status_code}")

    def test_qr_etudiant_inexistant(self, client, headers):
        """QR étudiant inexistant → 404."""
        res = get_qr_etudiant(client, headers, "ETU-INEXISTANT-999")
        assert res.status_code in [404, 422]
        print(f"\n[OK] QR inexistant → {res.status_code}")

    def test_qr_structure(self, client, headers):
        """QR code a les champs obligatoires."""
        etudiants = client.get(
            "/api/v1/etudiants", headers=headers).json()
        for e in etudiants:
            res = get_qr_etudiant(client, headers, e["id_etudiant"])
            if res.status_code == 200:
                data = res.json()
                assert "id_qrcode" in data or "id" in data
                assert "statut"    in data or "statut_qr" in data
                assert "id_etudiant" in data
                print(f"\n[OK] Structure QR valide")
                return
        print(f"\n[WARN] Aucun QR accessible pour tester la structure")


class TestStatutQRCode:

    def _trouver_qr_par_statut(self, client, headers, statut_cherche):
        """Trouve le premier QR avec le statut donné."""
        etudiants = client.get(
            "/api/v1/etudiants", headers=headers).json()
        for e in etudiants:
            res = get_qr_etudiant(client, headers, e["id_etudiant"])
            if res.status_code != 200:
                continue
            data   = res.json()
            statut = data.get("statut", data.get("statut_qr", ""))
            if statut == statut_cherche:
                return data, e["id_etudiant"]
        return None, None

    def test_info_qr_premier_actif(self, client, headers):
        """Premier QR ACTIF → statut = ACTIF."""
        qr, id_et = self._trouver_qr_par_statut(client, headers, "ACTIF")
        if not qr:
            print(f"\n[WARN] Aucun QR actif en base")
            return
        id_qr = qr.get("id_qrcode", qr.get("id"))
        res = client.get(
            f"/api/v1/presences/info-qr/{id_qr}",
            headers=headers
        )
        assert res.status_code == 200
        assert res.json()["statut_qr"] == "ACTIF"
        print(f"\n[OK] QR actif confirme : {id_qr}")

    def test_info_qr_premier_inactif(self, client, headers):
        """Premier QR INACTIF → statut = INACTIF."""
        qr, id_et = self._trouver_qr_par_statut(client, headers, "INACTIF")
        if not qr:
            print(f"\n[WARN] Aucun QR inactif en base")
            return
        id_qr = qr.get("id_qrcode", qr.get("id"))
        res = client.get(
            f"/api/v1/presences/info-qr/{id_qr}",
            headers=headers
        )
        assert res.status_code == 200
        assert res.json()["statut_qr"] == "INACTIF"
        print(f"\n[OK] QR inactif confirme : {id_qr}")

    def test_scan_qr_inactif_refuse(self, client, headers):
        """QR INACTIF → scan refusé 403."""
        qr, id_et = self._trouver_qr_par_statut(client, headers, "INACTIF")
        if not qr:
            print(f"\n[WARN] Aucun QR inactif pour tester")
            return
        res = client.post(
            "/api/v1/presences/scan",
            json={
                "id_qrcode":   qr.get("id_qrcode", qr.get("id")),
                "id_etudiant": id_et,
            },
            headers=headers
        )
        assert res.status_code == 403
        print(f"\n[OK] QR inactif refuse → 403")

    def test_scan_qr_actif_accepte(self, client, headers):
        """QR ACTIF → scan accepté 200 ou 201."""
        qr, id_et = self._trouver_qr_par_statut(client, headers, "ACTIF")
        if not qr:
            print(f"\n[WARN] Aucun QR actif pour tester")
            return
        res = client.post(
            "/api/v1/presences/scan",
            json={
                "id_qrcode":   qr.get("id_qrcode", qr.get("id")),
                "id_etudiant": id_et,
            },
            headers=headers
        )
        assert res.status_code in [200, 201]
        data = res.json()
        assert "total_presences" in data
        print(f"\n[OK] Scan QR actif : {data['message']}")

    def test_anti_doublon_meme_jour(self, client, headers):
        """Scanner deux fois le même jour → total inchangé."""
        qr, id_et = self._trouver_qr_par_statut(client, headers, "ACTIF")
        if not qr:
            print(f"\n[WARN] Aucun QR actif pour tester anti-doublon")
            return
        payload = {
            "id_qrcode":   qr.get("id_qrcode", qr.get("id")),
            "id_etudiant": id_et,
        }
        # Premier scan
        res1 = client.post(
            "/api/v1/presences/scan",
            json=payload, headers=headers
        )
        assert res1.status_code in [200, 201]
        total1 = res1.json()["total_presences"]

        # Deuxième scan même jour
        res2 = client.post(
            "/api/v1/presences/scan",
            json=payload, headers=headers
        )
        assert res2.status_code in [200, 201]
        total2 = res2.json()["total_presences"]

        assert total2 == total1, \
            f"Anti-doublon echoue : {total1} → {total2}"
        print(f"\n[OK] Anti-doublon OK — total reste {total2}")


class TestQRCodeConditionnalite:

    def test_bilan_qrcodes_en_base(self, client, headers):
        """Affiche le bilan des QR actifs/inactifs."""
        etudiants = client.get(
            "/api/v1/etudiants", headers=headers).json()
        actifs = inactifs = sans_qr = 0
        for e in etudiants:
            res = get_qr_etudiant(client, headers, e["id_etudiant"])
            if res.status_code == 200:
                statut = res.json().get(
                    "statut", res.json().get("statut_qr", ""))
                if statut == "ACTIF":
                    actifs += 1
                else:
                    inactifs += 1
            else:
                sans_qr += 1
        print(f"\n[OK] Bilan QR codes :")
        print(f"   ACTIF    : {actifs}")
        print(f"   INACTIF  : {inactifs}")
        print(f"   Sans QR  : {sans_qr}")
        assert actifs + inactifs + sans_qr == len(etudiants)

    def test_qr_inexistant_retourne_404(self, client, headers):
        """QR fake → 404."""
        res = client.get(
            "/api/v1/presences/info-qr/QR-FAKE-00000",
            headers=headers
        )
        assert res.status_code == 404
        print(f"\n[OK] QR fake → 404")

    def test_qr_data_contient_infos_flutter(self, client, headers):
        """info-qr retourne tous les champs nécessaires pour Flutter."""
        etudiants = client.get(
            "/api/v1/etudiants", headers=headers).json()
        for e in etudiants:
            id_et  = e["id_etudiant"]
            res_qr = get_qr_etudiant(client, headers, id_et)
            if res_qr.status_code != 200:
                continue
            qr    = res_qr.json()
            statut = qr.get("statut", qr.get("statut_qr", ""))
            if statut != "ACTIF":
                continue
            id_qr = qr.get("id_qrcode", qr.get("id"))
            res = client.get(
                f"/api/v1/presences/info-qr/{id_qr}",
                headers=headers
            )
            assert res.status_code == 200
            data     = res.json()
            etudiant = data["etudiant"]
            assert "id_qrcode"  in data
            assert "statut_qr"  in data
            assert "etudiant"   in data
            assert "nom"        in etudiant
            assert "prenom"     in etudiant
            assert "matricule"  in etudiant
            assert "specialite" in etudiant
            assert "niveau"     in etudiant
            print(f"\n[OK] Donnees Flutter completes :")
            print(f"   Etudiant : {etudiant.get('nom_complet', etudiant['nom'])}")
            print(f"   Statut   : {data['statut_qr']}")
            print(f"   Photo    : {'Oui' if etudiant.get('photo') else 'Non'}")
            return
        print(f"\n[WARN] Aucun QR actif pour tester les donnees Flutter")