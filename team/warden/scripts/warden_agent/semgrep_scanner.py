"""Semgrep SAST scanner — wraps semgrep CLI, returns Finding list."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

# reach team/shared from team/warden/scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import Finding


def check_semgrep() -> tuple[bool, str]:
    """Return (available, version_string)."""
    try:
        result = subprocess.run(
            ["semgrep", "--version"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, ""


def run_semgrep(target_path: str, config: str = "auto") -> list[Finding]:
    """
    Run semgrep on target_path. Returns findings.
    Prints install instruction and returns [] if semgrep not installed.
    """
    available, version = check_semgrep()
    if not available:
        print(
            "Semgrep not installed. Install with:\n"
            "  pip install semgrep\n"
            "  or: brew install semgrep",
            file=sys.stderr,
        )
        return []

    cmd = [
        "semgrep",
        "--config", config,
        "--json",
        "--quiet",
        "--no-git-ignore",
        "--include", "*.py",
        "--include", "*.js",
        "--include", "*.ts",
        "--include", "*.go",
        "--include", "*.rb",
        target_path,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        print("Semgrep timed out after 120s. Try targeting a subdirectory.", file=sys.stderr)
        return []

    if result.returncode not in (0, 1):  # 1 = findings found, still ok
        print(f"Semgrep error: {result.stderr[:500]}", file=sys.stderr)
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Semgrep returned invalid JSON.", file=sys.stderr)
        return []

    findings = []
    for r in data.get("results", []):
        sev_map = {
            "ERROR": "HIGH",
            "WARNING": "MEDIUM",
            "INFO": "LOW",
        }
        raw_sev = r.get("extra", {}).get("severity", "INFO").upper()
        severity = sev_map.get(raw_sev, "INFO")

        path = r.get("path", "unknown")
        start_line = r.get("start", {}).get("line", 0)
        rule_id = r.get("check_id", "")
        message = r.get("extra", {}).get("message", "No description")
        fix = r.get("extra", {}).get("fix", "")

        findings.append(Finding(
            id=rule_id,
            severity=severity,
            title=rule_id.split(".")[-1].replace("-", " ").title(),
            detail=message,
            location=f"{path}:{start_line}",
            recommendation=fix if fix else "Review and remediate per rule documentation.",
            effort="S",
        ))

    return findings
