"""Ambiente Alembic — migrations async contra o Postgres do prod2."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401  — importa todos os models p/ o autogenerate

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Não usamos config.set_main_option(): o ConfigParser interpreta '%' (presente em
# senhas URL-encoded, ex.: %40) como sintaxe de interpolação e quebra. Lemos a URL
# direto da settings.
DATABASE_URL = settings.database_url

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
