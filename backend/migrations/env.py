"""Alembic migration environment."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.database import Base
from app.features.analysis.persistence import models as analysis_models  # noqa: F401
from app.features.candidate.persistence import models as candidate_models  # noqa: F401
from app.features.market.persistence import models as market_models  # noqa: F401
from app.features.market.persistence import top_down_models as market_top_down_models  # noqa: F401
from app.features.market_data.persistence import instruments as market_data_instrument_models  # noqa: F401
from app.features.market_data.persistence import models as market_data_models  # noqa: F401
from app.features.product.persistence import models as product_models  # noqa: F401
from app.features.product_selection.persistence import models as product_selection_models  # noqa: F401
from app.features.trade_plan.persistence import models as trade_plan_models  # noqa: F401
from app.features.user_preferences.persistence import models as user_preference_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""

    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure and execute migrations on an existing connection."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations using the asynchronous PostgreSQL engine."""

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
