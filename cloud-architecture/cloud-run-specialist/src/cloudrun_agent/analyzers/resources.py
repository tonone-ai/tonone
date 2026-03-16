"""Hardware usage and waste detection analyzer."""

from dataclasses import dataclass

from cloudrun_agent.models.service import ServiceConfig, ServiceMetrics


@dataclass(frozen=True)
class ResourceFinding:
    severity: str  # critical, warning, info
    category: str
    message: str
    recommendation: str


def _parse_cpu_cores(cpu_str: str) -> float:
    """Convert CPU string to cores (e.g., '1000m' -> 1.0, '2' -> 2.0)."""
    if not cpu_str:
        return 0.0
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1]) / 1000
    return float(cpu_str)


def _parse_memory_mi(mem_str: str) -> float:
    """Convert memory string to MiB (e.g., '512Mi' -> 512, '1Gi' -> 1024)."""
    if not mem_str:
        return 0.0
    if mem_str.endswith("Gi"):
        return float(mem_str[:-2]) * 1024
    if mem_str.endswith("Mi"):
        return float(mem_str[:-2])
    if mem_str.endswith("Ki"):
        return float(mem_str[:-2]) / 1024
    return float(mem_str)


def analyze_resource_waste(
    config: ServiceConfig,
    metrics: ServiceMetrics | None = None,
) -> tuple[ResourceFinding, ...]:
    """Detect over-provisioned or under-utilized resources."""
    findings: list[ResourceFinding] = []
    cpu_cores = _parse_cpu_cores(config.resources.cpu)
    memory_mi = _parse_memory_mi(config.resources.memory)

    # Check for over-provisioned CPU
    if cpu_cores >= 4:
        findings.append(ResourceFinding(
            severity="warning",
            category="cpu_overprovisioned",
            message=f"Service allocated {cpu_cores} vCPUs — most Cloud Run workloads need 1-2.",
            recommendation="Review actual CPU usage in Cloud Monitoring. Consider reducing to 1-2 vCPUs.",
        ))

    # Check for over-provisioned memory
    if memory_mi >= 2048:
        findings.append(ResourceFinding(
            severity="warning",
            category="memory_overprovisioned",
            message=f"Service allocated {memory_mi:.0f}Mi memory.",
            recommendation="Check memory utilization metrics. Right-size to actual peak + 20% headroom.",
        ))

    # Min instances cost
    if config.scaling.min_instances > 0:
        findings.append(ResourceFinding(
            severity="info",
            category="min_instances_cost",
            message=f"Min instances set to {config.scaling.min_instances} — incurs idle cost.",
            recommendation="Set to 0 if cold starts are acceptable, or use CPU-always-allocated pricing.",
        ))

    # CPU idle if min instances with default billing
    if config.scaling.min_instances > 0 and cpu_cores > 1:
        findings.append(ResourceFinding(
            severity="warning",
            category="idle_cpu_cost",
            message=f"{config.scaling.min_instances} min instances × {cpu_cores} vCPUs = always-on cost.",
            recommendation="Consider reducing CPU per instance or min instances count.",
        ))

    # Analyze actual utilization if metrics available
    if metrics and metrics.cpu_utilization:
        avg_cpu = sum(p.value for p in metrics.cpu_utilization) / len(metrics.cpu_utilization)
        if avg_cpu < 0.1:
            findings.append(ResourceFinding(
                severity="critical",
                category="cpu_underutilized",
                message=f"Average CPU utilization is {avg_cpu:.1%} — significant waste.",
                recommendation=f"Reduce CPU allocation from {cpu_cores} to {max(0.5, cpu_cores * avg_cpu * 2)} vCPUs.",
            ))

    if metrics and metrics.memory_utilization:
        avg_mem = sum(p.value for p in metrics.memory_utilization) / len(metrics.memory_utilization)
        if avg_mem < 0.3:
            findings.append(ResourceFinding(
                severity="warning",
                category="memory_underutilized",
                message=f"Average memory utilization is {avg_mem:.1%}.",
                recommendation=f"Consider reducing memory from {memory_mi:.0f}Mi to {max(128, memory_mi * avg_mem * 1.5):.0f}Mi.",
            ))

    return tuple(findings)
