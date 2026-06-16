#Génération image QR code et Envoi Email/SMS


#
#  RÔLE : Implémenter les services externes :
#         - Génération d'image QR code (bibliothèque qrcode)
#         - Envoi d'emails (SMTP)
#         - Envoi de SMS (simulé — à brancher sur une API réelle)
#
#  Ces services implémentent les interfaces du Domaine :
#  IQRCodeService et INotificationService.
#
#  COUCHE : Infrastructure
# ============================================================

import json          # Pour convertir un dictionnaire en texte JSON
import base64        # Pour encoder l'image QR en texte (base64)
import smtplib       # Bibliothèque Python standard pour envoyer des emails
import io            # Pour créer un "fichier en mémoire" (sans écrire sur disque)
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Bibliothèque externe pour générer les images QR code
# Installation : pip install qrcode[pil]
try:
    import qrcode
    from qrcode.image.pure import PyPNGImage
    QR_DISPONIBLE = True
except ImportError:
    QR_DISPONIBLE = False

from app.Domain.interfaces import IQRCodeService, INotificationService
from app.core.config import settings


# ============================================================
#  SERVICE : QRCodeServiceImpl
# ============================================================
class QRCodeServiceImpl(IQRCodeService):
    """
    Implémentation concrète de IQRCodeService.
    Génère une vraie image QR code à partir de données.

    Le QR code encode les informations de l'étudiant
    au format JSON → quand le vigile scanne le QR,
    l'application lit ces informations instantanément.
    """

    async def generer(
        self,
        donnees: dict,
        id_etudiant: str,
    ) -> str:
        """
        Génère un QR code et retourne son contenu en base64.

        Pourquoi base64 ?
        Une image est des bytes binaires (0 et 1).
        On ne peut pas stocker des bytes bruts dans une colonne
        texte de PostgreSQL. Base64 convertit ces bytes en texte.

        Le front-end pourra afficher l'image avec :
        <img src="data:image/png;base64,{qr_data}" />
        """

        # Vérifier que la bibliothèque qrcode est installée
        if not QR_DISPONIBLE:
            # Si pas disponible → retourner un placeholder en JSON
            # Le système continue de fonctionner sans l'image
            return json.dumps({
                "erreur": "Bibliothèque qrcode non installée",
                "donnees": donnees,
            })

        # ── Étape 1 : Convertir les données en texte JSON ───
        # json.dumps() convertit un dict Python en string JSON
        # ensure_ascii=False → garde les accents (é, à, ç...)
        # indent=2 → formatte joliment le JSON
        contenu_qr = json.dumps(donnees, ensure_ascii=False, indent=2)

        # ── Étape 2 : Créer le QR code ──────────────────────
        qr = qrcode.QRCode(
            # version=1 → taille du QR (1 = le plus petit, 40 = le plus grand)
            # error_correction=H → peut être lu même si 30% est abîmé
            version             = 1,
            error_correction    = qrcode.constants.ERROR_CORRECT_H,
            # box_size = taille de chaque carré du QR en pixels
            box_size            = 10,
            # border = largeur de la bordure blanche autour du QR
            border              = 4,
        )

        # Ajouter le contenu JSON dans le QR
        qr.add_data(contenu_qr)
        qr.make(fit=True)  # fit=True → ajuste la version automatiquement

        # ── Étape 3 : Générer l'image PNG en mémoire ────────
        # io.BytesIO() = un "fichier" en RAM, pas sur le disque
        # On évite ainsi d'écrire des fichiers temporaires
        image = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        image.save(buffer)       # Sauvegarder l'image dans le buffer
        buffer.seek(0)           # Revenir au début du buffer pour lire

        # ── Étape 4 : Encoder en base64 ─────────────────────
        # base64.b64encode() convertit les bytes en texte base64
        # .decode("utf-8") convertit les bytes base64 en string Python
        image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return image_base64


# ============================================================
#  SERVICE : NotificationServiceImpl
# ============================================================
class NotificationServiceImpl(INotificationService):
    """
    Implémentation concrète de INotificationService.
    Envoie de vrais emails via SMTP et des SMS via API.
    """

    async def envoyer_email(
        self,
        destinataire: str,
        sujet: str,
        message: str,
    ) -> bool:
        """
        Envoie un email via SMTP.

        SMTP = Simple Mail Transfer Protocol.
        C'est le protocole standard pour envoyer des emails.
        Gmail, Outlook, et tous les serveurs mail l'utilisent.

        Retourne True si envoyé, False si erreur.
        """
        # Vérifier que la configuration SMTP est disponible
        if not all([
            settings.SMTP_HOST,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
        ]):
            # Pas de configuration → on simule l'envoi (mode développement)
            print(
                f"\n[EMAIL SIMULÉ]\n"
                f"À       : {destinataire}\n"
                f"Sujet   : {sujet}\n"
                f"Message : {message}\n"
                f"{'─' * 50}"
            )
            return True  # On considère l'envoi comme réussi en dev

        try:
            # ── Construire le message email ──────────────────
            # MIMEMultipart = email avec plusieurs parties (texte + HTML possible)
            email = MIMEMultipart("alternative")
            email["Subject"] = sujet
            email["From"]    = settings.SMTP_USER
            email["To"]      = destinataire

            # Partie texte brut (pour les clients mail qui ne supportent pas HTML)
            partie_texte = MIMEText(message, "plain", "utf-8")
            email.attach(partie_texte)

            # ── Envoyer via SMTP ─────────────────────────────
            # smtplib.SMTP_SSL = connexion sécurisée (port 465)
            # smtplib.SMTP avec starttls = port 587
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as serveur:
                # starttls() = démarre le chiffrement de la connexion
                serveur.starttls()
                # login() = authentification
                serveur.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                # sendmail() = envoie l'email
                serveur.sendmail(
                    settings.SMTP_USER,
                    destinataire,
                    email.as_string()
                )

            return True  # Succès

        except smtplib.SMTPException as e:
            # En cas d'erreur SMTP → on affiche l'erreur mais on ne plante pas
            print(f"[ERREUR EMAIL] {e}")
            return False

    async def envoyer_sms(
        self,
        numero: str,
        message: str,
    ) -> bool:
        """
        Envoie un SMS via une API externe.

        En production, vous brancheriez ici une vraie API SMS
        comme Twilio, Africa's Talking (populaire en Afrique),
        ou Orange API Cameroun.

        Pour l'instant, on simule l'envoi en mode développement.
        """

        # ── Mode simulation (développement) ─────────────────
        if not hasattr(settings, 'SMS_API_KEY') or not settings.SMS_API_KEY:
            print(
                f"\n[SMS SIMULÉ]\n"
                f"Numéro  : {numero}\n"
                f"Message : {message}\n"
                f"{'─' * 50}"
            )
            return True

        # ── Exemple avec Africa's Talking API ───────────────
        # (à adapter selon votre opérateur SMS)
        try:
            import urllib.request
            import urllib.parse

            # Préparer les données de la requête HTTP
            parametres = urllib.parse.urlencode({
                "username": settings.SMS_USERNAME,
                "to":       numero,
                "message":  message,
                "from":     "SIGC",  # Identifiant expéditeur
            }).encode("utf-8")

            # Envoyer la requête HTTP POST à l'API SMS
            requete = urllib.request.Request(
                url     = "https://api.africastalking.com/version1/messaging",
                data    = parametres,
                headers = {
                    "apiKey":       settings.SMS_API_KEY,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept":       "application/json",
                },
            )
            with urllib.request.urlopen(requete) as reponse:
                return reponse.status == 200

        except Exception as e:
            print(f"[ERREUR SMS] {e}")
            return False
