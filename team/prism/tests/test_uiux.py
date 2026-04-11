import pytest
from prism_agent.uiux import ALLOWED_DOMAINS, query


def test_allowed_domains():
    assert ALLOWED_DOMAINS == {"react", "web", "stacks", "icons", "chart"}


def test_rejects_disallowed_domain():
    with pytest.raises(ValueError, match="not available for Prism"):
        query("color", "test")


def test_query_returns_results():
    results = query("chart", "time series", limit=2)
    assert isinstance(results, list)
    assert len(results) > 0
