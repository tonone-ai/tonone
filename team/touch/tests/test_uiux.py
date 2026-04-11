import pytest
from touch_agent.uiux import ALLOWED_DOMAINS, query


def test_allowed_domains():
    assert ALLOWED_DOMAINS == {"app-interface", "stacks"}


def test_rejects_disallowed_domain():
    with pytest.raises(ValueError, match="not available for Touch"):
        query("style", "test")


def test_query_returns_results():
    results = query("app-interface", "touch targets", limit=2)
    assert isinstance(results, list)
    assert len(results) > 0
