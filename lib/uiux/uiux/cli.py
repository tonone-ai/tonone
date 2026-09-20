"""
uiux CLI — search design data and generate design systems from the terminal.

Usage:
    python -m uiux search --domain style --query "dark mode dashboard" --limit 3
    python -m uiux design-system --product-type "SaaS analytics"
    python -m uiux domains
    python -m uiux stacks
    python -m uiux stack --stack shadcn --query "form validation"
"""

import argparse
import json
import sys

from .design_system import generate_design_system
from .search import AVAILABLE_STACKS, DOMAINS, STACK_ALIASES, search, search_stack


def _cmd_domains(_args: argparse.Namespace) -> None:
    """List all available search domains as JSON."""
    print(json.dumps(sorted(DOMAINS), indent=2))


def _cmd_stacks(_args: argparse.Namespace) -> None:
    """List all available stack guideline sets as JSON."""
    print(json.dumps(sorted(AVAILABLE_STACKS), indent=2))


def _cmd_stack(args: argparse.Namespace) -> None:
    """Run a BM25 search over one stack's guidelines and print results as JSON."""
    try:
        results = search_stack(args.stack, args.query, args.limit)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)

    print(
        json.dumps(
            {
                "stack": STACK_ALIASES.get(args.stack, args.stack),
                "query": args.query,
                "count": len(results),
                "results": results,
            },
            indent=2,
        )
    )


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

    # --- stacks ---
    subparsers.add_parser("stacks", help="List all available stack guideline sets.")

    # --- stack ---
    stack_parser = subparsers.add_parser(
        "stack", help="BM25 search over one stack's guidelines."
    )
    stack_parser.add_argument(
        "--stack",
        required=True,
        choices=sorted(set(AVAILABLE_STACKS) | set(STACK_ALIASES)),
        help="Stack to search (e.g. react, shadcn, swiftui).",
    )
    stack_parser.add_argument("--query", required=True, help="Search query.")
    stack_parser.add_argument(
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
        "stacks": _cmd_stacks,
        "stack": _cmd_stack,
        "design-system": _cmd_design_system,
    }
    dispatch[args.command](args)
