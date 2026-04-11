import pytest
from surge_agent.uiux import ALLOWED_DOMAINS, query


def test_allowed_domains():
    assert ALLOWED_DOMAINS == {"landing", "product", "ux"}


def test_rejects_disallowed_domain():
    with pytest.raises(ValueError, match="not available for Surge"):
        query("style", "test")


def test_query_returns_results():
    results = query("ux", "forms validation", limit=2)
    assert isinstance(results, list)
    assert len(results) > 0
