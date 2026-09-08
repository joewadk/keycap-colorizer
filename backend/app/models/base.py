from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class DomainModel(BaseModel):
    """Strict base model for persisted and API-facing domain data."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
        alias_generator=to_camel,
        serialize_by_alias=True,
    )
