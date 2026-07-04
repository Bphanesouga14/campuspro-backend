"""Carte étudiant PDF — canvas bas niveau pour support photo."""
import io, base64, json, tempfile, os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader

BLEU   = HexColor("#1a3a5c")
BLEU_C = HexColor("#4f7cf7")
BLANC  = white
GRIS   = HexColor("#64748b")
GRIS_C = HexColor("#f0f4f8")

CARD_W = 8.56 * cm
CARD_H = 5.4  * cm


def _photo_reader(photo_data):
    """Convertit un data URL base64 en ImageReader ReportLab."""
    try:
        from PIL import Image as PILImage
        b64 = photo_data.split(",", 1)[1] if "," in photo_data else photo_data
        img_bytes = base64.b64decode(b64)
        pil = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        pil = pil.resize((200, 260), PILImage.LANCZOS)
        buf = io.BytesIO()
        pil.save(buf, "PNG")
        buf.seek(0)
        return ImageReader(buf)
    except Exception as ex:
        print(f"[CARTE] Photo erreur : {ex}")
        return None


def _dessiner_recto(c, ox, oy, nom, prenom, matricule,
                    specialite, niveau, annee, photo_reader=None):
    """Dessine le recto de la carte à la position (ox, oy)."""

    # Fond bleu
    c.setFillColor(BLEU)
    c.rect(ox, oy, CARD_W, CARD_H, fill=1, stroke=0)

    # Bande top bleue claire
    c.setFillColor(BLEU_C)
    c.rect(ox, oy + CARD_H - 1.1*cm, CARD_W, 1.1*cm, fill=1, stroke=0)

    # Texte bande top
    c.setFillColor(BLANC)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(ox + CARD_W/2, oy + CARD_H - 0.75*cm, "CAMPUS PRO")
    c.setFont("Helvetica", 6.5)
    c.setFillColor(HexColor("#90cdf4"))
    c.drawRightString(ox + CARD_W - 0.3*cm, oy + CARD_H - 0.75*cm, "CARTE ÉTUDIANT")

    # Zone photo
    px = ox + 0.35*cm
    py = oy + 1.1*cm
    pw = 1.8*cm
    ph = 2.4*cm

    if photo_reader:
        try:
            c.drawImage(photo_reader, px, py, pw, ph,
                        preserveAspectRatio=True, mask="auto")
            # Bordure photo
            c.setStrokeColor(BLEU_C)
            c.setLineWidth(0.8)
            c.rect(px, py, pw, ph, fill=0, stroke=1)
        except Exception:
            photo_reader = None

    if not photo_reader:
        c.setFillColor(HexColor("#2d5a8e"))
        c.rect(px, py, pw, ph, fill=1, stroke=0)
        c.setFillColor(BLANC)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(px + pw/2, py + ph/2, "PHOTO")

    # Infos texte
    tx = ox + 2.55*cm
    c.setFillColor(BLANC)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(tx, oy + CARD_H - 1.65*cm, f"{prenom.upper()} {nom.upper()}")

    # Ligne séparatrice
    c.setStrokeColor(BLEU_C)
    c.setLineWidth(0.5)
    c.line(tx, oy + CARD_H - 1.78*cm, ox + CARD_W - 0.3*cm, oy + CARD_H - 1.78*cm)

    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#90cdf4"))
    infos = [
        f"Mat : {matricule}",
        f"Filière : {specialite}",
        f"Niveau  : {niveau}",
        f"Année   : {annee}",
    ]
    y = oy + CARD_H - 2.2*cm
    for info in infos:
        c.drawString(tx, y, info)
        y -= 0.48*cm

    # Pied
    c.setFillColor(BLEU_C)
    c.rect(ox, oy, CARD_W, 0.75*cm, fill=1, stroke=0)
    c.setFillColor(BLANC)
    c.setFont("Helvetica", 6)
    c.drawCentredString(ox + CARD_W/2, oy + 0.22*cm,
        f"Valide pour l'année académique {annee}")


def _dessiner_verso(c, ox, oy, id_etudiant, nom, prenom,
                    matricule, specialite, niveau, annee):
    """Dessine le verso de la carte à la position (ox, oy)."""

    # Fond blanc + bordure
    c.setFillColor(BLANC)
    c.setStrokeColor(BLEU)
    c.setLineWidth(1.5)
    c.rect(ox, oy, CARD_W, CARD_H, fill=1, stroke=1)

    # Bande top
    c.setFillColor(BLEU)
    c.rect(ox, oy + CARD_H - 1*cm, CARD_W, 1*cm, fill=1, stroke=0)
    c.setFillColor(BLANC)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(ox + CARD_W/2, oy + CARD_H - 0.65*cm,
        "CARTE ÉTUDIANT — VÉRIFICATION")

    # QR code
    try:
        from reportlab.graphics.barcode.qr import QrCodeWidget
        from reportlab.graphics import renderPDF
        from reportlab.graphics.shapes import Drawing as RLDrawing

        qr_data = json.dumps({
            "id":  id_etudiant,
            "mat": matricule,
            "nom": f"{prenom} {nom}",
            "sp":  specialite,
            "niv": niveau,
        }, ensure_ascii=False)

        qr_widget = QrCodeWidget(qr_data)
        bounds    = qr_widget.getBounds()
        bw = bounds[2] - bounds[0]
        bh = bounds[3] - bounds[1]

        qr_size = 2.3*cm
        qr_x    = ox + (CARD_W - qr_size) / 2
        qr_y    = oy + CARD_H - 1.1*cm - qr_size - 0.2*cm

        d = RLDrawing(qr_size, qr_size)
        d.transform = (qr_size/bw, 0, 0, qr_size/bh, 0, 0)
        d.add(qr_widget)
        renderPDF.draw(d, c, qr_x, qr_y)

        c.setFillColor(GRIS)
        c.setFont("Helvetica", 6)
        c.drawCentredString(ox + CARD_W/2, qr_y - 0.35*cm,
            "Scanner pour vérifier l'identité")

    except Exception as ex:
        print(f"[CARTE] QR erreur : {ex}")

    # Pied verso
    c.setFillColor(GRIS_C)
    c.rect(ox, oy, CARD_W, 0.85*cm, fill=1, stroke=0)
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(ox + CARD_W/2, oy + 0.52*cm,
        "En cas de perte : contacter l'administration")
    c.drawCentredString(ox + CARD_W/2, oy + 0.22*cm,
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")


def generer_carte_etudiant_pdf(
    id_etudiant, nom, prenom, matricule,
    specialite, niveau, annee,
    photo_data=None, nom_ecole="CampusPro",
) -> bytes:
    """Génère la carte étudiant PDF recto/verso."""

    buf = io.BytesIO()
    PAGE_W, PAGE_H = A4

    c = canvas.Canvas(buf, pagesize=A4)

    # Titre en haut de page
    c.setFillColor(BLEU)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(PAGE_W/2, PAGE_H - 1.5*cm, "CARTE ÉTUDIANT")
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_W/2, PAGE_H - 2*cm,
        f"{nom_ecole} — Année académique {annee}")

    # Ligne séparatrice
    c.setStrokeColor(GRIS_C)
    c.setLineWidth(1)
    c.line(1.5*cm, PAGE_H - 2.3*cm, PAGE_W - 1.5*cm, PAGE_H - 2.3*cm)

    # Préparer la photo
    photo_reader = _photo_reader(photo_data) if photo_data else None

    # Positions : recto à gauche, verso à droite
    margin   = 1.5*cm
    gap      = 0.8*cm
    start_y  = PAGE_H - 2.8*cm - CARD_H

    recto_x  = margin
    verso_x  = margin + CARD_W + gap

    # Dessiner les deux faces
    _dessiner_recto(c, recto_x, start_y, nom, prenom, matricule,
                    specialite, niveau, annee, photo_reader)
    _dessiner_verso(c, verso_x, start_y, id_etudiant, nom, prenom,
                    matricule, specialite, niveau, annee)

    # Légendes sous les cartes
    c.setFillColor(GRIS)
    c.setFont("Helvetica", 8)
    c.drawCentredString(recto_x + CARD_W/2, start_y - 0.5*cm, "← RECTO")
    c.drawCentredString(verso_x + CARD_W/2, start_y - 0.5*cm, "VERSO →")

    c.setFont("Helvetica", 8)
    c.drawCentredString(PAGE_W/2, start_y - 1*cm,
        "Imprimez · Découpez · Plastifiez")

    c.save()
    return buf.getvalue()