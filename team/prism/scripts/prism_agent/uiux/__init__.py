"""Prism agent design intelligence — react, web, stacks, icons, and chart domains."""

try:
    from uiux.search import search, search_stack
except ImportError:

    def _missing(*a, **kw):
        raise RuntimeError(
            "uiux package not found — run: cd lib/uiux && bash setup.sh, "
            "then reinstall this agent"
        )

    search = _missing
    search_stack = _missing

ALLOWED_DOMAINS = {"react", "web", "stacks", "icons", "chart"}


def query(domain: str, terms: str, limit: int = 5) -> list[dict]:
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(
            f"Domain '{domain}' not available for Prism agent. "
            f"Allowed: {sorted(ALLOWED_DOMAINS)}"
        )
    if domain == "stacks":
        return search_stack(stack=terms.split()[0].lower(), query=terms, limit=limit)
    return search(domain=domain, query=terms, limit=limit)


def stack_guide(stack_name: str, query: str = "", limit: int = 5) -> list[dict]:
    """Load guidelines for a specific framework."""
    return search_stack(stack=stack_name, query=query, limit=limit)
