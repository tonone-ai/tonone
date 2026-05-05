"""pip-audit dependency vulnerability scanner."""

from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import Finding

_SEV_MAP = {
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "MODERATE": "MEDIUM",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW",
}


def run_pip_audit(target_path: str) -> list[Finding]:
    """
    Run pip-audit against requirements files found in target_path.
    Falls back to auditing the current environment if no requirements found.
    Returns Finding list. Returns [] with message if pip-audit not installed.
    """
    try:
        subprocess.run(
            ["pip-audit", "--version"], capture_output=True, timeout=10, check=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(
            "pip-audit not installed. Install with: pip install pip-audit",
            file=sys.stderr,
        )
        return []

    # find requirements files
    req_files = []
    for root, _, files in os.walk(target_path):
        parts = root.split(os.sep)
        if any(p in parts for p in (".venv", "node_modules", ".git")):
            continue
        for f in files:
            if f in (
                "requirements.txt",
                "requirements-dev.txt",
                "requirements-prod.txt",
            ):
                req_files.append(os.path.join(root, f))

    findings = []

    if req_files:
        for req_file in req_files:
            findings.extend(_audit_requirements(req_file))
    else:
        # audit current environment
        findings.extend(_audit_environment())

    return findings


def _audit_requirements(req_file: str) -> list[Finding]:
    cmd = ["pip-audit", "-r", req_file, "-f", "json", "--progress-spinner", "off"]
    return _run_and_parse(cmd, source=req_file)


def _audit_environment() -> list[Finding]:
    cmd = ["pip-audit", "-f", "json", "--progress-spinner", "off"]
    return _run_and_parse(cmd, source="current environment")


def _run_and_parse(cmd: list[str], source: str) -> list[Finding]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"pip-audit timed out on {source}", file=sys.stderr)
        return []

    raw = result.stdout.strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    findings = []
    for dep in data.get("dependencies", []):
        pkg_name = dep.get("name", "unknown")
        pkg_version = dep.get("version", "?")
        for vuln in dep.get("vulns", []):
            vuln_id = vuln.get("id", "")
            description = vuln.get("description", "")
            fix_versions = vuln.get("fix_versions", [])
            # explicit severity field takes precedence; aliases list is CVE IDs, not severities
            if vuln.get("severity"):
                severity = _SEV_MAP.get(str(vuln["severity"]).upper(), "HIGH")
            else:
                severity = "HIGH"

            fix = (
                f"Upgrade {pkg_name} to {fix_versions[0]}"
                if fix_versions
                else f"No fix available yet for {pkg_name} {pkg_version}"
            )

            findings.append(
                Finding(
                    id=vuln_id,
                    severity=severity,
                    title=f"{vuln_id} in {pkg_name} {pkg_version}",
                    detail=description or f"Vulnerability in {pkg_name} {pkg_version}",
                    location=f"{source} → {pkg_name}=={pkg_version}",
                    recommendation=fix,
                    effort="S",
                )
            )

    return findings
