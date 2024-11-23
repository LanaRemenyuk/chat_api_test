from json import dumps
from typing import Any, AsyncGenerator

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import MetaData, text

from apps.core.config import settings


def to_json(
    value: dict[Any, Any] | BaseModel | list[BaseModel],
) -> str:
    obj: dict[Any, Any] | list[dict[Any, Any]]

    if isinstance(value, BaseModel):
        obj = value.dict()
    elif isinstance(value, list):
        obj = []

        for item in value:
            obj.append(
                item.dict() if isinstance(item, BaseModel) else item,
            )
    else:
        obj = value

    return dumps(
        obj=obj,
        ensure_ascii=False,
    )


engine: AsyncEngine = create_async_engine(
    url=settings.postgres_settings.dsn,
    #echo=settings.app_settings.is_debug,
    future=True,
    pool_pre_ping=True,
    json_serializer=to_json,
)

metadata: MetaData = MetaData(
    schema=settings.postgres_settings.schema_name,
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    },
)

async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def create_schema(
    session: AsyncSession,
) -> None:
    await session.execute(
        statement=text(
            text=f'CREATE SCHEMA IF NOT EXISTS "{settings.postgres_settings.schema_name}"',
        ),
    )


async def add_extensions(
    session: AsyncSession,
) -> None:
    extensions: list[str] = getattr(settings.postgres_settings, "extensions", [])

    for extension in extensions:
        await session.execute(
            statement=text(
                text=f'CREATE EXTENSION IF NOT EXISTS "{extension}"',
            ),
        )


async def init_config(
    session: AsyncSession,
) -> None:
    pass


async def init_db() -> None:
    async with async_session() as session:
        await create_schema(
            session=session,
        )

        await add_extensions(
            session=session,
        )

        await session.close()

    async with engine.begin() as conn:
        await conn.run_sync(
            fn=metadata.create_all,
        )

    async with async_session() as session:
        await init_config(
            session=session,
        )

        await session.close()


async def close_connection() -> None:
    await engine.dispose()
