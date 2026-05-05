"""Infracost static IaC cost analyzer — wraps infracost CLI, returns Finding list."""

from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import Finding

_MONTHLY_SEVERITY = [
    (1000.0, "CRITICAL"),
    (100.0,  "HIGH"),
    (20.0,   "MEDIUM"),
    (0.01,   "LOW"),
]


def _severity_for_cost(monthly_usd: float) -> str:
    for threshold, sev in _MONTHLY_SEVERITY:
        if monthly_usd >= threshold:
            return sev
    return "INFO"


def check_infracost() -> tuple[bool, str]:
    """Return (available, version_string)."""
    try:
        result = subprocess.run(
            ["infracost", "--version"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, ""


def check_infracost_api_key() -> bool:
    """Return True if an infracost API key is configured."""
    if os.environ.get("INFRACOST_API_KEY"):
        return True
    try:
        result = subprocess.run(
            ["infracost", "configure", "get", "api_key"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.strip() + result.stderr.strip()
        return result.returncode == 0 and "No API key" not in output and len(result.stdout.strip()) > 10
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_infracost(target_path: str) -> list[Finding]:
    """
    Run infracost breakdown on target_path. Returns cost findings.
    Returns [] with message if infracost not installed or no IaC found.
    """
    available, version = check_infracost()
    if not available:
        print(
            "infracost not installed. Install: https://www.infracost.io/docs/",
            file=sys.stderr,
        )
        return []

    # infracost breakdown scans for Terraform/OpenTofu configs
    cmd = [
        "infracost", "breakdown",
        "--path", target_path,
        "--format", "json",
        "--no-color",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        print("infracost timed out after 180s.", file=sys.stderr)
        return []

    if result.returncode != 0:
        stderr_lower = result.stderr.lower()
        if "no terraform" in stderr_lower or "no supported" in stderr_lower or "no resource" in stderr_lower:
            return []
        if "api_key" in stderr_lower or "infracost_api_key" in stderr_lower:
            print(
                "infracost API key not configured. Get a free key at https://dashboard.infracost.io "
                "then run: infracost configure set api_key <key>",
                file=sys.stderr,
            )
            return []
        print(f"infracost error: {result.stderr[:400]}", file=sys.stderr)
        return []

    raw = result.stdout.strip()
    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("infracost returned invalid JSON.", file=sys.stderr)
        return []

    return _parse_infracost_output(data, target_path)


def _parse_infracost_output(data: dict, target_path: str) -> list[Finding]:
    findings: list[Finding] = []

    for project in data.get("projects", []):
        breakdown = project.get("breakdown", {})
        for resource in breakdown.get("resources", []):
            name = resource.get("name", "unknown")
            resource_type = name.split(".")[0] if "." in name else name
            monthly = float(resource.get("monthlyCost") or 0)

            if monthly < 0.01:
                continue

            severity = _severity_for_cost(monthly)

            # surface cost components as context
            components = resource.get("costComponents", [])
            detail_parts = [
                f"{c['name']}: ${float(c.get('monthlyCost') or 0):.2f}/mo"
                for c in components[:3]
                if float(c.get("monthlyCost") or 0) > 0
            ]
            detail = f"${monthly:.2f}/month. " + (", ".join(detail_parts) if detail_parts else "")

            recommendation = _recommendation_for_resource(resource_type, monthly, resource)

            tf_file = resource.get("filePath", target_path)
            tf_line = resource.get("startLine", 0)
            location = f"{tf_file}:{tf_line}" if tf_line else tf_file

            findings.append(Finding(
                id=f"COST-{resource_type.upper()}",
                severity=severity,
                title=f"High cost: {name}",
                detail=detail,
                location=location,
                recommendation=recommendation,
                effort=_effort_for_recommendation(recommendation),
            ))

    return findings


def _recommendation_for_resource(resource_type: str, monthly: float, resource: dict) -> str:
    recs: dict[str, str] = {
        "aws_instance":               "Right-size or switch to Reserved/Savings Plan (up to 72% savings).",
        "aws_db_instance":            "Use Reserved Instance for RDS (up to 69% savings). Consider Aurora Serverless for variable workloads.",
        "aws_rds_cluster":            "Evaluate Aurora Serverless v2 for variable workloads.",
        "aws_elasticsearch_domain":   "Right-size data nodes; consider OpenSearch Serverless.",
        "aws_opensearch_domain":      "Right-size data nodes; consider OpenSearch Serverless.",
        "aws_nat_gateway":            "Consolidate NAT gateways across AZs if multi-AZ is not required.",
        "aws_lb":                     "Remove unused load balancers or consolidate behind a single ALB.",
        "aws_cloudfront_distribution":"Review cache behavior — low hit rate inflates origin transfer costs.",
        "google_compute_instance":    "Right-size or commit to 1-year CUD (up to 57% savings).",
        "google_sql_database_instance":"Use committed use discounts or consider Cloud Spanner for scale.",
        "azurerm_virtual_machine":    "Right-size or switch to Reserved Instance (up to 72% savings).",
    }
    if resource_type in recs:
        return recs[resource_type]
    if monthly >= 100:
        return f"Review {resource_type} sizing and consider Reserved/Committed-use pricing."
    return f"Tag {resource_type} for cost allocation and review utilization."


def _effort_for_recommendation(rec: str) -> str:
    if "Reserved" in rec or "Savings Plan" in rec or "CUD" in rec:
        return "S"
    if "Right-size" in rec or "Serverless" in rec:
        return "M"
    return "S"
