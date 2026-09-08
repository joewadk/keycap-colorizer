from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.ingestion.models import PageEvidence
from app.layouts.templates import LayoutTemplate
from app.models.base import DomainModel


class ProductUnderstanding(DomainModel):
    # Required nullable fields work with strict structured-output providers.
    product_type: Literal["keyboard", "keycaps", "unknown"]
    confidence: Annotated[float, Field(ge=0, le=1)]
    manufacturer: Annotated[str, Field(min_length=1, max_length=200)] | None
    name: Annotated[str, Field(min_length=1, max_length=300)] | None
    layout_template: LayoutTemplate | None
    layout_confidence: Annotated[float, Field(ge=0, le=1)]
    knob: bool | None
    screen: bool | None
    badge: bool | None
    color_names: Annotated[list[str], Field(max_length=30)]
    notes: Annotated[list[str], Field(max_length=20)]

    @model_validator(mode="after")
    def layout_belongs_to_keyboard(self):
        if self.product_type != "keyboard" and self.layout_template is not None:
            raise ValueError("Only keyboards may have a layout template")
        return self


class UnderstandingResult(DomainModel):
    status: Literal["complete", "needs_review", "disabled", "failed"]
    evidence: PageEvidence
    understanding: ProductUnderstanding | None = None
    message: str
