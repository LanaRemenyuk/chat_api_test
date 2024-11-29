from typing import Any, Callable, Optional, Sequence

from fastapi import Depends, FastAPI, status
from fastapi.exceptions import HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRouter
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import HTMLResponse
from starlette.routing import BaseRoute

from apps.core.config import settings

def docs_basic_auth(
    auth: Optional[HTTPBasicCredentials] = Depends(
        HTTPBasic(),
    ),
) -> Optional[HTTPException]:
    if not settings.app_settings.docs_basic_credentials:
        return None

    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if settings.app_settings.docs_basic_credentials != f"{auth.username}:{auth.password}":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return None

def get_definition(
    service_name: str,
    routes: list[BaseRoute],
) -> Callable[..., Any]:
    title: str = service_name.title().replace("/", " ")
    description: str = f"{title} API documentation"

    async def definition_handler(
        version: str,
    ) -> dict[str, Any]:
        return get_openapi(
            title=title,
            description=description,
            version=version,
            routes=routes,
        )

    return definition_handler

def get_documentation(
    service_name: str,
    openapi_url: str,
) -> Callable[..., Any]:
    async def get_documentation() -> HTMLResponse:
        return get_swagger_ui_html(
            title=f"{service_name.upper()} service",
            openapi_url=openapi_url,
        )

    return get_documentation

def setup_docs(
    app: FastAPI,
    project_name: str,
    service_name: str,
    version: str,
    routes: list[BaseRoute],
) -> None:
    path: str = "{version:path}"

    app.add_api_route(
        path=f"/{service_name}/api/{path}/definition",
        include_in_schema=False,
        methods=[
            "GET",
        ],
        dependencies=[
            Depends(docs_basic_auth),
        ],
        endpoint=get_definition(
            service_name=project_name,
            routes=routes,
        ),
    )

    app.add_api_route(
        path=f"/{service_name}/api/{version}/docs",
        include_in_schema=False,
        methods=[
            "GET",
        ],
        dependencies=[
            Depends(docs_basic_auth),
        ],
        endpoint=get_documentation(
            service_name=project_name,
            openapi_url=f"/{service_name}/api/{version}/definition",
        ),
    )

def setup_router(
    app: FastAPI,
    router: APIRouter,
    version: str,
    service_name: str,
    project_name: str | None = None,
    dependencies: Optional[Sequence[Any]] = [],
) -> None:
    path: str = "{version:path}"
    name: str = ""

    if project_name:
        name += f"{project_name}/{service_name}"
    else:
        name += f"{service_name}"

    app.add_api_route(
        path=f"/{name}/api/{path}/definition",
        include_in_schema=False,
        methods=[
            "GET",
        ],
        dependencies=[
            Depends(docs_basic_auth),
        ],
        endpoint=get_definition(
            service_name=service_name,
            routes=router.routes,
        ),
    )

    app.add_api_route(
        path=f"/{name}/api/{version}/docs",
        include_in_schema=False,
        methods=[
            "GET",
        ],
        dependencies=[
            Depends(docs_basic_auth),
        ],
        endpoint=get_documentation(
            service_name=service_name,
            openapi_url=f"/{name}/api/{version}/definition",
        ),
    )

    app.include_router(
        router=router,
        dependencies=dependencies,
        tags=[
            service_name.capitalize(),
        ],
    )