from pathlib import Path

import pytest

from app.ingestion.extraction import extract_page
from app.ingestion.urls import IntakeError, normalize_url

FIXTURES = Path(__file__).parent / "fixtures"


def test_keyboard_metadata_specifications_and_images():
    page = extract_page((FIXTURES / "keyboard_product.html").read_text(), "https://example.com/board")
    assert page.title == "Compact 75 Keyboard"
    assert "aluminum" in page.description
    assert page.products[0]["brand"]["name"] == "Example"
    assert page.variants == ["Black", "Silver"]
    assert [(spec.name, spec.value) for spec in page.specifications] == [("Layout", "ANSI 75%"), ("Case", "Aluminum")]
    assert [image.url for image in page.images] == ["https://example.com/images/board.png", "https://example.com/images/board-side.png"]


def test_keycap_arrays_radio_labels_and_relative_images():
    page = extract_page((FIXTURES / "keycap_product.html").read_text(), "https://example.com/products/caps")
    assert page.title == "Forest Keycaps"
    assert page.variants == ["Forest", "Bone", "Moss"]
    assert len(page.images) == 2
    assert page.images[0].url == "https://example.com/caps.jpg"
    assert page.specifications[0].value == "Cherry"


def test_malformed_and_missing_metadata_remain_explicit():
    page = extract_page((FIXTURES / "malformed_product.html").read_text(), "https://example.com/item")
    assert not page.products and not page.title
    assert any("JSON-LD block" in warning for warning in page.warnings)
    assert "unavailable" in page.text_excerpt


def test_url_normalization_preserves_product_variant_query():
    assert normalize_url(" HTTPS://EXAMPLE.COM:443/item?variant=blue#photos ") == "https://example.com/item?variant=blue"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "https://user:secret@example.com", "http://localhost", "http://127.0.0.1", "http://[::1]", "http://192.168.1.2", "http://example.com:8080", "https://example.com/a b", "no-url"])
def test_reject_invalid_or_local_urls(url):
    with pytest.raises(IntakeError):
        normalize_url(url)
