"""Cloud Run pricing analysis."""

from dataclasses import dataclass

from cloudrun_agent.models.service import ServiceConfig, ServiceMetrics

# Cloud Run pricing (Tier 1 regions, as of 2025)
# See: https://cloud.google.com/run/pricing
VCPU_PER_SEC = 0.00002400
MEMORY_GIB_PER_SEC = 0.00000250
REQUEST_PER_MILLION = 0.40
MIN_INSTANCE_VCPU_PER_SEC = 0.00000600
MIN_INSTANCE_MEM_GIB_PER_SEC = 0.00000065


@dataclass(frozen=True)
class PricingEstimate:
    daily_cpu_cost: float
    daily_memory_cost: float
    daily_request_cost: float
    daily_min_instance_cost: float
    daily_total: float
    monthly_estimate: float
    findings: tuple[str, ...]


def _parse_cpu_cores(cpu_str: str) -> float:
    if not cpu_str:
        return 1.0
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1]) / 1000
    return float(cpu_str)


def _parse_memory_gib(mem_str: str) -> float:
    if not mem_str:
        return 0.5
    if mem_str.endswith("Gi"):
        return float(mem_str[:-2])
    if mem_str.endswith("Mi"):
        return float(mem_str[:-2]) / 1024
    return float(mem_str)


def estimate_pricing(
    config: ServiceConfig,
    metrics: ServiceMetrics | None = None,
    *,
    avg_request_duration_sec: float = 0.3,
    daily_requests: int | None = None,
) -> PricingEstimate:
    """Estimate daily/monthly cost for a Cloud Run service."""
    cpu_cores = _parse_cpu_cores(config.resources.cpu)
    memory_gib = _parse_memory_gib(config.resources.memory)
    findings: list[str] = []

    # Estimate daily requests from metrics or default
    if daily_requests is None and metrics and metrics.request_count:
        daily_requests = int(sum(p.value for p in metrics.request_count))
    if daily_requests is None:
        daily_requests = 10_000
        findings.append(
            "Using estimated 10k daily requests - provide metrics for accuracy."
        )

    # Active CPU/memory cost (request-processing time)
    active_seconds = daily_requests * avg_request_duration_sec
    daily_cpu_cost = active_seconds * cpu_cores * VCPU_PER_SEC
    daily_memory_cost = active_seconds * memory_gib * MEMORY_GIB_PER_SEC

    # Request cost
    daily_request_cost = (daily_requests / 1_000_000) * REQUEST_PER_MILLION

    # Min instance idle cost (24h)
    idle_seconds_per_day = 86400
    min_inst = config.scaling.min_instances
    daily_min_instance_cost = 0.0
    if min_inst > 0:
        daily_min_instance_cost = (
            min_inst
            * idle_seconds_per_day
            * (
                cpu_cores * MIN_INSTANCE_VCPU_PER_SEC
                + memory_gib * MIN_INSTANCE_MEM_GIB_PER_SEC
            )
        )
        findings.append(
            f"Min instances ({min_inst}) idle cost: ${daily_min_instance_cost:.2f}/day"
        )

    daily_total = (
        daily_cpu_cost
        + daily_memory_cost
        + daily_request_cost
        + daily_min_instance_cost
    )
    monthly_estimate = daily_total * 30

    # Cost optimization findings
    if daily_min_instance_cost > daily_cpu_cost + daily_memory_cost:
        findings.append(
            "Idle min-instance cost exceeds active processing cost - consider reducing min instances."
        )

    if cpu_cores >= 2 and daily_requests < 50_000:
        findings.append(
            f"{cpu_cores} vCPUs with only ~{daily_requests:,} daily requests - likely over-provisioned."
        )

    if monthly_estimate > 100 and config.scaling.concurrency == 1:
        findings.append(
            "Concurrency=1 multiplies instance count - increasing concurrency could cut cost significantly."
        )

    return PricingEstimate(
        daily_cpu_cost=round(daily_cpu_cost, 4),
        daily_memory_cost=round(daily_memory_cost, 4),
        daily_request_cost=round(daily_request_cost, 4),
        daily_min_instance_cost=round(daily_min_instance_cost, 4),
        daily_total=round(daily_total, 4),
        monthly_estimate=round(monthly_estimate, 2),
        findings=tuple(findings),
    )
