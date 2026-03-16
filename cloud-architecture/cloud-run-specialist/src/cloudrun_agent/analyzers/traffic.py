"""Traffic and latency analyzer."""

from dataclasses import dataclass

from cloudrun_agent.models.service import ServiceConfig, ServiceMetrics


@dataclass(frozen=True)
class TrafficFinding:
    severity: str
    category: str
    message: str
    recommendation: str


def analyze_traffic(
    config: ServiceConfig,
    metrics: ServiceMetrics | None = None,
) -> tuple[TrafficFinding, ...]:
    """Analyze traffic patterns and latency characteristics."""
    findings: list[TrafficFinding] = []

    # Traffic split across revisions
    active_revisions = [r for r in config.revisions if r.traffic_percent > 0]
    if len(active_revisions) > 1:
        split_desc = ", ".join(
            f"{r.name}: {r.traffic_percent}%" for r in active_revisions
        )
        findings.append(TrafficFinding(
            severity="info",
            category="traffic_split",
            message=f"Traffic split across {len(active_revisions)} revisions: {split_desc}.",
            recommendation="Verify this is intentional (canary/rollout). Consolidate if the rollout is complete.",
        ))

    if not metrics:
        findings.append(TrafficFinding(
            severity="info",
            category="no_metrics",
            message="No metrics available — traffic analysis is limited to configuration.",
            recommendation="Enable Cloud Monitoring API and ensure metrics are being collected.",
        ))
        return tuple(findings)

    # Request volume analysis
    if metrics.request_count:
        total_requests = sum(p.value for p in metrics.request_count)
        if total_requests == 0:
            findings.append(TrafficFinding(
                severity="warning",
                category="no_traffic",
                message="Service received zero requests in the observation period.",
                recommendation="Verify the service is needed. Unused services still incur min-instance costs.",
            ))
        elif total_requests < 100:
            findings.append(TrafficFinding(
                severity="info",
                category="low_traffic",
                message=f"Very low traffic: {total_requests:.0f} requests in the observation period.",
                recommendation="Consider if Cloud Functions would be more cost-effective for low-traffic services.",
            ))

    # Instance scaling efficiency
    if metrics.instance_count:
        instance_values = [p.value for p in metrics.instance_count]
        max_instances = max(instance_values)
        min_instances = min(instance_values)
        avg_instances = sum(instance_values) / len(instance_values)

        if max_instances > 0 and (max_instances / max(avg_instances, 0.01)) > 5:
            findings.append(TrafficFinding(
                severity="warning",
                category="traffic_spikes",
                message=f"Instance count spikes from avg {avg_instances:.1f} to {max_instances:.0f}.",
                recommendation="Investigate traffic spikes. Consider min-instances to absorb bursts without cold starts.",
            ))

        if min_instances == 0 and max_instances > 0:
            findings.append(TrafficFinding(
                severity="info",
                category="scale_to_zero",
                message="Service scales to zero between requests.",
                recommendation="Expected for low-traffic services. Set min-instances=1 if cold starts are problematic.",
            ))

    # Latency analysis
    if metrics.request_latency_p50 and metrics.request_latency_p99:
        p50_values = [p.value for p in metrics.request_latency_p50]
        p99_values = [p.value for p in metrics.request_latency_p99]
        avg_p50 = sum(p50_values) / len(p50_values) if p50_values else 0
        avg_p99 = sum(p99_values) / len(p99_values) if p99_values else 0

        if avg_p99 > 0 and (avg_p99 / max(avg_p50, 0.001)) > 10:
            findings.append(TrafficFinding(
                severity="warning",
                category="latency_tail",
                message=f"Large latency spread: P50={avg_p50:.3f}s, P99={avg_p99:.3f}s ({avg_p99/max(avg_p50,0.001):.0f}x).",
                recommendation="Long tail suggests cold starts or occasional slow operations. Check for outlier causes.",
            ))

    # Billable time efficiency
    if metrics.billable_instance_time and metrics.request_count:
        total_billable = sum(p.value for p in metrics.billable_instance_time)
        total_requests = sum(p.value for p in metrics.request_count)
        if total_requests > 0:
            billable_per_request = total_billable / total_requests
            if billable_per_request > 5:
                findings.append(TrafficFinding(
                    severity="warning",
                    category="high_billable_time",
                    message=f"Billable instance-time per request: {billable_per_request:.1f}s.",
                    recommendation="High per-request cost. Check for long-running background work or low concurrency.",
                ))

    return tuple(findings)
