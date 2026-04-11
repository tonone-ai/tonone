"""Lens agent design intelligence — chart and style domains (style auto-scoped to BI)."""

try:
    from uiux.search import search
except ImportError:

    def _missing(*a, **kw):
        raise RuntimeError(
            "uiux package not found — run: cd lib/uiux && bash setup.sh, "
            "then reinstall this agent"
        )

    search = _missing

ALLOWED_DOMAINS = {"chart", "style"}


def query(domain: str, terms: str, limit: int = 5) -> list[dict]:
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(
            f"Domain '{domain}' not available for Lens agent. "
            f"Allowed: {sorted(ALLOWED_DOMAINS)}"
        )
    if domain == "style":
        terms = f"{terms} BI Dashboard"
    return search(domain=domain, query=terms, limit=limit)
