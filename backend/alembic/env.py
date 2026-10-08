"""Alembic environment configuration for Gemini Notebook.

Reads the database URL from app.config.settings or DATABASE_URL env var,
handles hostname remapping for local host execution, and registers SQLAlchemy models.
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure backend root is on sys.path so app modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.db.database import Base
# Import models so Base.metadata contains all tables
import app.db.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    db_url = os.getenv("DATABASE_URL") or settings.database_url
    if not db_url:
        db_url = config.get_main_option("sqlalchemy.url", "")
    
    # If running outside container (host), remap postgres:5432 to 127.0.0.1:5434
    if "@postgres:5432" in db_url:
        try:
            import socket
            socket.gethostbyname("postgres")
        except socket.gaierror:
            db_url = db_url.replace("@postgres:5432", "@127.0.0.1:5434")

    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
