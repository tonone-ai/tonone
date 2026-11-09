"""Tests for team/form/scripts/direction-roulette/roulette.py."""

import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "team/form/scripts/direction-roulette/roulette.py"
)
ITEMS = [
    "manifests",
    "port-signage",
    "cb-radio",
    "diners",
    "iata",
    "pallets",
    "tide-tables",
]


def run(args, stdin=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
    )


def picks(out):
    lines = out.strip().splitlines()
    assert lines[0].startswith("seed: ")
    return lines[1:]


def test_deterministic_with_seed():
    a = run(["--seed", "42", "--pick", "3", *ITEMS])
    b = run(["--seed", "42", "--pick", "3", *ITEMS])
    assert a.returncode == 0
    assert a.stdout == b.stdout


def test_picks_distinct_and_from_items():
    r = run(["--seed", "7", "--pick", "3", *ITEMS])
    p = picks(r.stdout)
    assert len(p) == 3 and len(set(p)) == 3
    assert set(p) <= set(ITEMS)


def test_pick_exceeds_items_exits_2():
    r = run(["--seed", "1", "--pick", "5", "a", "b"])
    assert r.returncode == 2


def test_stdin_input():
    r = run(["--seed", "9", "--pick", "2"], stdin="\n".join(ITEMS) + "\n")
    assert r.returncode == 0
    assert len(picks(r.stdout)) == 2
    assert r.stdout == run(["--seed", "9", "--pick", "2", *ITEMS]).stdout


def test_default_seed_printed():
    r = run(["--pick", "2", *ITEMS])
    assert r.returncode == 0
    seed = r.stdout.splitlines()[0].split(": ")[1]
    r2 = run(["--seed", seed, "--pick", "2", *ITEMS])
    assert r.stdout == r2.stdout
