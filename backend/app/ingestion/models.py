from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.base import DomainModel


class ProductImage(DomainModel):
    url: str
    alt: str = ""


class Specification(DomainModel):
    name: str
    value: str


class PageEvidence(DomainModel):
    source_url: str
    final_url: str
    title: str = ""
    description: str = ""
    products: list[dict] = Field(default_factory=list)
    variants: list[str] = Field(default_factory=list)
    images: list[ProductImage] = Field(default_factory=list)
    specifications: list[Specification] = Field(default_factory=list)
    text_excerpt: str = ""
    warnings: list[str] = Field(default_factory=list)


class ScrapeResult(DomainModel):
    provider: Literal["playwright", "firecrawl"] = "playwright"
    evidence: PageEvidence
    cached: bool
    fetched_at: datetime
