#!/usr/bin/env python3
"""Seeded random pick of N items. Stdlib only, no network.

Usage:
  roulette.py --seed S --pick 3 item1 item2 ...
  printf 'a\nb\nc\n' | roulette.py --pick 2

Prints "seed: <S>" then one picked item per line. Same seed + same item
list (same order) gives the same picks. Exit 2 on usage errors.
"""

import argparse
import random
import sys
import time


def main(argv=None):
    p = argparse.ArgumentParser(description="Deterministic seeded picker")
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="integer seed (default: time-based, printed)",
    )
    p.add_argument(
        "--pick", type=int, default=3, help="how many items to pick (default 3)"
    )
    p.add_argument(
        "items", nargs="*", help="items; if none, read newline list from stdin"
    )
    try:
        args = p.parse_args(argv)
    except SystemExit as e:
        sys.exit(2 if e.code not in (0, None) else 0)

    items = args.items
    if not items and not sys.stdin.isatty():
        items = [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]
    if args.pick < 1:
        print("error: --pick must be >= 1", file=sys.stderr)
        return 2
    if len(items) < args.pick:
        print(
            f"error: need at least {args.pick} items, got {len(items)}", file=sys.stderr
        )
        return 2

    seed = (
        args.seed if args.seed is not None else int(time.time() * 1000) % 1_000_000_000
    )
    rng = random.Random(seed)
    picks = rng.sample(items, args.pick)
    print(f"seed: {seed}")
    for it in picks:
        print(it)
    return 0


if __name__ == "__main__":
    sys.exit(main())
