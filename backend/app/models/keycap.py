import re
from enum import StrEnum
from typing import Annotated

from pydantic import Field, HttpUrl, field_validator, model_validator

from app.models.base import DomainModel


NonEmptyString = Annotated[str, Field(min_length=1)]
KeyboardUnit = Annotated[float, Field(gt=0, le=20)]
HEX_COLOR = re.compile(r"^#[0-9A-F]{6}$")


class KeycapProfile(StrEnum):
    CHERRY = "Cherry"
    OEM = "OEM"
    XDA = "XDA"
    DSA = "DSA"
    SA = "SA"
    UNKNOWN = "Unknown"


class ColorSource(StrEnum):
    PRESET = "preset"
    MANUFACTURER = "manufacturer"
    IMAGE_SAMPLE = "image_sample"
    MODEL_ESTIMATE = "model_estimate"


class KeycapColor(DomainModel):
    id: NonEmptyString
    name: NonEmptyString
    hex: str
    source: ColorSource
    confidence: Annotated[float, Field(ge=0, le=1)] | None = None

    @field_validator("hex", mode="before")
    @classmethod
    def normalize_hex(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip().upper()
        if re.fullmatch(r"[0-9A-F]{6}", normalized):
            normalized = f"#{normalized}"
        if not HEX_COLOR.fullmatch(normalized):
            raise ValueError("hex must be a six-digit RGB color")
        return normalized


class SupportedKey(DomainModel):
    legend: NonEmptyString | None = None
    width_u: KeyboardUnit
    quantity: Annotated[int, Field(gt=0)] | None = None


class KeycapSet(DomainModel):
    id: NonEmptyString
    manufacturer: NonEmptyString
    name: NonEmptyString
    profile: KeycapProfile = KeycapProfile.UNKNOWN
    colors: Annotated[list[KeycapColor], Field(min_length=1)]
    supported_keys: list[SupportedKey] = Field(default_factory=list)
    source_url: HttpUrl

    @model_validator(mode="after")
    def require_unique_color_ids(self) -> "KeycapSet":
        color_ids = [color.id for color in self.colors]
        if len(color_ids) != len(set(color_ids)):
            raise ValueError("keycap color IDs must be unique")
        return self
