from typing import Annotated, Literal

from pydantic import Field

from app.models.base import DomainModel
from app.models.configuration import CaseColor, Configuration
from app.models.compatibility import CompatibilityResult
from app.models.keyboard import KeyboardDefinition
from app.models.keycap import KeycapSet


class KeyboardImport(DomainModel):
    kind: Literal["keyboard"]
    product: KeyboardDefinition


class KeycapImport(DomainModel):
    kind: Literal["keycaps"]
    product: KeycapSet


ProductRecord = Annotated[KeyboardImport | KeycapImport, Field(discriminator="kind")]


class ConfigurationCreate(DomainModel):
    case_color: CaseColor | None = None
    keyboard_id: Annotated[str, Field(min_length=1)]
    keycap_set_id: Annotated[str, Field(min_length=1)]
    key_color_map: dict[Annotated[str, Field(min_length=1)], Annotated[str, Field(min_length=1)]] = Field(default_factory=dict)
    name: Annotated[str, Field(min_length=1, max_length=200)] | None = None


class RestoredConfiguration(DomainModel):
    configuration: Configuration
    keyboard: KeyboardDefinition
    keycap_set: KeycapSet
    compatibility: CompatibilityResult
