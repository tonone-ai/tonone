import pytest
from form_agent.uiux import ALLOWED_DOMAINS, query


def test_allowed_domains():
    assert ALLOWED_DOMAINS == {
        "style",
        "color",
        "typography",
        "google-fonts",
        "product",
    }


def test_rejects_disallowed_domain():
    with pytest.raises(ValueError, match="not available for Form"):
        query("ux", "test")


def test_query_returns_results():
    results = query("color", "fintech", limit=2)
    assert isinstance(results, list)
    assert len(results) > 0
