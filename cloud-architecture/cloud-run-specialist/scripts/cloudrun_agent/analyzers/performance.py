"""Performance bottleneck analyzer."""

from dataclasses import dataclass

from cloudrun_agent.models.service import ServiceConfig, ServiceMetrics


@dataclass(frozen=True)
class PerformanceFinding:
    severity: str
    category: str
    message: str
    recommendation: str


def analyze_performance(
    config: ServiceConfig,
    metrics: ServiceMetrics | None = None,
) -> tuple[PerformanceFinding, ...]:
    """Identify performance bottlenecks from config and metrics."""
    findings: list[PerformanceFinding] = []

    # Cold start risk
    if config.scaling.min_instances == 0:
        findings.append(
            PerformanceFinding(
                severity="warning",
                category="cold_start_risk",
                message="Min instances is 0 - service will cold-start after idle periods.",
                recommendation="Set min-instances to 1+ for latency-sensitive services, or use startup CPU boost.",
            )
        )

    # Concurrency too high can cause contention
    if config.scaling.concurrency > 250:
        findings.append(
            PerformanceFinding(
                severity="warning",
                category="high_concurrency",
                message=f"Concurrency set to {config.scaling.concurrency} - may cause resource contention.",
                recommendation="Lower concurrency to 80-100 for CPU-bound workloads, 200-250 for I/O-bound.",
            )
        )

    # Concurrency of 1 wastes resources
    if config.scaling.concurrency == 1:
        findings.append(
            PerformanceFinding(
                severity="info",
                category="single_concurrency",
                message="Concurrency is 1 - each instance handles one request at a time.",
                recommendation="Increase concurrency if your app is thread-safe. This significantly reduces cost.",
            )
        )

    # Low max instances may throttle
    if config.scaling.max_instances < 10:
        findings.append(
            PerformanceFinding(
                severity="warning",
                category="low_max_instances",
                message=f"Max instances capped at {config.scaling.max_instances} - may throttle under load.",
                recommendation="Increase max-instances or verify this limit matches your expected peak traffic.",
            )
        )

    # Latency analysis from metrics
    if metrics and metrics.request_latency_p99:
        p99_values = [p.value for p in metrics.request_latency_p99]
        max_p99 = max(p99_values) if p99_values else 0
        avg_p99 = sum(p99_values) / len(p99_values) if p99_values else 0

        if avg_p99 > 2.0:
            findings.append(
                PerformanceFinding(
                    severity="critical",
                    category="high_latency",
                    message=f"P99 latency averages {avg_p99:.2f}s (peak: {max_p99:.2f}s).",
                    recommendation="Investigate slow dependencies, database queries, or CPU-intensive operations.",
                )
            )
        elif avg_p99 > 0.5:
            findings.append(
                PerformanceFinding(
                    severity="warning",
                    category="elevated_latency",
                    message=f"P99 latency averages {avg_p99:.2f}s.",
                    recommendation="Consider caching, connection pooling, or async processing.",
                )
            )

    # Error rate analysis
    if metrics and metrics.error_count and metrics.request_count:
        total_errors = sum(p.value for p in metrics.error_count)
        total_requests = sum(p.value for p in metrics.request_count)
        if total_requests > 0:
            error_rate = total_errors / total_requests
            if error_rate > 0.05:
                findings.append(
                    PerformanceFinding(
                        severity="critical",
                        category="high_error_rate",
                        message=f"Error rate is {error_rate:.1%} ({total_errors:.0f}/{total_requests:.0f}).",
                        recommendation="Check logs for error patterns. Common causes: OOM kills, timeout, dependency failures.",
                    )
                )
            elif error_rate > 0.01:
                findings.append(
                    PerformanceFinding(
                        severity="warning",
                        category="elevated_error_rate",
                        message=f"Error rate is {error_rate:.1%}.",
                        recommendation="Review error logs - even low error rates affect user experience at scale.",
                    )
                )

    return tuple(findings)
