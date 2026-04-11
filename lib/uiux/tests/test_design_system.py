"""Tests for uiux.design_system — design system generator."""

import pytest
from uiux.design_system import generate_design_system

# ── basic generation ──────────────────────────────────────────────────────────


def test_generate_returns_string():
    output = generate_design_system("SaaS dashboard")
    assert isinstance(output, str)


def test_generate_not_empty():
    output = generate_design_system("SaaS dashboard")
    assert len(output) > 100


def test_generate_ecommerce():
    output = generate_design_system("e-commerce luxury")
    assert isinstance(output, str)
    assert len(output) > 100


def test_generate_unknown_product_type():
    # Should not raise — falls back to defaults
    output = generate_design_system("something completely unknown xyz123")
    assert isinstance(output, str)


# ── key sections present ──────────────────────────────────────────────────────


def test_output_contains_pattern_section():
    output = generate_design_system("SaaS dashboard")
    assert "PATTERN" in output


def test_output_contains_style_section():
    output = generate_design_system("SaaS dashboard")
    assert "STYLE" in output


def test_output_contains_colors_section():
    output = generate_design_system("SaaS dashboard")
    assert "COLORS" in output


def test_output_contains_typography_section():
    output = generate_design_system("SaaS dashboard")
    assert "TYPOGRAPHY" in output


def test_output_contains_checklist():
    output = generate_design_system("SaaS dashboard")
    assert "PRE-DELIVERY CHECKLIST" in output


def test_output_contains_target_header():
    output = generate_design_system("SaaS dashboard")
    assert "TARGET:" in output


# ── different product types ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "product_type",
    [
        "fintech mobile app",
        "healthcare platform",
        "gaming dashboard",
        "portfolio website",
        "restaurant booking",
    ],
)
def test_generate_various_product_types(product_type):
    output = generate_design_system(product_type)
    assert isinstance(output, str)
    assert "PATTERN" in output
    assert "COLORS" in output
