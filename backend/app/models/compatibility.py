from typing import Literal

from pydantic import Field

from app.models.base import DomainModel
from app.models.keyboard import KeyboardDefinition
from app.models.keycap import KeycapSet


class CompatibilityRequest(DomainModel):
    keyboard: KeyboardDefinition
    keycap_set: KeycapSet


class KeyFitIssue(DomainModel):
    key: str
    required_width_u: float
    reason: str


class CompatibilityResult(DomainModel):
    status: Literal["compatible", "incompatible", "unknown"]
    compatible: bool
    missing: list[KeyFitIssue] = Field(default_factory=list)
    uncertain: list[KeyFitIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
