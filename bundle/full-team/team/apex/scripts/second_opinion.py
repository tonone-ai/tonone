#!/usr/bin/env python3
"""apex-second-opinion helper (stdlib only): probe, prepare, send.

  second_opinion.py probe
  second_opinion.py prepare --cli NAME --input FILE|- [--out-dir DIR]
  second_opinion.py send --cli NAME --payload FILE --consent SHA256

Redaction reuses the secret-* rules in team/warden/hooks/rules.json (the same
source of truth warden-guard uses); nothing is invented here. Over-redacts on
purpose: the rules' placeholder exclusions are ignored. `send` refuses unless
--consent equals the sha256 of the payload file's bytes, and never runs
anything else. No network code lives here; the external CLI does the sending.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RULES_PATH = (
    Path(__file__).resolve().parent.parent.parent / "warden" / "hooks" / "rules.json"
)
MARK = "[REDACTED]"
INSTRUCTION = (
    "You are a second reviewer. Review the following diff or plan for correctness, "
    "security and design bugs. Reply with a JSON array of findings, each "
    '{"severity":"CRITICAL|HIGH|MEDIUM|LOW","title":"","file":"","line":null,'
    '"evidence":"quoted text from the input","impact":"","fix":"","confidence":"high|medium|low"}. '
    "Only report what the input supports. Input follows."
)
# name -> (argv builder, whether payload goes on stdin)
CLIS = {
    "codex": lambda: ["codex", "exec", "-s", "read-only", "-"],
    "gemini": lambda: ["gemini", "-p", INSTRUCTION],
    "llm": lambda: ["llm", INSTRUCTION],
}


def _compile(pattern, macros):
    for _ in range(4):
        nxt = re.sub(
            r"\{\{([A-Z0-9_]+)\}\}",
            lambda m: macros.get(m.group(1), m.group(0)),
            pattern,
        )
        if nxt == pattern:
            break
        pattern = nxt
    flags = 0
    m = re.match(r"\(\?(-?)i\)", pattern)
    if m:
        pattern = pattern[m.end() :]
        flags = 0 if m.group(1) else re.I
    # Python rejects inline (?-i)/(?i) mid-pattern; scope them as groups.
    pattern = re.sub(r"\(\?-i\)(.*)", r"(?-i:\1)", pattern)
    return re.compile(pattern, flags)


def load_secret_rules(path=RULES_PATH):
    raw = json.loads(Path(path).read_text())
    macros = raw.get("macros", {})
    out = []
    for r in raw.get("rules", []):
        if not str(r.get("id", "")).startswith("secret-"):
            continue
        rule = {"id": r["id"], "any": [], "capture": None}
        rule["any"] = [_compile(p, macros) for p in r.get("any", [])]
        cap = r.get("capture")
        if cap:
            rule["capture"] = (
                _compile(cap["pattern"], macros),
                cap.get("group", 1),
                [_compile(p, macros) for p in cap.get("reject", [])],
            )
        out.append(rule)
    return out


def redact(text, rules=None):
    """Return (redacted_text, count)."""
    rules = load_secret_rules() if rules is None else rules
    count = 0
    lines = text.split("\n")
    in_pem = False
    for i, line in enumerate(lines):
        if in_pem:
            lines[i] = MARK
            count += 1
            if re.search(r"-----END [A-Z ]*PRIVATE KEY-----", line):
                in_pem = False
            continue
        if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", line):
            lines[i] = MARK
            count += 1
            in_pem = not re.search(r"-----END [A-Z ]*PRIVATE KEY-----", line)
            continue
        for rule in rules:
            for rx in rule["any"]:
                line, n = rx.subn(MARK, line)
                count += n
            cap = rule["capture"]
            if cap:
                rx, group, reject = cap
                for m in reversed(list(rx.finditer(line))):
                    val = m.group(group)
                    if val == MARK or any(r.search(val) for r in reject):
                        continue
                    line = line[: m.start(group)] + MARK + line[m.end(group) :]
                    count += 1
        lines[i] = line
    return "\n".join(lines), count


def probe(path=None):
    return {n: p for n in CLIS if (p := shutil.which(n, path=path))}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def prepare(raw, cli, out_dir, now=None):
    red, count = redact(raw)
    data = red.encode("utf-8")
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{ts}.payload.txt"
    path.write_bytes(data)
    return {
        "cli": cli,
        "path": str(path),
        "bytes": len(data),
        "sha256": sha256(data),
        "redactions": count,
    }


def send(cli, payload_path, consent, path=None):
    p = Path(payload_path)
    data = p.read_bytes()
    digest = sha256(data)
    if not consent or consent.lower() != digest:
        raise PermissionError(
            f"consent {consent!r} does not match payload sha256 {digest}"
        )
    exe = shutil.which(cli, path=path)
    if cli not in CLIS or not exe:
        raise FileNotFoundError(f"{cli} not on PATH or unsupported")
    argv = CLIS[cli]()
    argv[0] = exe
    proc = subprocess.run(argv, input=data, capture_output=True, timeout=600)
    resp = p.with_name(p.name.replace(".payload.txt", ".response.txt"))
    resp.write_bytes(proc.stdout)
    return {
        "cli": cli,
        "response": str(resp),
        "bytes": len(proc.stdout),
        "exit": proc.returncode,
        "stderr": proc.stderr.decode("utf-8", "replace")[:500],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe")
    pp = sub.add_parser("prepare")
    pp.add_argument("--cli", required=True, choices=sorted(CLIS))
    pp.add_argument("--input", required=True)
    pp.add_argument("--out-dir", default=".tonone/second-opinion")
    sp = sub.add_parser("send")
    sp.add_argument("--cli", required=True, choices=sorted(CLIS))
    sp.add_argument("--payload", required=True)
    sp.add_argument("--consent", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "probe":
        found = probe()
        print(json.dumps({"found": found}))
        return 0 if found else 3
    if a.cmd == "prepare":
        raw = (
            sys.stdin.read()
            if a.input == "-"
            else Path(a.input).read_text(errors="replace")
        )
        print(json.dumps(prepare(raw, a.cli, a.out_dir)))
        return 0
    try:
        print(json.dumps(send(a.cli, a.payload, a.consent)))
        return 0
    except PermissionError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
