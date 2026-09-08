from enum import StrEnum
from typing import Annotated

from pydantic import Field, HttpUrl, model_validator

from app.models.base import DomainModel


NonEmptyString = Annotated[str, Field(min_length=1)]
KeyboardUnit = Annotated[float, Field(gt=0, le=20)]
Coordinate = Annotated[float, Field(ge=0)]


class LayoutType(StrEnum):
    SIXTY = "60"
    SIXTY_FIVE = "65"
    SEVENTY = "70"
    SEVENTY_FIVE = "75"
    TKL = "TKL"
    NINETY_SIX = "96"
    FULL_SIZE = "100"
    OTHER = "OTHER"


class KeyboardCase(DomainModel):
    color: NonEmptyString
    material: NonEmptyString | None = None
    width_mm: Annotated[float, Field(gt=0)] | None = None
    depth_mm: Annotated[float, Field(gt=0)] | None = None
    height_mm: Annotated[float, Field(gt=0)] | None = None
    corner_radius_mm: Annotated[float, Field(ge=0)] | None = None


class KeyboardFeatures(DomainModel):
    knob: bool = False
    screen: bool = False
    badge: bool = False


class KeyboardKey(DomainModel):
    id: NonEmptyString
    legend: str
    row: Annotated[int, Field(ge=0)]
    x: Coordinate
    y: Coordinate
    width_u: KeyboardUnit = 1.0
    height_u: KeyboardUnit = 1.0
    stabilizer: bool = False
    group: list[NonEmptyString] = Field(default_factory=list)


class KeyboardDefinition(DomainModel):
    id: NonEmptyString
    manufacturer: NonEmptyString
    model: NonEmptyString
    layout_type: LayoutType
    case: KeyboardCase
    keys: Annotated[list[KeyboardKey], Field(min_length=1)]
    features: KeyboardFeatures = Field(default_factory=KeyboardFeatures)
    source_url: HttpUrl

    @model_validator(mode="after")
    def require_unique_key_ids(self) -> "KeyboardDefinition":
        key_ids = [key.id for key in self.keys]
        if len(key_ids) != len(set(key_ids)):
            raise ValueError("keyboard key IDs must be unique")
        return self

