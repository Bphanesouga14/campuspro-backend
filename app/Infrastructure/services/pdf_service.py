"""
Service de génération de reçus PDF après paiement.
Utilise ReportLab pour créer des PDFs professionnels.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# Couleurs CampusPro
BLEU       = HexColor("#1a3a5c")
VERT       = HexColor("#2e7d4f")
GRIS_CLAIR = HexColor("#f0f4f8")
GRIS_TEXTE = HexColor("#64748b")


def generer_recu_pdf(
    etudiant_nom:    str,
    etudiant_mat:    str,
    specialite:      str,
    niveau:          int,
    numero_tranche:  int,
    montant_attendu: int,
    montant_paye:    int,
    date_paiement:   str,
    id_paiement:     str,
    nom_ecole:       str = "CampusPro",
    annee:           str = "2024-2025",
) -> bytes:
    """
    Génère un reçu PDF et retourne les bytes.
    
    Usage :
        pdf_bytes = generer_recu_pdf(...)
        # Envoyer par email ou retourner en réponse HTTP
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize    = A4,
        rightMargin = 2*cm,
        leftMargin  = 2*cm,
        topMargin   = 2*cm,
        bottomMargin= 2*cm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # ── En-tête ───────────────────────────────────────────────
    header_data = [[
        Paragraph(f"""
            <font color='white' size='18'><b>🎓 {nom_ecole}</b></font><br/>
            <font color='#90cdf4' size='9'>Gestion des étudiants, paiements & QR codes</font>
        """, ParagraphStyle("h", fontName="Helvetica-Bold", alignment=TA_LEFT)),
        Paragraph(f"""
            <font color='white' size='10'><b>REÇU DE PAIEMENT</b></font><br/>
            <font color='#90cdf4' size='8'>N° {id_paiement}</font><br/>
            <font color='#90cdf4' size='8'>Date : {date_paiement}</font>
        """, ParagraphStyle("h2", fontName="Helvetica", alignment=TA_RIGHT)),
    ]]
    header_table = Table(header_data, colWidths=[10*cm, 7*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), BLEU),
        ("PADDING",     (0,0), (-1,-1), 16),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [BLEU]),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), [8]),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── Statut paiement ───────────────────────────────────────
    reste = montant_attendu - montant_paye
    if reste == 0:
        statut_txt   = "✅ TRANCHE SOLDÉE"
        statut_color = VERT
    else:
        statut_txt   = f"⚠ PAIEMENT PARTIEL — Reste : {reste:,} FCFA"
        statut_color = HexColor("#d97706")

    statut_style = ParagraphStyle(
        "statut", fontName="Helvetica-Bold",
        fontSize=11, alignment=TA_CENTER,
        textColor=white, backColor=statut_color,
        spaceBefore=4, spaceAfter=4,
        borderPadding=(8, 12, 8, 12),
    )
    elements.append(Paragraph(statut_txt, statut_style))
    elements.append(Spacer(1, 0.4*cm))

    # ── Informations étudiant ─────────────────────────────────
    titre_style = ParagraphStyle(
        "titre", fontName="Helvetica-Bold",
        fontSize=10, textColor=BLEU,
        spaceAfter=6,
    )
    elements.append(Paragraph("INFORMATIONS ÉTUDIANT", titre_style))

    info_data = [
        ["Nom & Prénom",     etudiant_nom,   "Matricule",       etudiant_mat],
        ["Spécialité",       specialite,     "Niveau",          f"Niveau {niveau}"],
        ["Année académique", annee,          "Tranche",         f"Tranche {numero_tranche}"],
    ]
    info_table = Table(info_data, colWidths=[4*cm, 6*cm, 3.5*cm, 4*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), GRIS_CLAIR),
        ("BACKGROUND",    (2,0), (2,-1), GRIS_CLAIR),
        ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("TEXTCOLOR",     (0,0), (0,-1), GRIS_TEXTE),
        ("TEXTCOLOR",     (2,0), (2,-1), GRIS_TEXTE),
        ("PADDING",       (0,0), (-1,-1), 8),
        ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [white, GRIS_CLAIR]),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*cm))

    # ── Détail du paiement ────────────────────────────────────
    elements.append(Paragraph("DÉTAIL DU PAIEMENT", titre_style))

    montant_style_v = ParagraphStyle(
        "mv", fontName="Helvetica-Bold",
        fontSize=11, textColor=BLEU,
    )
    pay_data = [
        ["Montant de la tranche",  f"{montant_attendu:,} FCFA"],
        ["Montant versé",          f"{montant_paye:,} FCFA"],
        ["Reste à payer",          f"{reste:,} FCFA"],
        ["Date de paiement",       date_paiement],
        ["Référence paiement",     id_paiement],
    ]
    pay_table = Table(pay_data, colWidths=[8*cm, 9.5*cm])
    pay_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), GRIS_CLAIR),
        ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("TEXTCOLOR",     (0,0), (0,-1), GRIS_TEXTE),
        ("TEXTCOLOR",     (1,1), (1,1), VERT),      # montant versé en vert
        ("TEXTCOLOR",     (1,2), (1,2), HexColor("#dc2626") if reste > 0 else VERT),
        ("FONTNAME",      (1,0), (1,-1), "Helvetica-Bold"),
        ("PADDING",       (0,0), (-1,-1), 10),
        ("GRID",          (0,0), (-1,-1), 0.5, HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [white, GRIS_CLAIR]),
        ("FONTSIZE",      (1,0), (1,0), 13),        # montant attendu plus grand
        ("TEXTCOLOR",     (1,0), (1,0), BLEU),
    ]))
    elements.append(pay_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── Pied de page ─────────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
    elements.append(Spacer(1, 0.3*cm))

    footer_style = ParagraphStyle(
        "footer", fontName="Helvetica",
        fontSize=8, textColor=GRIS_TEXTE, alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        f"Ce reçu a été généré automatiquement par CampusPro le "
        f"{datetime.now().strftime('%d/%m/%Y à %H:%M')}.<br/>"
        f"Il constitue une preuve de paiement valide. "
        f"Conservez-le précieusement.",
        footer_style
    ))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        f"© {datetime.now().year} CampusPro — Tous droits réservés",
        footer_style
    ))

    doc.build(elements)
    return buffer.getvalue()