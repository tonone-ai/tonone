"""
Tests for lib/jev-ultrafast — the opt-in bridge to the jev-ultrafast browser
agent (see docs/jev-ultrafast.md).

Risk map:
- Bridge throws or prompts when unconfigured → HIGH: every caller gains an
  error path that depends on someone's credentials. The whole contract is that
  "unavailable" is a JSON answer.
- Target allowlist leaks → CRITICAL: the driver attaches to the user's real
  Chrome profile, so a permissive host check means an agent loose in their
  signed-in accounts.
- Key bridging breaks → MEDIUM: a user with JEV_API_KEY alone passes preflight
  and fails on the first model call.

Offline by construction: no network, and jev_ultrafast is never imported here.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
LIB = REPO / "lib" / "jev-ultrafast"


def _load(name):
    """Import a module from a hyphenated directory that is not a package."""
    spec = importlib.util.spec_from_file_location(f"jevuf_{name}", LIB / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cli = _load("cli")


def _run(args, env_extra=None):
    """Run the CLI as a subprocess and return its parsed JSON."""
    import os

    env = dict(os.environ)
    for key in (
        "TONONE_JEV_ULTRAFAST",
        "TONONE_JEV_ULTRAFAST_HOME",
        "TYPESAFE_API_KEY",
        "TEXT_MODEL_API_KEY",
    ):
        env.pop(key, None)
    env.update(env_extra or {})
    done = subprocess.run(
        [sys.executable, str(LIB / "cli.py")] + args,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert done.returncode == 0, f"CLI exited {done.returncode}: {done.stderr}"
    return json.loads(done.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# The contract: one JSON object, exit 0, never a prompt
# ---------------------------------------------------------------------------


def test_preflight_without_opt_in_is_an_answer_not_an_error():
    out = _run(["preflight"])
    assert out["ok"] is True
    assert out["available"] is False
    assert out["reason"] == "opt_in_unset"
    assert out["fallback"]


def test_preflight_reports_missing_checkout():
    out = _run(["preflight"], {"TONONE_JEV_ULTRAFAST": "1"})
    assert out["available"] is False
    assert out["reason"] == "home_unset"


def test_preflight_reports_missing_keys(tmp_path):
    checkout = tmp_path / "jev-ultrafast"
    (checkout / "jev_ultrafast").mkdir(parents=True)
    out = _run(
        ["preflight"],
        {"TONONE_JEV_ULTRAFAST": "1", "TONONE_JEV_ULTRAFAST_HOME": str(checkout)},
    )
    assert out["available"] is False
    assert out["reason"] == "typesafe_key_missing"


def test_unknown_command_still_emits_json():
    out = _run([])
    assert out["ok"] is False
    assert out["reason"] == "no_command"


def test_bad_arguments_still_emit_json():
    out = _run(["explore"])  # missing required --url/--goal
    assert out["ok"] is False
    assert out["reason"] == "bad_arguments"


def test_explore_without_opt_in_returns_fallback_instruction():
    out = _run(["explore", "--url", "http://localhost:3000", "--goal", "Sign in"])
    assert out["ok"] is False
    assert out["steps"] == []
    assert out["fallback"]


# ---------------------------------------------------------------------------
# Target allowlist — deny by default
# ---------------------------------------------------------------------------


def test_localhost_variants_are_allowed():
    for url in (
        "http://localhost:3000/login",
        "http://127.0.0.1:8080",
        "https://app.localhost/signup",
        "file:///tmp/prototype.html",
    ):
        ok, _host, reason = cli.host_allowed(url)
        assert ok, f"{url} should be allowed ({reason})"


def test_public_hosts_are_refused_by_default(monkeypatch):
    monkeypatch.delenv(cli.HOSTS, raising=False)
    for url in ("https://app.example.com", "https://example.com/checkout"):
        ok, _host, reason = cli.host_allowed(url)
        assert not ok and reason == "host_not_allowed"


def test_allowlist_matches_exact_host_and_dotted_suffix(monkeypatch):
    monkeypatch.setenv(cli.HOSTS, "staging.example.com, .preview.example.net")
    assert cli.host_allowed("https://staging.example.com/app")[0]
    assert cli.host_allowed("https://pr-42.preview.example.net")[0]
    # A suffix entry must not match the parent domain or a lookalike.
    assert not cli.host_allowed("https://example.com")[0]
    assert not cli.host_allowed("https://notstaging.example.com")[0]


def test_non_http_schemes_are_refused():
    ok, _host, reason = cli.host_allowed("ftp://localhost/x")
    assert not ok and reason == "unsupported_scheme"


# ---------------------------------------------------------------------------
# Environment handling
# ---------------------------------------------------------------------------


def test_jev_api_key_is_bridged_into_the_child_only(monkeypatch, tmp_path):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("JEV_API_KEY", "test-key")
    env = cli.child_env(tmp_path)
    assert env["TYPESAFE_API_KEY"] == "test-key"
    import os

    assert "TYPESAFE_API_KEY" not in os.environ, "must never leak into this process"


def test_command_uses_the_checkout_and_passes_every_goal(tmp_path, monkeypatch):
    monkeypatch.delenv(cli.CMD, raising=False)
    checkout = tmp_path / "jev-ultrafast"
    checkout.mkdir()
    (checkout / ".env").write_text("TYPESAFE_API_KEY=x\n")

    class Args:
        url = "http://localhost:3000"
        goal = ["Sign in", "Reach the dashboard"]
        max_steps = 7
        timeout = 42.0

    cmd = cli.build_command(checkout, Args())
    assert cmd[:4] == ["uv", "run", "--project", str(checkout)]
    assert "--env-file" in cmd and str(checkout / ".env") in cmd
    assert cmd.count("--goal") == 2
    assert "Reach the dashboard" in cmd
    assert cmd[cmd.index("--max-steps") + 1] == "7"


def test_command_override_replaces_the_launcher_prefix(tmp_path, monkeypatch):
    monkeypatch.setenv(cli.CMD, "/usr/bin/python3.12")
    checkout = tmp_path / "checkout"
    checkout.mkdir()

    class Args:
        url = "http://localhost:3000"
        goal = ["Sign in"]
        max_steps = 5
        timeout = 10.0

    cmd = cli.build_command(checkout, Args())
    assert cmd[0] == "/usr/bin/python3.12"
    assert "uv" not in cmd


# ---------------------------------------------------------------------------
# Runner — the only file that imports jev_ultrafast
# ---------------------------------------------------------------------------


def test_runner_reports_a_missing_driver_as_json():
    """jev_ultrafast is not installed in this repo's environment — the runner
    must say so in JSON and exit 0, not raise ImportError."""
    done = subprocess.run(
        [
            sys.executable,
            str(LIB / "runner.py"),
            "--url",
            "http://localhost:3000",
            "--goal",
            "Sign in",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert out["ok"] is False
    assert out["reason"] == "driver_import_failed"
    assert out["steps"] == []


def test_transcript_step_carries_no_page_content():
    runner = _load("runner")
    entry = {
        "step": 1,
        "action": "textbox Email",
        "kind": "fill",
        "operation": "TYPE_TEXT",
        "text": "qa@example.test",
        "url": "http://localhost:3000/signup",
        "page_changed": True,
        "probability": 0.94,
        "confidence": 0.91,
        "elapsed_ms": 1840,
        "usage": {"input_tokens": 900},
        "page_text": "secret customer record",
    }
    step = runner.step_of(entry)
    assert step["action"] == "textbox Email"
    assert "page_text" not in step and "usage" not in step
    assert set(step) == set(runner.FIELDS)
