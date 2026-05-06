"""Cloud cost fetcher — queries actual spend from AWS Cost Explorer or GCP billing."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import Finding

_SPEND_SEVERITY = [
    (5000.0, "CRITICAL"),
    (1000.0, "HIGH"),
    (200.0, "MEDIUM"),
    (0.01, "LOW"),
]


def _severity_for_spend(monthly_usd: float) -> str:
    for threshold, sev in _SPEND_SEVERITY:
        if monthly_usd >= threshold:
            return sev
    return "INFO"


def _aws_available() -> bool:
    try:
        result = subprocess.run(
            ["aws", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _gcloud_available() -> bool:
    try:
        result = subprocess.run(
            ["gcloud", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_cloud_cost_fetch(target_path: str) -> list[Finding]:
    """
    Query actual cloud spend. Tries AWS Cost Explorer first, then GCP.
    Returns [] if no cloud CLI is available or authenticated.
    """
    findings: list[Finding] = []

    if _aws_available():
        findings.extend(_fetch_aws_costs())

    if _gcloud_available():
        findings.extend(_fetch_gcp_costs())

    if not findings and not _aws_available() and not _gcloud_available():
        print(
            "No cloud CLI found (aws/gcloud). Install to fetch actual spend.",
            file=sys.stderr,
        )

    return findings


def _fetch_aws_costs() -> list[Finding]:
    today = date.today()
    start = (today.replace(day=1) - timedelta(days=1)).replace(day=1).isoformat()
    end = today.replace(day=1).isoformat()

    cmd = [
        "aws",
        "ce",
        "get-cost-and-usage",
        "--time-period",
        f"Start={start},End={end}",
        "--granularity",
        "MONTHLY",
        "--metrics",
        "UnblendedCost",
        "--group-by",
        "Type=DIMENSION,Key=SERVICE",
        "--output",
        "json",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        print("AWS Cost Explorer timed out.", file=sys.stderr)
        return []

    if result.returncode != 0:
        stderr = result.stderr.lower()
        if (
            "unable to locate credentials" in stderr
            or "authfailure" in stderr
            or "accessdenied" in stderr
        ):
            print(
                "AWS credentials not configured or missing ce:GetCostAndUsage permission.",
                file=sys.stderr,
            )
        else:
            print(f"aws ce error: {result.stderr[:300]}", file=sys.stderr)
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    return _parse_aws_costs(data, start, end)


def _parse_aws_costs(data: dict, start: str, end: str) -> list[Finding]:
    findings: list[Finding] = []
    period_label = f"{start} to {end}"

    for period in data.get("ResultsByTime", []):
        for group in period.get("Groups", []):
            service = group.get("Keys", ["unknown"])[0]
            amount = float(
                group.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", 0)
            )

            if amount < 1.0:
                continue

            severity = _severity_for_spend(amount)
            recommendation = _aws_service_recommendation(service, amount)

            findings.append(
                Finding(
                    id=f"AWS-{service.upper().replace(' ', '-')[:30]}",
                    severity=severity,
                    title=f"AWS spend: {service}",
                    detail=f"${amount:.2f} in {period_label}.",
                    location=f"aws://cost-explorer/{service}",
                    recommendation=recommendation,
                    effort="S",
                )
            )

    return sorted(findings, key=lambda f: -float(f.detail.split("$")[1].split(" ")[0]))


def _aws_service_recommendation(service: str, amount: float) -> str:
    recs: dict[str, str] = {
        "Amazon EC2": "Check for idle/oversized instances. Consider Savings Plans (up to 66% off on-demand).",
        "Amazon RDS": "Use Reserved Instances for steady-state workloads (up to 69% savings).",
        "Amazon S3": "Enable Intelligent-Tiering for infrequently accessed data. Audit lifecycle rules.",
        "AWS Lambda": "Review function memory sizing — Lambda bills on GB-seconds.",
        "Amazon CloudFront": "Review cache hit rate. Low hit rate = high origin transfer cost.",
        "Amazon DynamoDB": "Use on-demand only for spiky workloads; provisioned + auto-scaling is cheaper at steady state.",
        "AWS Data Transfer": "Minimize cross-AZ and cross-region traffic. Use VPC endpoints for S3/DynamoDB.",
        "Amazon Elastic Container": "Use Fargate Spot for fault-tolerant workloads (up to 70% savings).",
        "Amazon Elastic Kubernetes": "Right-size node groups and consider Karpenter for bin packing.",
        "Amazon Relational Database": "Use Reserved Instances for steady-state workloads (up to 69% savings).",
    }
    for key, rec in recs.items():
        if key.lower() in service.lower():
            return rec
    if amount >= 1000:
        return (
            f"Review {service} — top spend driver. Explore Reserved/Committed pricing."
        )
    return f"Review {service} usage. Check for unused resources and tagging."


def _fetch_gcp_costs() -> list[Finding]:
    # List billing accounts and their projects for context
    cmd = ["gcloud", "billing", "accounts", "list", "--format=json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return []

    if result.returncode != 0:
        stderr = result.stderr.lower()
        if (
            "not authenticated" in stderr
            or "credentials" in stderr
            or "permission" in stderr
        ):
            print(
                "GCP credentials not configured or missing billing.accounts.list permission.",
                file=sys.stderr,
            )
        return []

    try:
        accounts = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    if not accounts:
        return []

    findings: list[Finding] = []
    for account in accounts[:3]:
        account_id = account.get("name", "").split("/")[-1]
        display_name = account.get("displayName", account_id)
        # Billing export via BigQuery is the full path; surface account as INFO for now
        findings.append(
            Finding(
                id=f"GCP-BILLING-{account_id[:20]}",
                severity="INFO",
                title=f"GCP billing account: {display_name}",
                detail=f"Billing account {account_id} found. Detailed spend requires BigQuery billing export.",
                location=f"gcp://billing/{account_id}",
                recommendation="Enable BigQuery billing export for per-service cost breakdown. Run `gcloud alpha billing budgets list` to see active budgets.",
                effort="S",
            )
        )

    return findings
