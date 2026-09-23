#!/usr/bin/env python3
"""tonone's opt-in bridge to jev-ultrafast (github.com/browser-use/jev-ultrafast).

Two commands, one JSON object on stdout, exit code 0 always:

    python3 lib/jev-ultrafast/cli.py preflight
    python3 lib/jev-ultrafast/cli.py explore --url URL --goal 'One outcome' [--goal ...]

`preflight` answers one question — is the live-exploration path available right
now — without touching the network, importing anything, or prompting. `explore`
runs one flow through the driver and returns a flow transcript.

Design rules, inherited from lib/jev/README.md and docs/jev-ultrafast.md:

  1. Never throws, never prompts, never blocks. Unavailable is a JSON answer,
     not an error. Callers fall back to gstack `/browse`, then to source-only.
  2. Credentials are environment-only. Nothing here reads a config file or
     writes a key anywhere.
  3. Deny-default on targets. Localhost and explicitly allowlisted hosts only;
     anything else is refused, production included.
  4. Standard library only. tonone gains no dependency from this file.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
RUNNER = HERE / "runner.py"

OPT_IN = "TONONE_JEV_ULTRAFAST"
HOME = "TONONE_JEV_ULTRAFAST_HOME"
CMD = "TONONE_JEV_ULTRAFAST_CMD"
HOSTS = "TONONE_JEV_ULTRAFAST_HOSTS"

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}

DEFAULT_MAX_STEPS = 20
DEFAULT_TIMEOUT = 180.0


def emit(payload):
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.exit(0)


def allowed_hosts():
    raw = os.environ.get(HOSTS, "")
    return [h.strip().lower() for h in raw.split(",") if h.strip()]


def host_allowed(url):
    """Deny-default target check. Returns (ok, host, reason)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, None, "unparseable_url"
    if parsed.scheme not in {"http", "https", "file"}:
        return False, None, "unsupported_scheme"
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "file":
        return True, "file", None
    if not host:
        return False, None, "no_host"
    if host in LOCAL_HOSTS or host.endswith(".localhost"):
        return True, host, None
    for allowed in allowed_hosts():
        if host == allowed or (allowed.startswith(".") and host.endswith(allowed)):
            return True, host, None
    return False, host, "host_not_allowed"


def driver_home():
    raw = os.environ.get(HOME, "").strip()
    if not raw:
        return None, "home_unset"
    path = Path(raw).expanduser()
    if not path.is_dir():
        return None, "home_missing"
    if not (path / "jev_ultrafast").is_dir():
        return None, "home_not_a_checkout"
    return path, None


def child_env(home):
    """Environment for the driver subprocess.

    The one trap worth encoding: lib/jev accepts either JEV_API_KEY or
    TYPESAFE_API_KEY, jev-ultrafast reads only TYPESAFE_API_KEY. A user with
    JEV_API_KEY alone would otherwise pass preflight and fail on the first
    model call. Bridge it in the child only — never written, never persisted.
    """
    env = dict(os.environ)
    if not env.get("TYPESAFE_API_KEY") and env.get("JEV_API_KEY"):
        env["TYPESAFE_API_KEY"] = env["JEV_API_KEY"]
    env.setdefault("JEV_ULTRAFAST_HOME", str(home))
    return env


def keys_present(env=None):
    env = env or os.environ
    typesafe = bool(env.get("TYPESAFE_API_KEY") or env.get("JEV_API_KEY"))
    return {"typesafe": typesafe, "text_model": bool(env.get("TEXT_MODEL_API_KEY"))}


def preflight_state():
    opt_in = os.environ.get(OPT_IN) == "1"
    home, home_reason = driver_home()
    keys = keys_present()
    reason = None
    if not opt_in:
        reason = "opt_in_unset"
    elif home is None:
        reason = home_reason
    elif not keys["typesafe"]:
        reason = "typesafe_key_missing"
    elif not keys["text_model"]:
        reason = "text_model_key_missing"
    return {
        "ok": True,
        "available": reason is None,
        "mode": "jev-ultrafast" if reason is None else "unavailable",
        "opt_in": opt_in,
        "home": str(home) if home else None,
        "keys": keys,
        "allowed_hosts": ["localhost", "127.0.0.1", "::1"] + allowed_hosts(),
        "reason": reason,
        "fallback": "gstack /browse, then source-only",
    }


def build_command(home, args):
    override = os.environ.get(CMD, "").strip()
    prefix = (
        shlex.split(override) if override else ["uv", "run", "--project", str(home)]
    )
    if not override:
        env_file = home / ".env"
        if env_file.is_file():
            prefix += ["--env-file", str(env_file)]
        prefix += ["python"]
    cmd = prefix + [str(RUNNER), "--url", args.url]
    for goal in args.goal:
        cmd += ["--goal", goal]
    cmd += ["--max-steps", str(args.max_steps), "--timeout", str(args.timeout)]
    return cmd


def explore(args):
    state = preflight_state()
    if not state["available"]:
        emit({**state, "ok": False, "source": "none", "steps": []})

    ok, host, reason = host_allowed(args.url)
    if not ok:
        emit(
            {
                "ok": False,
                "source": "none",
                "reason": reason,
                "host": host,
                "hint": f"add the host to {HOSTS} to explore it; production is not a target",
                "steps": [],
            }
        )

    home = Path(state["home"])
    cmd = build_command(home, args)
    try:
        done = subprocess.run(
            cmd,
            env=child_env(home),
            cwd=str(home),
            capture_output=True,
            text=True,
            timeout=args.timeout + 30,
        )
    except FileNotFoundError:
        emit(
            {
                "ok": False,
                "source": "none",
                "reason": "driver_command_not_found",
                "cmd": cmd[0],
                "steps": [],
            }
        )
    except subprocess.TimeoutExpired:
        emit({"ok": False, "source": "none", "reason": "driver_timeout", "steps": []})

    line = next(
        (ln for ln in reversed(done.stdout.splitlines()) if ln.strip().startswith("{")),
        None,
    )
    if line is None:
        emit(
            {
                "ok": False,
                "source": "none",
                "reason": "driver_no_json",
                "exit_code": done.returncode,
                "stderr_tail": done.stderr.strip().splitlines()[-3:],
                "steps": [],
            }
        )
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        emit({"ok": False, "source": "none", "reason": "driver_bad_json", "steps": []})

    payload.setdefault("source", "jev-ultrafast")
    payload["host"] = host
    emit(payload)


def main():
    parser = argparse.ArgumentParser(add_help=True)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("preflight")
    run = sub.add_parser("explore")
    run.add_argument("--url", required=True)
    run.add_argument(
        "--goal",
        action="append",
        required=True,
        help="Repeat for an ordered list of goals.",
    )
    run.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    run.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)

    try:
        args = parser.parse_args()
    except SystemExit:
        emit(
            {
                "ok": False,
                "reason": "bad_arguments",
                "usage": "preflight | explore --url URL --goal GOAL",
            }
        )

    if args.command == "preflight":
        emit(preflight_state())
    if args.command == "explore":
        explore(args)
    emit(
        {
            "ok": False,
            "reason": "no_command",
            "usage": "preflight | explore --url URL --goal GOAL",
        }
    )


if __name__ == "__main__":
    main()
