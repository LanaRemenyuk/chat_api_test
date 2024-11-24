from asyncio import run
from logging import Logger, getLogger
from os.path import dirname
from sys import path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.engine import Connection, engine_from_config
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel

from alembic import context
from alembic.config import Config

if __package__:
    from apps.core.config import settings
    from apps.db import metadata
    from apps.users.models import *
    from apps.auth.models import *
    from apps.chats.models import *
else:
    path.append(dirname(__file__) + "/..")

    from apps.core.config import settings
    from apps.db import metadata
    from apps.users.models import *
    from apps.auth.models import *
    from apps.chats.models import *

load_dotenv()

logger: Logger = getLogger("alembic.env")
config: Config = context.config

config.set_main_option(
    name="sqlalchemy.url",
    value="postgresql+asyncpg://{}:{}@{}:{}/{}".format(
        settings.postgres_settings.username,
        settings.postgres_settings.password,
        settings.postgres_settings.host,
        settings.postgres_settings.port,
        settings.postgres_settings.db_name,
    ),
)

context_configuration: dict[str, Any] = {
    "target_metadata": SQLModel.metadata,
    "include_schemas": True,
    "version_table_schema": metadata.schema,
}


def include_object(
    object: Any,
    name: str,
    type_: str,
    reflected: Any,
    compare_to: Any,
) -> bool:
    return False if type_ == "table" and object.schema != metadata.schema else True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option(
            name="sqlalchemy.url",
        ),
        include_object=include_object,
        **context_configuration,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(
    connection: Connection,
) -> None:
    context.configure(
        connection=connection,
        include_object=include_object,
        **context_configuration,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine: AsyncEngine = AsyncEngine(
        sync_engine=engine_from_config(  # type: ignore
            config.get_section(
                config.config_ini_section,
            ),
        ),
    )

    async with engine.connect() as connection:
        await connection.run_sync(
            fn=do_run_migrations,
        )

    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run(run_migrations_online())