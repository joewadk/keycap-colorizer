from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.base import DomainModel

router = APIRouter()


class Capabilities(DomainModel):
    ai_enabled: bool
    message: str


@router.get("/capabilities", response_model=Capabilities)
def capabilities(settings: Settings = Depends(get_settings)) -> Capabilities:
    enabled = bool(settings.ai_provider and settings.openai_api_key.get_secret_value().strip()
                   and settings.openai_model.strip())
    return Capabilities(ai_enabled=enabled, message=
        "AI product understanding configured; available through the intake CLI." if enabled else
        "AI product understanding is disabled. The sample keyboard works without an AI key.")
