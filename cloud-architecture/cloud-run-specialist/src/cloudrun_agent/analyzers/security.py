"""Security posture analyzer for Cloud Run services."""

from dataclasses import dataclass
from typing import Any

from cloudrun_agent.models.service import ServiceConfig


@dataclass(frozen=True)
class SecurityFinding:
    severity: str  # critical, warning, info
    category: str
    message: str
    recommendation: str


def analyze_security(
    config: ServiceConfig,
    iam_policy: dict[str, Any] | None = None,
) -> tuple[SecurityFinding, ...]:
    """Analyze security posture of a Cloud Run service."""
    findings: list[SecurityFinding] = []

    # Ingress: publicly accessible
    if config.ingress in ("all", ""):
        findings.append(SecurityFinding(
            severity="warning",
            category="public_ingress",
            message="Service accepts traffic from all sources (ingress=all).",
            recommendation="Set ingress to 'internal' or 'internal-and-cloud-load-balancing' if not public-facing.",
        ))

    # Default compute service account
    sa = config.service_account
    if not sa or sa.endswith("-compute@developer.gserviceaccount.com"):
        findings.append(SecurityFinding(
            severity="critical",
            category="default_service_account",
            message="Service uses the default Compute Engine service account.",
            recommendation="Create a dedicated service account with least-privilege permissions.",
        ))

    # No VPC connector
    if not config.vpc_connector:
        findings.append(SecurityFinding(
            severity="info",
            category="no_vpc_connector",
            message="No VPC connector configured — cannot reach private resources.",
            recommendation="Add a VPC connector if this service needs to access VPC-internal resources (DB, Redis, etc).",
        ))

    # IAM: allUsers or allAuthenticatedUsers
    if iam_policy:
        bindings = iam_policy.get("bindings", [])
        for binding in bindings:
            members = binding.get("members", [])
            role = binding.get("role", "")
            if "allUsers" in members:
                findings.append(SecurityFinding(
                    severity="critical",
                    category="public_iam",
                    message=f"IAM grants '{role}' to allUsers — anyone on the internet can invoke.",
                    recommendation="Remove allUsers binding. Use Cloud Load Balancing + IAP for public access.",
                ))
            if "allAuthenticatedUsers" in members:
                findings.append(SecurityFinding(
                    severity="warning",
                    category="broad_iam",
                    message=f"IAM grants '{role}' to allAuthenticatedUsers — any Google account can invoke.",
                    recommendation="Restrict to specific service accounts or user groups.",
                ))

    # Sensitive env vars (check names only, never log values)
    sensitive_patterns = ("KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "PRIVATE")
    plaintext_secrets = [
        name for name, value in config.env_vars.items()
        if any(p in name.upper() for p in sensitive_patterns)
        and value != "<from-secret>"
    ]
    if plaintext_secrets:
        var_names = ", ".join(plaintext_secrets[:5])
        findings.append(SecurityFinding(
            severity="critical",
            category="plaintext_secrets",
            message=f"Potentially sensitive env vars set as plaintext: {var_names}.",
            recommendation="Use Secret Manager references instead of plaintext values.",
        ))

    return tuple(findings)
