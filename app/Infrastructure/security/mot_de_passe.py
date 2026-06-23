#Hashage et vérification des mots de passe (bcrypt)

# ============================================================
#  FICHIER : app/Infrastructure/security/mot_de_passe.py
#
#  RÔLE : Hasher et vérifier les mots de passe avec bcrypt.
#
#  POURQUOI HASHER ?
#  On ne stocke JAMAIS un mot de passe en clair en base.
#  bcrypt transforme "MonMotDePasse123" en une chaîne illisible
#  et irréversible (impossible de "dé-hasher").
#  Pour vérifier un mot de passe, on hash ce qui est tapé et on
#  compare les deux hash — jamais les mots de passe en clair.
#
#  bcrypt intègre aussi un "sel" (salt) aléatoire par mot de passe,
#  donc deux utilisateurs avec le même mot de passe auront des
#  hash complètement différents.
#
#  COUCHE : Infrastructure
# ============================================================

import bcrypt


def hasher_mot_de_passe(mot_de_passe: str) -> str:
    """
    Hash un mot de passe en clair. Retourne le hash sous forme de string
    (stockable directement dans une colonne texte de PostgreSQL).
    """
    sel = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(mot_de_passe.encode("utf-8"), sel)
    return hash_bytes.decode("utf-8")


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    """
    Vérifie qu'un mot de passe en clair correspond au hash stocké en base.
    Retourne False (au lieu de lever une exception) si le hash est
    invalide/corrompu, par sécurité.
    """
    try:
        return bcrypt.checkpw(
            mot_de_passe.encode("utf-8"),
            hash_stocke.encode("utf-8"),
        )
    except (ValueError, AttributeError):
        return False
