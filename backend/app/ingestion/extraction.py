import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.ingestion.models import PageEvidence, ProductImage, Specification
from app.ingestion.urls import IntakeError, normalize_url


def extract_page(html: str, source_url: str, final_url: str | None = None) -> PageEvidence:
    source_url = normalize_url(source_url)
    final_url = normalize_url(final_url or source_url)
    soup = BeautifulSoup(html, "html.parser")
    evidence = PageEvidence(source_url=source_url, final_url=final_url)

    def meta(name: str) -> str:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        return str(tag.get("content", "")).strip() if tag else ""

    evidence.title = meta("og:title") or (soup.title.get_text(" ", strip=True) if soup.title else "")
    evidence.description = meta("description") or meta("og:description")

    def visit(value: object) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            types = value.get("@type", [])
            types = [types] if isinstance(types, str) else types
            if isinstance(types, list) and any(str(t).rstrip("/").split("/")[-1] in {"Product", "ProductGroup"} for t in types):
                evidence.products.append(value)
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child)

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            visit(json.loads(script.get_text()))
        except (ValueError, RecursionError):
            evidence.warnings.append("A JSON-LD block could not be parsed.")

    seen_images: set[str] = set()

    def add_image(value: object, alt: str = "") -> None:
        if isinstance(value, list):
            for item in value:
                add_image(item, alt)
        elif isinstance(value, dict):
            add_image(value.get("contentUrl") or value.get("url"), alt)
        elif isinstance(value, str) and value.strip():
            try:
                url = normalize_url(urljoin(final_url, value))
            except IntakeError:
                return
            if url not in seen_images:
                seen_images.add(url)
                evidence.images.append(ProductImage(url=url, alt=alt))

    variants: list[str] = []
    for product in evidence.products:
        if not evidence.title and isinstance(product.get("name"), str):
            evidence.title = product["name"]
        if not evidence.description and isinstance(product.get("description"), str):
            evidence.description = product["description"]
        add_image(product.get("image"))
        color = product.get("color")
        if isinstance(color, str):
            variants.append(color)
    add_image(meta("og:image"))
    add_image(meta("twitter:image"))

    # Drop explicitly hidden markup; this parser does not evaluate stylesheets.
    for tag in soup.select('script, style, noscript, [hidden], [aria-hidden="true"]'):
        tag.decompose()
    for tag in soup.select("[style]"):
        if tag.attrs and re.search(r"(?:display\s*:\s*none|visibility\s*:\s*hidden)", str(tag.get("style", "")), re.I):
            tag.decompose()
    content = soup.find("main") or soup.find("article") or soup
    for tag in content.select("img"):
        if str(tag.get("width", "")) in {"0", "1"} or str(tag.get("height", "")) in {"0", "1"}:
            continue
        add_image(tag.get("data-src") or tag.get("src"), str(tag.get("alt", "")))
        if tag.get("srcset"):
            for candidate in str(tag["srcset"]).split(","):
                if candidate.strip():
                    add_image(candidate.strip().split()[0], str(tag.get("alt", "")))

    for option in content.select("select option"):
        if not option.has_attr("disabled") and option.get("value") != "":
            variants.append(option.get_text(" ", strip=True))
    for label in content.select("label"):
        control = soup.find("input", id=label.get("for")) if label.get("for") else label.find("input")
        if control and control.get("type") == "radio":
            variants.append(label.get_text(" ", strip=True))
    for tag in content.select("[data-option-value], [role='radio']"):
        variants.append(str(tag.get("data-option-value") or tag.get("aria-label") or tag.get_text(" ", strip=True)))
    evidence.variants = list(dict.fromkeys(value.strip() for value in variants if value.strip()))[:100]

    for row in content.select("table tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) >= 2:
            name, value = cells[0].get_text(" ", strip=True), " / ".join(cell.get_text(" ", strip=True) for cell in cells[1:])
            if name and value:
                evidence.specifications.append(Specification(name=name, value=value))
    for term in content.select("dl dt"):
        description = term.find_next_sibling("dd")
        if description:
            evidence.specifications.append(Specification(name=term.get_text(" ", strip=True), value=description.get_text(" ", strip=True)))

    evidence.images = evidence.images[:30]
    evidence.text_excerpt = content.get_text(" ", strip=True)[:20000]
    if not evidence.title:
        evidence.warnings.append("Page title is missing.")
    if not evidence.products:
        evidence.warnings.append("No Product JSON-LD was found; generic page evidence was retained.")
    if not evidence.images:
        evidence.warnings.append("No product image candidates were found.")
    return evidence
