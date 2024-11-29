from http import HTTPStatus
from logging import config as logging_config
from typing import Any

from fastapi import Depends, FastAPI, status
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uvicorn import run

from apps.auth.api.v1.api import auth_routers as v1_auth_routers
from apps.chats.api.v1.api import chats_routers as v1_chats_routers
from apps.core.config import settings
from apps.core.logger import get_logging_config
from apps.core.setup import setup_docs, setup_router
from apps.db import close_connection, get_session, init_db
from apps.mq.connection import RabbitMQConnectionManager
from apps.mq.consumer import start_consumer
from apps.users.api.v1.api import users_routers as v1_users_routers

IS_DEBUG: bool = settings.users_settings.is_debug or False
LOG_LEVEL: str = settings.users_settings.log_level or "INFO"

log_config: dict[str, Any] = get_logging_config(
    log_level=LOG_LEVEL,
)

logging_config.dictConfig(
    config=log_config,
)

async def unicorn_exception_handler(
    request: Request,
    exception: Exception,
) -> ORJSONResponse:
    status_code: int
    detail: str

    if isinstance(exception, HTTPException):
        status_code = exception.status_code
        detail = exception.detail
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = HTTPStatus(status_code).phrase

    return ORJSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "detail": detail,
        },
    )
rabbit_connection_manager = RabbitMQConnectionManager(settings.mq_settings.broker_url)

def get_application() -> FastAPI:
    project_name: str = settings.users_settings.docs_name.replace("-", " ").capitalize()

    app: FastAPI = FastAPI(
        title=project_name,
        default_response_class=ORJSONResponse,
        version=settings.users_settings.docs_version,
        docs_url=None,
        openapi_url=None,
        debug=IS_DEBUG,
    )

    app.add_exception_handler(
        exc_class_or_status_code=Exception,
        handler=unicorn_exception_handler,
    )

    @app.on_event("startup")
    async def startup_event():
        print("Запуск приложения...")
        await rabbit_connection_manager.connect()
        print("Соединение с RabbitMQ установлено.")

    @app.on_event("shutdown")
    async def shutdown_event():
        print("Остановка приложения...")
        await rabbit_connection_manager.disconnect()
        print("Соединение с RabbitMQ закрыто.")

    setup_docs(
        app=app,
        version="v1",
        project_name=project_name,
        service_name=settings.users_settings.service_name,
        routes=[
            route
            for router in v1_users_routers+v1_auth_routers+v1_chats_routers
            for route in router.routes
        ],
    )

    for router in v1_users_routers+v1_auth_routers+v1_chats_routers:
        setup_router(
            app=app,
            router=router,
            version=getattr(router, "version"),
            service_name=getattr(router, "service_name"),
        )

    return app


app: FastAPI = get_application()

if __name__ == "__main__":
    run(
        app=app,
        host=settings.app_settings.wsgi_host,
        port=int(settings.app_settings.wsgi_port),
        use_colors=True,

    )
