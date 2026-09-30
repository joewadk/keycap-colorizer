from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from app.models.base import DomainModel
from app.models.compatibility import CompatibilityResult
from app.models.keyboard import KeyboardDefinition
from app.models.keycap import KeycapSet
from app.ingestion.models import PageEvidence


class WorkflowStep(StrEnum):
    QUEUED = "QUEUED"
    CHECKING_CACHE = "CHECKING_CACHE"
    FETCHING_PAGE = "FETCHING_PAGE"
    EXTRACTING_METADATA = "EXTRACTING_METADATA"
    CLASSIFYING_PRODUCT = "CLASSIFYING_PRODUCT"
    ANALYZING_LAYOUT = "ANALYZING_LAYOUT"
    EXTRACTING_COLORS = "EXTRACTING_COLORS"
    VALIDATING = "VALIDATING"
    SAVING = "SAVING"
    COMPLETE = "COMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


class ProgressEvent(DomainModel):
    step: WorkflowStep
    message: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IntakeRequest(DomainModel):
    keyboard_url: str
    keycap_url: str
    provider: Literal["playwright", "firecrawl"] | None = None
    refresh: bool = False


class WorkflowResult(DomainModel):
    keyboard: KeyboardDefinition
    keycap_set: KeycapSet
    compatibility: CompatibilityResult
    warnings: list[str] = Field(default_factory=list)
    cached_products: list[Literal["keyboard", "keycaps"]] = Field(default_factory=list)


class IntakeJob(DomainModel):
    id: str
    status: Literal["queued", "running", "complete", "needs_review", "failed"] = "queued"
    step: WorkflowStep = WorkflowStep.QUEUED
    events: list[ProgressEvent] = Field(default_factory=list)
    message: str = "Queued for local processing."
    result: WorkflowResult | None = None
    review_evidence: list[PageEvidence] = Field(default_factory=list)


class ReviewRequired(ValueError):
    def __init__(self, message: str, warnings: list[str] | None = None, evidence: PageEvidence | None = None):
        super().__init__(message)
        self.warnings = warnings or []
        self.evidence = evidence
