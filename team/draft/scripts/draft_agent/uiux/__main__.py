"""CLI: python3 -m draft_agent.uiux search --domain X --query 'Y'"""

import argparse
import json
import sys

from . import ALLOWED_DOMAINS, query


def main():
    parser = argparse.ArgumentParser(description="Draft design intelligence")
    sub = parser.add_subparsers(dest="cmd")

    s = sub.add_parser("search")
    s.add_argument("--domain", required=True, choices=sorted(ALLOWED_DOMAINS))
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=5)

    sub.add_parser("domains")

    args = parser.parse_args()
    if args.cmd == "domains":
        print(json.dumps(sorted(ALLOWED_DOMAINS)))
    elif args.cmd == "search":
        results = query(args.domain, args.query, args.limit)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
