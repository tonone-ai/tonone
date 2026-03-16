"""Main runner — orchestrates analysis across all dimensions."""

import json
from dataclasses import asdict
from typing import Any

from cloudrun_agent.analyzers.performance import analyze_performance
from cloudrun_agent.analyzers.pricing import estimate_pricing
from cloudrun_agent.analyzers.resources import analyze_resource_waste
from cloudrun_agent.analyzers.security import analyze_security
from cloudrun_agent.analyzers.traffic import analyze_traffic
from cloudrun_agent.tools.gcloud import (
    describe_service,
    get_iam_policy,
    list_services,
)
from cloudrun_agent.tools.metrics import fetch_service_metrics
from cloudrun_agent.tools.parser import parse_service


def discover_services(
    *,
    project: str | None = None,
    region: str | None = None,
) -> list[dict[str, str]]:
    """Discover Cloud Run services and return summary list."""
    raw_services = list_services(project=project, region=region)
    results = []
    for svc in raw_services:
        metadata = svc.get("metadata", {})
        status = svc.get("status", {})
        results.append({
            "name": metadata.get("name", ""),
            "region": metadata.get("labels", {}).get(
                "cloud.googleapis.com/location", ""
            ),
            "url": status.get("url", ""),
        })
    return results


def analyze_service(
    name: str,
    *,
    region: str,
    project: str | None = None,
    include_metrics: bool = True,
) -> dict[str, Any]:
    """Run full analysis on a single Cloud Run service."""
    # Fetch service config
    raw = describe_service(name, region=region, project=project)
    config = parse_service(raw)

    # Fetch IAM policy
    iam_policy = None
    try:
        iam_policy = get_iam_policy(name, region=region, project=project)
    except Exception:
        pass

    # Fetch metrics if requested
    metrics = None
    if include_metrics:
        try:
            metrics = fetch_service_metrics(
                name,
                region=region,
                project=project,
            )
        except Exception:
            pass

    # Run all analyzers
    resource_findings = analyze_resource_waste(config, metrics)
    perf_findings = analyze_performance(config, metrics)
    pricing = estimate_pricing(config, metrics)
    security_findings = analyze_security(config, iam_policy)
    traffic_findings = analyze_traffic(config, metrics)

    return {
        "service": {
            "name": config.name,
            "region": config.region,
            "project": config.project,
            "url": config.url,
            "resources": asdict(config.resources),
            "scaling": asdict(config.scaling),
            "ingress": config.ingress,
            "service_account": config.service_account,
            "vpc_connector": config.vpc_connector,
            "revision_count": len(config.revisions),
        },
        "resource_waste": [asdict(f) for f in resource_findings],
        "performance": [asdict(f) for f in perf_findings],
        "pricing": asdict(pricing),
        "security": [asdict(f) for f in security_findings],
        "traffic": [asdict(f) for f in traffic_findings],
    }


def analyze_all_services(
    *,
    project: str | None = None,
    region: str | None = None,
) -> list[dict[str, Any]]:
    """Discover and analyze all Cloud Run services."""
    services = discover_services(project=project, region=region)
    results = []
    for svc in services:
        try:
            result = analyze_service(
                svc["name"],
                region=svc["region"],
                project=project,
            )
            results.append(result)
        except Exception as e:
            results.append({
                "service": {"name": svc["name"], "region": svc["region"]},
                "error": str(e),
            })
    return results


def format_report(analysis: dict[str, Any]) -> str:
    """Format analysis results as readable text."""
    return json.dumps(analysis, indent=2)
