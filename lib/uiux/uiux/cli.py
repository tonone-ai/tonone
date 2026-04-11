"""
uiux CLI — search design data and generate design systems from the terminal.

Usage:
    python -m uiux search --domain style --query "dark mode dashboard" --limit 3
    python -m uiux design-system --product-type "SaaS analytics"
    python -m uiux domains
"""

import argparse
import json
import sys

from .design_system import generate_design_system
from .search import DOMAINS, search


def _cmd_domains(_args: argparse.Namespace) -> None:
    """List all available search domains as JSON."""
    print(json.dumps(sorted(DOMAINS), indent=2))


def _cmd_search(args: argparse.Namespace) -> None:
    """Run a BM25 search and print results as JSON."""
    try:
        results = search(args.domain, args.query, args.limit)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)

    print(
        json.dumps(
            {
                "domain": args.domain,
                "query": args.query,
                "count": len(results),
                "results": results,
            },
            indent=2,
        )
    )


def _cmd_design_system(args: argparse.Namespace) -> None:
    """Generate a design system and print it as formatted text."""
    output = generate_design_system(args.product_type)
    print(output)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uiux",
        description="UI/UX design intelligence — BM25 search + design system generator.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- domains ---
    subparsers.add_parser("domains", help="List all available search domains.")

    # --- search ---
    search_parser = subparsers.add_parser(
        "search", help="BM25 search over a design domain."
    )
    search_parser.add_argument(
        "--domain",
        required=True,
        choices=sorted(DOMAINS),
        help="Design domain to search.",
    )
    search_parser.add_argument("--query", required=True, help="Search query.")
    search_parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum number of results (default: 3).",
    )

    # --- design-system ---
    ds_parser = subparsers.add_parser(
        "design-system", help="Generate a design system recommendation."
    )
    ds_parser.add_argument(
        "--product-type",
        required=True,
        help="Product description (e.g. 'SaaS dashboard').",
    )

    return parser


def main() -> None:
    """Entry point for the uiux CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    dispatch = {
        "domains": _cmd_domains,
        "search": _cmd_search,
        "design-system": _cmd_design_system,
    }
    dispatch[args.command](args)
