from typing import Any

from pydantic.class_validators import validator
from pydantic.networks import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from apps.users import __version__ as version


class Base(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")


class PostgresSettings(Base):
    protocol: str = "postgresql+asyncpg"
    host: str = "0.0.0.0"
    port: str = "5432"
    db_name: str = "greenatom_chat"
    schema_name: str = "public"
    username: str | None = None
    password: str | None = None
    extensions: list[str] | None = []
    dsn: str | None = ""

    @validator("dsn", pre=True)
    def build_dsn(
        cls,
        value: PostgresDsn | None,
        values: dict[str, Any],
    ) -> PostgresDsn:
        if value is not None and value != "":
            return value

        postgres_dsn: PostgresDsn = PostgresDsn(
            url="{}://{}:{}@{}:{}/{}".format(
                values["protocol"],
                values["username"],
                values["password"],
                values["host"],
                values["port"],
                values["db_name"],
            ),
        )

        return str(postgres_dsn)

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")


class MQSettings(Base):
    broker_url: str | None = None
    queue_name: str = "chat_queue"

    model_config = SettingsConfigDict(env_prefix="MQ_")


class AppSettings(Base):
    is_debug: bool | None = None
    log_level: str | None = None
    service_name: str | None = None
    docs_version: str = version
    docs_name: str = "users"
    api_key: str | None = None
    jwt_secret_key: str | None = None

    model_config = SettingsConfigDict(env_prefix="APP_")


class UsersSettings(AppSettings):
    service_name: str = "users"
    shema_name: str = "public"


class AuthSettings(AppSettings):
    service_name: str = "auth_service"
    schema_name: str = "public"


class ChatsSettings(AppSettings):
    service_name: str = "chats"


class Settings(Base):
    postgres_settings: PostgresSettings = PostgresSettings()
    mq_settings: MQSettings = MQSettings()
    users_settings: UsersSettings = UsersSettings()
    auth_settings: AuthSettings = AuthSettings()
    chats_settings: ChatsSettings = ChatsSettings()


settings = Settings()
