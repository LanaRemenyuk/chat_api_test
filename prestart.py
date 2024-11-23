from asyncpg import Connection, connect
from asyncpg.exceptions import InvalidCatalogNameError
from app.core.config import settings
from app.core.logger import get_logging_config
from time import sleep
from logging import config as logging_config, error, info
from sys import exit
from asyncio import run

log_config: dict[str, Any] = get_logging_config(
    log_level=settings.app_settings.log_level,
)

logging_config.dictConfig(config=log_config)

async def get_connection(db_name: str | None = None) -> Connection:
    dsn: str = "postgresql://{}:{}@{}:{}".format(
        settings.postgres_settings.username,
        settings.postgres_settings.password,
        settings.postgres_settings.host,
        settings.postgres_settings.port,
    )

    if db_name:
        dsn += f"/{db_name}"

    connection = await connect(dsn=dsn)
    return connection

async def create_database(connection: Connection, db_name: str) -> None:
    if not await connection.fetchrow(
        query=f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';"
    ):
        info("Creating database...")
        await connection.execute(f"CREATE DATABASE {db_name};")

async def create_schema(connection: Connection, schema_name: str) -> None:
    if not await connection.fetchrow(
        query=f"SELECT 1 FROM information_schema.schemata WHERE schema_name = '{schema_name}';"
    ):
        info("Creating schema...")
        await connection.execute(f"CREATE SCHEMA {schema_name};")

async def main() -> None:
    retries = 100
    delay = 10

    while True:
        db_name = settings.postgres_settings.db_name
        schema_name = settings.postgres_settings.schema_name

        connection = None

        try:
            connection = await get_connection(db_name=db_name)
            await create_schema(connection=connection, schema_name=schema_name)
        except OSError:
            retries -= 1
            if retries == 0:
                error("PostgreSQL connection error")
                exit(1)
            info(f"Waiting for PostgreSQL, {retries} remaining attempt...")
            sleep(delay)
        except InvalidCatalogNameError:
            connection = await get_connection()
            await create_database(connection=connection, db_name=db_name)
            await connection.close()
        else:
            await connection.close()
            exit(0)

if __name__ == "__main__":
    run(main)
