from datetime import datetime, timezone
from typing import Annotated

from pydantic import Field, field_validator

from app.models.base import DomainModel


NonEmptyString = Annotated[str, Field(min_length=1)]


class Configuration(DomainModel):
    id: NonEmptyString
    keyboard_id: NonEmptyString
    keycap_set_id: NonEmptyString
    key_color_map: dict[NonEmptyString, NonEmptyString] = Field(default_factory=dict)
    date_created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: NonEmptyString | None = None

    @field_validator("date_created")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("date_created must include a timezone")
        return value

