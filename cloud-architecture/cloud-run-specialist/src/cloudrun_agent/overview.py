"""Fleet-level overview across all Cloud Run services."""

import sys
from dataclasses import asdict
from typing import Any

from cloudrun_agent.analyzers.performance import analyze_performance
from cloudrun_agent.analyzers.pricing import estimate_pricing
from cloudrun_agent.analyzers.resources import analyze_resource_waste, _parse_cpu_cores, _parse_memory_mi
from cloudrun_agent.analyzers.security import analyze_security
from cloudrun_agent.analyzers.traffic import analyze_traffic
from cloudrun_agent.tools.gcloud import (
    describe_service,
    get_iam_policy,
    list_services,
)
from cloudrun_agent.tools.metrics import fetch_service_metrics
from cloudrun_agent.tools.parser import parse_service
from cloudrun_agent.models.service import ServiceConfig


def _progress(message: str) -> None:
    """Print a progress message to stderr."""
    print(message, file=sys.stderr, flush=True)


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "warning": 1, "info": 2}.get(severity, 3)


def _worst_severity(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "ok"
    return min(findings, key=lambda f: _severity_rank(f["severity"]))["severity"]


def _count_by_severity(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
    for f in findings:
        sev = f.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def _compute_fleet_infra(configs: list[ServiceConfig]) -> dict[str, Any]:
    """Compute fleet-level infrastructure statistics."""
    regions: dict[str, int] = {}
    total_vcpu = 0.0
    total_memory_mi = 0.0
    ingress_breakdown: dict[str, int] = {}
    max_instance_cap = 0
    services_with_min = 0
    services_with_vpc = 0
    services_with_boost = 0
    services_with_threat_detection = 0
    service_accounts: set[str] = set()
    default_sa_count = 0
    concurrency_1_count = 0

    for cfg in configs:
        # Region distribution
        regions[cfg.region] = regions.get(cfg.region, 0) + 1

        # Resource totals (per max-instance capacity)
        cpu = _parse_cpu_cores(cfg.resources.cpu)
        mem = _parse_memory_mi(cfg.resources.memory)
        total_vcpu += cpu
        total_memory_mi += mem

        # Ingress
        ingress = cfg.network.ingress or "all"
        ingress_breakdown[ingress] = ingress_breakdown.get(ingress, 0) + 1

        # Scaling
        max_instance_cap += cfg.scaling.max_instances
        if cfg.scaling.min_instances > 0:
            services_with_min += 1

        # Networking
        if cfg.network.vpc_connector or cfg.network.vpc_network:
            services_with_vpc += 1

        # Features
        if cfg.startup_cpu_boost:
            services_with_boost += 1
        if cfg.threat_detection:
            services_with_threat_detection += 1

        # Service accounts
        sa = cfg.service_account
        if sa:
            service_accounts.add(sa)
        if not sa or sa.endswith("-compute@developer.gserviceaccount.com"):
            default_sa_count += 1

        if cfg.scaling.concurrency == 1:
            concurrency_1_count += 1

    return {
        "regions": regions,
        "total_vcpu_allocated": round(total_vcpu, 1),
        "total_memory_gib": round(total_memory_mi / 1024, 1),
        "max_instance_capacity": max_instance_cap,
        "services_with_min_instances": services_with_min,
        "ingress_breakdown": ingress_breakdown,
        "services_with_vpc": services_with_vpc,
        "services_with_startup_boost": services_with_boost,
        "services_with_threat_detection": services_with_threat_detection,
        "unique_service_accounts": len(service_accounts),
        "services_using_default_sa": default_sa_count,
        "single_concurrency_services": concurrency_1_count,
    }


def build_overview(
    *,
    project: str | None = None,
    region: str | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Build a fleet-level overview of all Cloud Run services."""
    raw_services = list_services(project=project, region=region)

    total = len(raw_services)
    if total == 0:
        _progress("No Cloud Run services found.")
        return {
            "fleet": {
                "total_services": 0,
                "total_monthly_cost": 0,
                "total_daily_requests": 0,
                "findings_summary": {"critical": 0, "warning": 0, "info": 0},
                "infrastructure": {},
            },
            "services": [],
            "findings_by_group": {},
            "top_findings": [],
        }

    _progress(f"Found {total} Cloud Run service(s). Analyzing...\n")

    configs: list[ServiceConfig] = []
    services_summary: list[dict[str, Any]] = []
    all_findings: list[dict[str, Any]] = []
    total_monthly_cost = 0.0
    total_daily_requests = 0.0

    for idx, raw_svc in enumerate(raw_services, 1):
        metadata = raw_svc.get("metadata", {})
        name = metadata.get("name", "")
        svc_region = metadata.get("labels", {}).get(
            "cloud.googleapis.com/location", ""
        )

        _progress(f"  [{idx}/{total}] {name} ({svc_region})")

        try:
            raw = describe_service(name, region=svc_region, project=project)
            config = parse_service(raw)
            configs.append(config)
        except Exception as e:
            services_summary.append({
                "name": name, "region": svc_region,
                "status": "error", "error": str(e),
            })
            continue

        # Fetch IAM
        iam_policy = None
        try:
            iam_policy = get_iam_policy(name, region=svc_region, project=project)
        except Exception:
            pass

        # Fetch metrics
        metrics = None
        try:
            metrics = fetch_service_metrics(
                name, region=svc_region, project=project,
            )
        except Exception:
            pass

        # Run analyzers
        resource_findings = [asdict(f) for f in analyze_resource_waste(config, metrics)]
        perf_findings = [asdict(f) for f in analyze_performance(config, metrics)]
        security_findings = [asdict(f) for f in analyze_security(config, iam_policy)]
        traffic_findings = [asdict(f) for f in analyze_traffic(config, metrics)]
        pricing = estimate_pricing(config, metrics)

        # Tag each finding with its dimension group
        for f in resource_findings:
            f["group"] = "resources"
        for f in perf_findings:
            f["group"] = "performance"
        for f in security_findings:
            f["group"] = "security"
        for f in traffic_findings:
            f["group"] = "traffic"

        all_svc_findings = resource_findings + perf_findings + security_findings + traffic_findings
        for f in all_svc_findings:
            f["service"] = name

        all_findings.extend(all_svc_findings)
        total_monthly_cost += pricing.monthly_estimate

        # Metrics summaries
        daily_requests = 0.0
        if metrics and metrics.request_count:
            daily_requests = sum(p.value for p in metrics.request_count)
        total_daily_requests += daily_requests

        avg_cpu = None
        avg_mem = None
        if metrics and metrics.cpu_utilization:
            avg_cpu = sum(p.value for p in metrics.cpu_utilization) / len(metrics.cpu_utilization)
        if metrics and metrics.memory_utilization:
            avg_mem = sum(p.value for p in metrics.memory_utilization) / len(metrics.memory_utilization)

        p50 = None
        p99 = None
        if metrics and metrics.request_latency_p50:
            p50 = sum(p.value for p in metrics.request_latency_p50) / len(metrics.request_latency_p50)
        if metrics and metrics.request_latency_p99:
            p99 = sum(p.value for p in metrics.request_latency_p99) / len(metrics.request_latency_p99)

        # Error rate
        error_rate = None
        if metrics and metrics.error_count and metrics.request_count:
            total_err = sum(p.value for p in metrics.error_count)
            total_req = sum(p.value for p in metrics.request_count)
            if total_req > 0:
                error_rate = round(total_err / total_req, 4)

        # Time-series
        time_series: dict[str, list[dict[str, Any]]] = {}
        if metrics:
            for key, points in [
                ("request_count", metrics.request_count),
                ("cpu_utilization", metrics.cpu_utilization),
                ("memory_utilization", metrics.memory_utilization),
                ("latency_p50", metrics.request_latency_p50),
                ("latency_p99", metrics.request_latency_p99),
                ("instance_count", metrics.instance_count),
            ]:
                if points:
                    time_series[key] = [
                        {"t": p.timestamp, "v": round(p.value, 4)}
                        for p in points
                    ]

        services_summary.append({
            "name": name,
            "region": svc_region,
            "cpu": config.resources.cpu,
            "memory": config.resources.memory,
            "min_instances": config.scaling.min_instances,
            "max_instances": config.scaling.max_instances,
            "concurrency": config.scaling.concurrency,
            "ingress": config.network.ingress,
            "egress": config.network.egress,
            "vpc_connected": bool(config.network.vpc_connector or config.network.vpc_network),
            "startup_boost": config.startup_cpu_boost,
            "service_account": config.service_account,
            "generation": config.generation,
            "daily_requests": round(daily_requests),
            "avg_cpu_util": round(avg_cpu, 3) if avg_cpu is not None else None,
            "avg_mem_util": round(avg_mem, 3) if avg_mem is not None else None,
            "latency_p50_s": round(p50, 3) if p50 is not None else None,
            "latency_p99_s": round(p99, 3) if p99 is not None else None,
            "error_rate": error_rate,
            "monthly_cost": pricing.monthly_estimate,
            "findings_count": _count_by_severity(all_svc_findings),
            "worst_severity": _worst_severity(all_svc_findings),
            "time_series": time_series,
        })

    # Sort findings by severity
    all_findings.sort(key=lambda f: _severity_rank(f["severity"]))
    grouped_findings = _group_findings(all_findings)

    # Organize by dimension group
    findings_by_group: dict[str, list[dict[str, Any]]] = {}
    for f in grouped_findings:
        group = f.get("group", "other")
        if group not in findings_by_group:
            findings_by_group[group] = []
        findings_by_group[group].append(f)

    # Fleet infrastructure stats
    fleet_infra = _compute_fleet_infra(configs)

    return {
        "fleet": {
            "total_services": len(services_summary),
            "total_monthly_cost": round(total_monthly_cost, 2),
            "total_daily_requests": round(total_daily_requests),
            "findings_summary": _count_by_severity(all_findings),
            "infrastructure": fleet_infra,
        },
        "services": services_summary,
        "findings_by_group": findings_by_group,
        "top_findings": grouped_findings[:15],
    }


def _group_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group similar findings across services."""
    groups: dict[str, dict[str, Any]] = {}

    for f in findings:
        key = f["category"]
        if key not in groups:
            groups[key] = {
                "severity": f["severity"],
                "category": f["category"],
                "message": f["message"],
                "recommendation": f["recommendation"],
                "affected_services": [],
            }
        groups[key]["affected_services"].append(f.get("service", ""))
        if _severity_rank(f["severity"]) < _severity_rank(groups[key]["severity"]):
            groups[key]["severity"] = f["severity"]
            groups[key]["message"] = f["message"]
        if "group" not in groups[key]:
            groups[key]["group"] = f.get("group", "other")

    result = list(groups.values())
    result.sort(key=lambda g: (_severity_rank(g["severity"]), -len(g["affected_services"])))
    return result
