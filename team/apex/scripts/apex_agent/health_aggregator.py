"""Runs Warden/Forge/Cortex/Spine depth scans in parallel and merges findings."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import NamedTuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import AgentReport, Finding, ReportMetadata


class SubScanResult(NamedTuple):
    agent: str
    findings: list[Finding]
    error: str | None


def _run_scan(agent: str, script_path: str, target: str, extra_args: list[str]) -> SubScanResult:
    """Run one depth scan as a subprocess, capture its JSON output."""
    if not os.path.exists(script_path):
        return SubScanResult(
            agent=agent,
            findings=[],
            error=f"script not found: {script_path}",
        )

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_path = tmp.name

    try:
        cmd = [sys.executable, script_path, target, "--out", out_path] + extra_args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode not in (0, 2):
            # exit 2 = findings found (expected); other codes = real error
            return SubScanResult(
                agent=agent,
                findings=[],
                error=f"exit {result.returncode}: {result.stderr[:400]}",
            )

        if not os.path.exists(out_path):
            return SubScanResult(
                agent=agent,
                findings=[],
                error="subprocess produced no output file",
            )

        with open(out_path) as fh:
            data = json.load(fh)

        findings = [Finding(**f) for f in data.get("findings", [])]
        return SubScanResult(agent=agent, findings=findings, error=None)

    except subprocess.TimeoutExpired:
        return SubScanResult(agent=agent, findings=[], error="timeout after 120s")
    except Exception as exc:  # noqa: BLE001
        return SubScanResult(agent=agent, findings=[], error=str(exc))
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


def _script_path(agent: str, script_name: str) -> str:
    root = os.path.join(os.path.dirname(__file__), "../../../..")
    return os.path.abspath(
        os.path.join(root, "team", agent, "scripts", f"{agent}_agent", script_name)
    )


def aggregate_health(target: str) -> tuple[list[Finding], list[str]]:
    """
    Run all four depth scans in parallel.

    Returns (findings, errors) where errors is a list of agent-level error strings.
    """
    scans = [
        ("warden", _script_path("warden", "scan.py"), ["--skip-semgrep"]),
        ("forge",  _script_path("forge",  "cost_scan.py"), []),
        ("cortex", _script_path("cortex", "eval_scan.py"), []),
        ("spine",  _script_path("spine",  "perf_scan.py"), ["--skip-endpoints"]),
    ]

    results: list[SubScanResult] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_run_scan, agent, script, target, extra): agent
            for agent, script, extra in scans
        }
        for fut in as_completed(futures):
            results.append(fut.result())

    all_findings: list[Finding] = []
    errors: list[str] = []
    for res in results:
        if res.error:
            print(f"  [apex] {res.agent}: {res.error}", file=sys.stderr)
            errors.append(f"{res.agent}: {res.error}")
        else:
            print(f"  [apex] {res.agent}: {len(res.findings)} finding(s)")
        all_findings.extend(res.findings)

    return all_findings, errors
