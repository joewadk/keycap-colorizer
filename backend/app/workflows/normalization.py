import hashlib
import re
from typing import Literal

from app.ingestion.models import PageEvidence
from app.ingestion.urls import normalize_url
from app.layouts import LayoutOverrides, LayoutTemplate, build_keyboard_from_template
from app.models.keyboard import KeyboardDefinition
from app.models.keycap import KeycapColor, KeycapProfile, KeycapSet
from app.workflows.models import ReviewRequired


def stable_id(kind: str, url: str) -> str:
    return f"{kind}-{hashlib.sha256(normalize_url(url).encode()).hexdigest()[:16]}"


def _product_name(evidence: PageEvidence) -> str:
    for product in evidence.products:
        if isinstance(product.get("name"), str) and product["name"].strip():
            return product["name"].strip()
    return evidence.title.strip()


def _manufacturer(evidence: PageEvidence) -> str:
    for product in evidence.products:
        brand = product.get("brand")
        if isinstance(brand, dict) and isinstance(brand.get("name"), str) and brand["name"].strip():
            return brand["name"].strip()
        if isinstance(brand, str) and brand.strip():
            return brand.strip()
        value = product.get("manufacturer")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Unknown manufacturer"


def _text(evidence: PageEvidence) -> str:
    specifications = " ".join(f"{item.name} {item.value}" for item in evidence.specifications)
    return f"{evidence.title} {evidence.description} {specifications} {evidence.text_excerpt}"


def classify(evidence: PageEvidence) -> Literal["keyboard", "keycaps", "unknown"]:
    # Product identity is much more reliable than the rest of a commerce page. Long
    # pages commonly mention keycaps, switches, and recommended accessories that are
    # not the product being sold.
    identity = f"{evidence.title} {_product_name(evidence)}".lower()
    if re.search(r"\b(?:keycap|keycaps|key[ -]caps)\s+(?:set|kit)\b|\breplacement\s+keycaps?\b", identity):
        return "keycaps"
    identity_keycaps = bool(re.search(r"\b(?:keycap|keycaps|key[ -]caps)\b", identity))
    identity_keyboard = bool(re.search(r"\b(?:mechanical\s+|gaming\s+|custom\s+)?keyboards?\b|\bbarebones?\b", identity))
    if identity_keyboard and not identity_keycaps:
        return "keyboard"
    if identity_keycaps and not identity_keyboard:
        return "keycaps"

    text = _text(evidence).lower()
    keycaps = sum(term in text for term in ("keycap", "key caps", "keycaps", "cherry profile", "pbt"))
    keyboard = sum(term in text for term in ("keyboard", "barebones", "hot-swap", "hotswap", "ansi 75", "ansi 65", "tkl"))
    if keyboard > keycaps and keyboard:
        return "keyboard"
    if keycaps > keyboard and keycaps:
        return "keycaps"
    return "unknown"


def keyboard_from_evidence(evidence: PageEvidence) -> tuple[KeyboardDefinition, list[str]]:
    text = _text(evidence)
    candidates = []
    if re.search(r"(?i)ANSI\s*65\s*%|\b65\s*%\s*(?:keyboard|layout)", text):
        candidates.append(LayoutTemplate.ANSI_65)
    if re.search(r"(?i)ANSI\s*75\s*%|\b75\s*%\s*(?:keyboard|layout)", text):
        candidates.append(LayoutTemplate.ANSI_75)
    if re.search(r"(?i)ANSI\s*TKL|tenkeyless|\bTKL\b", text):
        candidates.append(LayoutTemplate.ANSI_TKL)
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) != 1:
        raise ReviewRequired("Keyboard layout needs review. The page must clearly identify ANSI 65%, ANSI 75%, or ANSI TKL.")
    name = _product_name(evidence)
    if not name:
        raise ReviewRequired("Keyboard name is missing; raw page evidence was retained.")
    lower = text.lower()
    material = next((value for value in ("aluminum", "plastic", "polycarbonate", "acrylic") if value in lower), None)
    warnings = ["Case color was not explicitly identified; a neutral preview color is used."]
    board = build_keyboard_from_template(
        candidates[0], keyboard_id=stable_id("keyboard", evidence.source_url),
        manufacturer=_manufacturer(evidence), model=name, source_url=evidence.source_url,
        case_color="#303735", overrides=LayoutOverrides(
            knob=bool(re.search(r"(?i)\bknob\b", text)),
            screen=bool(re.search(r"(?i)\b(?:screen|display)\b", text)),
            badge=bool(re.search(r"(?i)\bbadge\b", text)),
        ),
    )
    if material:
        board.case.material = material.title()
    return board, warnings


def explicit_colors(evidence: PageEvidence) -> list[KeycapColor]:
    sources = list(evidence.variants)
    sources.extend(f"{item.name}: {item.value}" for item in evidence.specifications)
    colors: list[KeycapColor] = []
    seen = set()
    for source in sources:
        # Accept explicit labeled codes, never infer RGB from a color name.
        for name, value in re.findall(r"([A-Za-z][A-Za-z0-9 _-]{0,40}?)\s*[:=]?\s*(#[0-9A-Fa-f]{6})\b", source):
            clean_name = re.sub(r"(?i)\b(?:colors?|codes?)\b\s*[:=-]?\s*", "", name).strip(" :-")
            if not clean_name or value.upper() in seen:
                continue
            seen.add(value.upper())
            identifier = re.sub(r"[^a-z0-9]+", "-", clean_name.lower()).strip("-") or f"color-{len(colors)+1}"
            colors.append(KeycapColor(id=identifier, name=clean_name, hex=value, source="manufacturer", confidence=1.0))
    return colors


def keycaps_from_evidence(evidence: PageEvidence, sampled: list[KeycapColor] | None = None) -> tuple[KeycapSet, list[str]]:
    name = _product_name(evidence)
    if not name:
        raise ReviewRequired("Keycap-set name is missing; raw page evidence was retained.")
    colors = explicit_colors(evidence)
    warnings = []
    if not colors and sampled:
        colors = sampled
        warnings.append("No manufacturer color codes were found; approximate image samples are used.")
    if not colors:
        raise ReviewRequired("Keycap colors need review. No explicit color codes or usable image samples were found.")
    text = _text(evidence).lower()
    profile = next((profile for profile in KeycapProfile if profile is not KeycapProfile.UNKNOWN and profile.value.lower() in text), KeycapProfile.UNKNOWN)
    warnings.append("Key inventory was not proven by the page, so compatibility remains unverified.")
    return KeycapSet(
        id=stable_id("keycaps", evidence.source_url), manufacturer=_manufacturer(evidence), name=name,
        profile=profile, colors=colors, supported_keys=[], source_url=evidence.source_url,
    ), warnings
