import pytest
from draft_agent.uiux import ALLOWED_DOMAINS, query


def test_allowed_domains():
    assert ALLOWED_DOMAINS == {"ux", "landing", "product"}


def test_rejects_disallowed_domain():
    with pytest.raises(ValueError, match="not available for Draft"):
        query("style", "test")


def test_query_returns_results():
    results = query("ux", "navigation", limit=2)
    assert isinstance(results, list)
    assert len(results) > 0
