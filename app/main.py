"""FastAPI application entry point."""

from fastapi import FastAPI

from app.routers.health import router as health_router


def create_app() -> FastAPI:
    """Build and configure the DevFix FastAPI application."""
    application = FastAPI(
        title="DevFix API",
        summary="AI 协作开发问题闭环系统",
        version="0.1.0",
    )
    application.include_router(health_router)
    return application


app = create_app()

