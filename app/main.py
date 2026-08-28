"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.db import DatabaseResources, build_database_resources
from app.routers.health import router as health_router
from app.routers.issues import router as issues_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the DevFix FastAPI application."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
        resolved_settings = settings if settings is not None else get_settings()
        resources: DatabaseResources | None = None

        if resolved_settings.database_url is not None:
            resources = build_database_resources(
                resolved_settings.database_url.get_secret_value()
            )
        #resolved_settings.database_url.get_secret_value()是取得了URL

        application.state.database_resources = resources

        #这样写，fastapi的可以让Request取到resources

        try:
            yield
        finally:
            if resources is not None:
                #resources是DatabaseResources的对象，所以可以使用dispose方法
                await resources.dispose()
            application.state.database_resources = None

    application = FastAPI(
        title="DevFix API",
        summary="AI 协作开发问题闭环系统",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(issues_router)
    return application


app = create_app()
