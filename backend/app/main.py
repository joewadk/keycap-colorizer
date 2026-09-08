from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.compatibility import router as compatibility_router
from app.api.capabilities import router as capabilities_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router, prefix="/api")
    application.include_router(compatibility_router, prefix="/api")
    application.include_router(capabilities_router, prefix="/api")
    return application


app = create_app()
