# NOTE : Pour la gestion évolutive du schéma de base, il est recommandé d'utiliser Alembic pour les migrations.
import asyncio
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.db import engine, Base

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Base de données initialisée avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la base de données : {e}")

if __name__ == "__main__":
    asyncio.run(init_db())
