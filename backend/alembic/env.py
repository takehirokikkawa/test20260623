import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to values within the .ini file.
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging unless the caller already
# set up logging (e.g. when called programmatically).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# We use hand-written raw-SQL migrations, so target_metadata is None.
target_metadata = None

# ---------------------------------------------------------------------------
# Override sqlalchemy.url from environment variable.
# ---------------------------------------------------------------------------
def get_url() -> str:
    url = os.environ.get("ALEMBIC_DATABASE_URL")
    if not url:
        # Fallback: derive from DATABASE_URL by swapping the async driver.
        url = os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg2://techinsight:techinsight@localhost:5432/techinsight",
        )
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine; calls to
    context.execute() emit the given string to the script output.
    """
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
    """Run migrations in 'online' mode (default).

    Creates an Engine and associates a connection with the context.
    """
    # Override the URL from the ini file.
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
