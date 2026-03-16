"""Wrapper functions for gcloud CLI commands targeting Cloud Run."""

import json
import subprocess
from typing import Any


class GcloudError(Exception):
    """Raised when a gcloud command fails."""

    def __init__(self, command: str, stderr: str, returncode: int):
        self.command = command
        self.stderr = stderr
        self.returncode = returncode
        hint = _remediation_hint(stderr)
        message = f"gcloud command failed (exit {returncode}): {stderr}"
        if hint:
            message += f"\n\n  Fix: {hint}"
        super().__init__(message)


def _remediation_hint(stderr: str) -> str | None:
    """Map common gcloud errors to actionable fix commands."""
    lower = stderr.lower()

    if "not found" in lower and "gcloud" in lower:
        return "Install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install"

    if "not authenticated" in lower or "login" in lower or "reauth" in lower:
        return "Run: gcloud auth login"

    if "no project" in lower or "project_id" in lower or "project is not set" in lower:
        return "Run: gcloud config set project YOUR_PROJECT_ID"

    if "permission" in lower or "forbidden" in lower or "403" in lower:
        return (
            "Check IAM roles. Required: roles/run.viewer, roles/monitoring.viewer\n"
            "  Grant: gcloud projects add-iam-policy-binding PROJECT "
            "--member=user:YOU@DOMAIN --role=roles/run.viewer"
        )

    if "could not find" in lower and "service" in lower:
        return "Verify service name and region: gcloud run services list"

    if "quota" in lower or "rate" in lower:
        return "API rate limit hit. Wait a moment and retry, or check quotas: https://console.cloud.google.com/iam-admin/quotas"

    return None


def run_gcloud(args: list[str], *, timeout: int = 60) -> dict[str, Any] | list[Any]:
    """Run a gcloud command and return parsed JSON output.

    Args:
        args: gcloud command arguments (without 'gcloud' prefix).
        timeout: Command timeout in seconds.

    Returns:
        Parsed JSON output from gcloud.

    Raises:
        GcloudError: If the command fails.
    """
    cmd = ["gcloud", *args, "--format=json"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise GcloudError(
            command=" ".join(cmd),
            stderr=result.stderr.strip(),
            returncode=result.returncode,
        )

    if not result.stdout.strip():
        return []

    return json.loads(result.stdout)


def run_gcloud_raw(args: list[str], *, timeout: int = 60) -> str:
    """Run a gcloud command and return raw text output.

    Args:
        args: gcloud command arguments (without 'gcloud' prefix).
        timeout: Command timeout in seconds.

    Returns:
        Raw stdout string.

    Raises:
        GcloudError: If the command fails.
    """
    cmd = ["gcloud", *args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise GcloudError(
            command=" ".join(cmd),
            stderr=result.stderr.strip(),
            returncode=result.returncode,
        )

    return result.stdout


def list_services(
    *,
    project: str | None = None,
    region: str | None = None,
) -> list[dict[str, Any]]:
    """List all Cloud Run services."""
    args = ["run", "services", "list"]
    if project:
        args.extend(["--project", project])
    if region:
        args.extend(["--region", region])
    result = run_gcloud(args)
    return result if isinstance(result, list) else [result]


def describe_service(
    name: str,
    *,
    region: str,
    project: str | None = None,
) -> dict[str, Any]:
    """Get detailed service configuration."""
    args = ["run", "services", "describe", name, "--region", region]
    if project:
        args.extend(["--project", project])
    result = run_gcloud(args)
    return result if isinstance(result, dict) else {}


def list_revisions(
    service: str,
    *,
    region: str,
    project: str | None = None,
) -> list[dict[str, Any]]:
    """List revisions for a Cloud Run service."""
    args = [
        "run", "revisions", "list",
        "--service", service,
        "--region", region,
    ]
    if project:
        args.extend(["--project", project])
    result = run_gcloud(args)
    return result if isinstance(result, list) else [result]


def get_service_logs(
    service: str,
    *,
    region: str,
    project: str | None = None,
    limit: int = 100,
    severity: str | None = None,
) -> str:
    """Fetch recent logs for a Cloud Run service."""
    log_filter = f'resource.type="cloud_run_revision" resource.labels.service_name="{service}" resource.labels.location="{region}"'
    if severity:
        log_filter += f" severity>={severity}"

    args = ["logging", "read", log_filter, f"--limit={limit}"]
    if project:
        args.extend(["--project", project])
    return run_gcloud(args, timeout=120)


def get_iam_policy(
    service: str,
    *,
    region: str,
    project: str | None = None,
) -> dict[str, Any]:
    """Get IAM policy for a Cloud Run service."""
    args = [
        "run", "services", "get-iam-policy", service,
        "--region", region,
    ]
    if project:
        args.extend(["--project", project])
    result = run_gcloud(args)
    return result if isinstance(result, dict) else {}


def _get_access_token() -> str:
    """Get current gcloud access token."""
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise GcloudError("gcloud auth print-access-token", result.stderr.strip(), result.returncode)
    return result.stdout.strip()


def _get_project_id() -> str:
    """Get current gcloud project ID."""
    result = subprocess.run(
        ["gcloud", "config", "get-value", "project"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def get_metrics(
    service: str,
    *,
    region: str,
    project: str | None = None,
    metric_type: str = "run.googleapis.com/request_count",
    interval_seconds: int = 86400,
    per_series_aligner: str = "ALIGN_RATE",
    alignment_period: str = "3600s",
) -> list[dict[str, Any]]:
    """Query Cloud Monitoring metrics via REST API.

    Uses the monitoring.timeSeries.list API with gcloud auth token.
    """
    import urllib.parse
    from datetime import datetime, timezone, timedelta

    project_id = project or _get_project_id()
    token = _get_access_token()

    now = datetime.now(timezone.utc)
    start = now - timedelta(seconds=interval_seconds)

    filter_str = (
        f'metric.type="{metric_type}" '
        f'resource.type="cloud_run_revision" '
        f'resource.labels.service_name="{service}" '
        f'resource.labels.location="{region}"'
    )

    params = urllib.parse.urlencode({
        "filter": filter_str,
        "interval.startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interval.endTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "aggregation.alignmentPeriod": alignment_period,
        "aggregation.perSeriesAligner": per_series_aligner,
    })

    url = f"https://monitoring.googleapis.com/v3/projects/{project_id}/timeSeries?{params}"

    cmd = [
        "curl", "-s", "-f",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        raise GcloudError("curl monitoring API", result.stderr.strip(), result.returncode)

    if not result.stdout.strip():
        return []

    data = json.loads(result.stdout)
    return data.get("timeSeries", [])
