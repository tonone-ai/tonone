import pytest
from lens_agent.uiux import ALLOWED_DOMAINS, query


def test_allowed_domains():
    assert ALLOWED_DOMAINS == {"chart", "style"}


def test_rejects_disallowed_domain():
    with pytest.raises(ValueError, match="not available for Lens"):
        query("color", "test")


def test_query_returns_results():
    results = query("chart", "comparison", limit=2)
    assert isinstance(results, list)
    assert len(results) > 0
