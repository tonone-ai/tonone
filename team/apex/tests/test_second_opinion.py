import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import second_opinion as so  # noqa: E402

SCRIPT = Path(so.__file__)
AKIA = "AKIA" + "ABCDEFGHIJKLMNOP"
GHP = "ghp_" + "aB3dE5gH7jK9mN1pQ3sT5vX7zA9cD1fG3hJ5"
ASSIGNED = 'api_key = "' + "q8Zr2LmX9vTb4KwP7yHs" + '"'


def fake_cli(tmp_path, name, marker):
    d = tmp_path / "bin"
    d.mkdir(exist_ok=True)
    f = d / name
    f.write_text(f"#!/bin/sh\ncat > /dev/null\ntouch {marker}\necho '[]'\n")
    f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return d


def test_redaction_applied():
    text = f"a\nkey {AKIA}\ntok {GHP}\n{ASSIGNED}\n-----BEGIN RSA PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY-----\nok line\n"
    out, n = so.redact(text)
    for secret in (AKIA, GHP, "q8Zr2LmX9vTb4KwP7yHs", "MIIabc"):
        assert secret not in out
    assert "ok line" in out and n >= 4


def test_hash_matches_written_bytes(tmp_path):
    res = so.prepare(f"x {AKIA}\n", "codex", tmp_path)
    data = Path(res["path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == res["sha256"]
    assert len(data) == res["bytes"]
    assert AKIA.encode() not in data


def test_probe_with_fake_path(tmp_path):
    d = fake_cli(tmp_path, "gemini", tmp_path / "m")
    assert so.probe(str(d)) == {"gemini": str(d / "gemini")}
    assert so.probe(str(tmp_path / "empty")) == {}


@pytest.mark.parametrize("consent", ["", "deadbeef", "0" * 64])
def test_send_refuses_without_matching_consent(tmp_path, consent):
    marker = tmp_path / "ran"
    d = fake_cli(tmp_path, "codex", marker)
    res = so.prepare("hello", "codex", tmp_path / "out")
    with pytest.raises(PermissionError):
        so.send("codex", res["path"], consent, path=str(d))
    assert not marker.exists()


def test_cli_send_requires_consent_flag_and_runs_on_match(tmp_path):
    marker = tmp_path / "ran"
    d = fake_cli(tmp_path, "codex", marker)
    env = {**os.environ, "PATH": f"{d}:{os.environ['PATH']}"}
    res = so.prepare("hello", "codex", tmp_path / "out")
    base = [
        sys.executable,
        str(SCRIPT),
        "send",
        "--cli",
        "codex",
        "--payload",
        res["path"],
    ]
    assert (
        subprocess.run(base, env=env, capture_output=True).returncode == 2
    )  # argparse: no --consent
    bad = subprocess.run(base + ["--consent", "nope"], env=env, capture_output=True)
    assert bad.returncode == 2 and not marker.exists()
    ok = subprocess.run(
        base + ["--consent", res["sha256"]], env=env, capture_output=True, text=True
    )
    assert ok.returncode == 0 and marker.exists()
    assert Path(json.loads(ok.stdout)["response"]).read_text().strip() == "[]"


def test_prepare_and_probe_never_invoke_cli(tmp_path):
    marker = tmp_path / "ran"
    d = fake_cli(tmp_path, "codex", marker)
    env = {**os.environ, "PATH": f"{d}:{os.environ['PATH']}"}
    subprocess.run([sys.executable, str(SCRIPT), "probe"], env=env, capture_output=True)
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "prepare",
            "--cli",
            "codex",
            "--input",
            "-",
            "--out-dir",
            str(tmp_path / "o"),
        ],
        env=env,
        input=b"x",
        capture_output=True,
    )
    assert not marker.exists()
