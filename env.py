'''from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from logging.config import fileConfig
import asyncio

# Configuration Alembic
config = context.config
fileConfig(config.config_file_name)

# Importer tes modèles
from app.Infrastructure.database.session import Base

target_metadata = Base.metadata

def run_migrations_online():
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        future=True,
    )

    async def do_run_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda conn: context.run_migrations(connection=conn)
            )

    asyncio.run(do_run_migrations())'''
