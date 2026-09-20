from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.compatibility import router as compatibility_router
from app.api.capabilities import router as capabilities_router
from app.api.storage import router as storage_router
from app.ingestion.urls import IntakeError
from app.storage.repository import Conflict, InvalidConfiguration, NotFound, StorageError
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
    application.include_router(storage_router, prefix="/api")

    async def storage_error_handler(request, error):
        codes = {NotFound: 404, Conflict: 409, InvalidConfiguration: 422, StorageError: 503, IntakeError: 422}
        return JSONResponse(status_code=codes[type(error)], content={"detail": str(error)})

    for error_type in (NotFound, Conflict, InvalidConfiguration, StorageError, IntakeError):
        application.add_exception_handler(error_type, storage_error_handler)
    return application


app = create_app()
