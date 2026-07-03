"""
Script de migration — à exécuter après chaque mise à jour du backend.
Lance : python migrer.py
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

import app.Infrastructure.database.session as db
from sqlalchemy import text

MIGRATIONS = [
    "ALTER TABLE utilisateurs ADD COLUMN IF NOT EXISTS photo TEXT",
    "ALTER TABLE etudiants ADD COLUMN IF NOT EXISTS photo TEXT",
    """
    CREATE TABLE IF NOT EXISTS presences (
        id SERIAL PRIMARY KEY,
        id_etudiant VARCHAR(20) REFERENCES etudiants(id_etudiant),
        id_qrcode VARCHAR(20) REFERENCES qr_codes(id_qrcode),
        date_scan TIMESTAMP DEFAULT NOW(),
        cours VARCHAR(100),
        scanner_par VARCHAR(20),
        valide BOOLEAN DEFAULT TRUE
    )
    """,
]

async def run():
    await db.initialiser_base_de_donnees()
    async with db.AsyncSessionLocal() as session:
        for sql in MIGRATIONS:
            try:
                await session.execute(text(sql.strip()))
                print(f"✅ {sql.strip()[:60]}...")
            except Exception as e:
                print(f"⚠️  {e}")
        await session.commit()
        print("\n✅ Migrations terminées.")
    await db.engine.dispose()

asyncio.run(run())