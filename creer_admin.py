#!/usr/bin/env python3
"""
============================================================
  SCRIPT : creer_admin.py
  USAGE  : python creer_admin.py
============================================================

Ce script crée le premier compte ADMIN dans la base de données.
À exécuter UNE SEULE FOIS après le déploiement, avant de démarrer
le serveur, pour avoir un compte avec lequel se connecter.

Après avoir créé ce compte, tous les autres comptes (secrétaire,
caissier) peuvent être créés via l'API :
  POST /api/v1/auth/utilisateurs
  Authorization: Bearer <token_admin>

PRÉREQUIS :
  - Fichier .env configuré (DATABASE_URL, JWT_SECRET_KEY)
  - Base de données accessible et tables créées
    (uvicorn main:app les crée automatiquement au démarrage)
"""

import asyncio
import getpass
import sys
import uuid

# ── Charger les variables d'environnement ──────────────────
from dotenv import load_dotenv
load_dotenv()

from app.core.config import settings
from app.Infrastructure.database import session as db_session
from app.Infrastructure.database.session import initialiser_base_de_donnees
from app.Infrastructure.repositories.utilisateur_repo import SQLAlchemyUtilisateurRepository
from app.Infrastructure.security.mot_de_passe import hasher_mot_de_passe
from app.Domain.entities import UtilisateurDomaine
from app.Domain.value_objects import RoleUtilisateur


async def main():
    print("=" * 60)
    print("  LGS — Création du compte administrateur")
    print("=" * 60)
    print()

    print("Entrez les informations du compte ADMIN :\n")
    email = input("Email        : ").strip().lower()
    nom   = input("Nom complet  : ").strip()

    while True:
        mdp   = getpass.getpass("Mot de passe (min. 8 car.) : ")
        mdp2  = getpass.getpass("Confirmez   : ")
        if mdp != mdp2:
            print("❌ Les mots de passe ne correspondent pas. Recommencez.\n")
            continue
        if len(mdp) < 8:
            print("❌ Mot de passe trop court (minimum 8 caractères).\n")
            continue
        break

    print("\n⏳ Connexion à la base de données...")

    # Initialise la connexion (Supabase ou local selon .env)
    # et crée les tables si elles n'existent pas encore.
    await initialiser_base_de_donnees()

    async with db_session.AsyncSessionLocal() as session:
        repo = SQLAlchemyUtilisateurRepository(session)

        # Vérifier si l'email existe déjà
        existant = await repo.trouver_par_email(email)
        if existant:
            print(f"\n⚠️  Un compte existe déjà avec l'email '{email}'.")
            print(f"   Rôle actuel : {existant.role.value}")
            confirm = input("   Voulez-vous quand même continuer et créer un autre compte ? (o/N) : ")
            if confirm.lower() != "o":
                print("Annulé.")
                return

        utilisateur = UtilisateurDomaine(
            id_utilisateur    = f"USR-{str(uuid.uuid4())[:8].upper()}",
            email             = email,
            nom               = nom,
            mot_de_passe_hash = hasher_mot_de_passe(mdp),
            role              = RoleUtilisateur.ADMIN,
            actif             = True,
        )

        sauvegarde = await repo.sauvegarder(utilisateur)
        await session.commit()

    print()
    print("✅ Compte ADMIN créé avec succès !")
    print(f"   ID    : {sauvegarde.id_utilisateur}")
    print(f"   Email : {sauvegarde.email}")
    print(f"   Rôle  : {sauvegarde.role.value}")
    print()
    print("Vous pouvez maintenant démarrer le serveur :")
    print("  uvicorn main:app --reload")
    print()
    print("Et vous connecter via :")
    print("  POST /api/v1/auth/login")
    print(f"  username={email}  password=<votre_mot_de_passe>")


if __name__ == "__main__":
    asyncio.run(main())
