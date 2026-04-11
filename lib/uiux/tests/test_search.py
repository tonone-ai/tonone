"""Tests for uiux.search — BM25 search engine."""

import pytest
from uiux.search import DOMAINS, search

# ── domain coverage ──────────────────────────────────────────────────────────


def test_domains_not_empty():
    assert len(DOMAINS) > 0


def test_known_domains_present():
    expected = {
        "style",
        "color",
        "product",
        "typography",
        "ux",
        "landing",
        "chart",
        "icons",
        "react",
        "web",
        "google-fonts",
    }
    assert expected.issubset(DOMAINS)


# ── search basic behaviour ────────────────────────────────────────────────────


def test_search_returns_list():
    results = search("style", "minimalism clean")
    assert isinstance(results, list)


def test_search_returns_results():
    results = search("style", "minimalism")
    assert len(results) > 0


def test_search_respects_limit():
    results = search("style", "design", limit=2)
    assert len(results) <= 2


def test_search_default_limit():
    results = search("style", "dark mode dashboard")
    assert len(results) <= 3


def test_search_returns_dicts():
    results = search("product", "saas dashboard")
    assert all(isinstance(r, dict) for r in results)


def test_search_result_has_expected_fields_style():
    results = search("style", "minimalism")
    if results:
        assert "Style Category" in results[0]


def test_search_result_has_expected_fields_color():
    results = search("color", "saas")
    if results:
        assert "Product Type" in results[0]


def test_search_result_has_expected_fields_product():
    results = search("product", "ecommerce")
    if results:
        assert "Product Type" in results[0]


def test_search_result_has_expected_fields_typography():
    results = search("typography", "modern clean")
    if results:
        assert "Heading Font" in results[0]


def test_search_result_has_expected_fields_google_fonts():
    results = search("google-fonts", "sans-serif")
    if results:
        assert "Family" in results[0]


# ── edge cases ────────────────────────────────────────────────────────────────


def test_invalid_domain_raises():
    with pytest.raises(ValueError, match="Unknown domain"):
        search("nonexistent-domain", "query")


def test_empty_query_returns_list():
    # Empty query has no tokens — BM25 returns scores of 0 for all docs,
    # so results may be empty but should not raise.
    results = search("style", "")
    assert isinstance(results, list)


def test_all_domains_searchable():
    """Every domain should be searchable without raising an exception."""
    for domain in DOMAINS:
        results = search(domain, "design", limit=1)
        assert isinstance(results, list), f"domain {domain!r} did not return a list"
