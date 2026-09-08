from fastapi import APIRouter

from app.models.compatibility import CompatibilityRequest, CompatibilityResult
from app.services.compatibility import check_compatibility

router = APIRouter(tags=["compatibility"])


@router.post("/compatibility/check", response_model=CompatibilityResult)
def check(request: CompatibilityRequest) -> CompatibilityResult:
    return check_compatibility(request.keyboard, request.keycap_set)
