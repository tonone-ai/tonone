"""Fetch and parse Cloud Monitoring metrics into typed models."""

from typing import Any

from cloudrun_agent.models.service import MetricPoint, ServiceMetrics
from cloudrun_agent.tools.gcloud import get_metrics


# Metric type constants
REQUEST_COUNT = "run.googleapis.com/request_count"
CPU_UTILIZATION = "run.googleapis.com/container/cpu/utilizations"
MEMORY_UTILIZATION = "run.googleapis.com/container/memory/utilizations"
REQUEST_LATENCIES = "run.googleapis.com/request_latencies"
INSTANCE_COUNT = "run.googleapis.com/container/instance_count"
BILLABLE_INSTANCE_TIME = "run.googleapis.com/container/billable_instance_time"


def _extract_value(value_obj: dict[str, Any]) -> float:
    """Extract numeric value from a Cloud Monitoring value object."""
    if "doubleValue" in value_obj:
        return float(value_obj["doubleValue"])
    if "int64Value" in value_obj:
        return float(value_obj["int64Value"])
    if "distributionValue" in value_obj:
        return float(value_obj["distributionValue"].get("mean", 0) or 0)
    return 0.0


def _extract_points(time_series: list[dict[str, Any]]) -> tuple[MetricPoint, ...]:
    """Extract metric points from time series data, aggregating across series."""
    points_by_time: dict[str, float] = {}

    for series in time_series:
        for point in series.get("points", []):
            interval = point.get("interval", {})
            timestamp = interval.get("endTime", "")
            value = _extract_value(point.get("value", {}))

            if timestamp in points_by_time:
                points_by_time[timestamp] += value
            else:
                points_by_time[timestamp] = value

    return tuple(
        MetricPoint(timestamp=ts, value=val)
        for ts, val in sorted(points_by_time.items())
    )


def _extract_distribution_percentile(
    time_series: list[dict[str, Any]],
    percentile: float,
    *,
    unit_divisor: float = 1000.0,
) -> tuple[MetricPoint, ...]:
    """Extract percentile from distribution metrics.

    Cloud Run latency distributions use milliseconds with exponential buckets.
    Bucket boundary i = scale * growthFactor^(i-1) for i >= 1, bucket 0 is underflow.

    Args:
        time_series: Raw time series from Cloud Monitoring API.
        percentile: Target percentile (0.0 to 1.0).
        unit_divisor: Divide bucket boundary by this to convert units (1000 = ms→s).
    """
    # Aggregate distributions across series by timestamp
    aggregated: dict[str, dict[str, Any]] = {}

    for series in time_series:
        for point in series.get("points", []):
            interval = point.get("interval", {})
            timestamp = interval.get("endTime", "")
            dist = point.get("value", {}).get("distributionValue", {})

            count = int(dist.get("count", 0) or 0)
            if count == 0:
                continue

            bucket_counts = [int(c) for c in dist.get("bucketCounts", [])]
            if not bucket_counts:
                continue

            if timestamp not in aggregated:
                aggregated[timestamp] = {
                    "bucketCounts": [0] * len(bucket_counts),
                    "bucketOptions": dist.get("bucketOptions", {}),
                    "mean_sum": 0.0,
                    "count": 0,
                }

            entry = aggregated[timestamp]
            # Extend if needed
            while len(entry["bucketCounts"]) < len(bucket_counts):
                entry["bucketCounts"].append(0)
            for i, c in enumerate(bucket_counts):
                entry["bucketCounts"][i] += c
            entry["mean_sum"] += float(dist.get("mean", 0) or 0) * count
            entry["count"] += count

    points: list[MetricPoint] = []
    for timestamp in sorted(aggregated):
        entry = aggregated[timestamp]
        bucket_counts = entry["bucketCounts"]
        total = sum(bucket_counts)
        if total == 0:
            continue

        bounds = entry["bucketOptions"].get("exponentialBuckets", {})
        growth = bounds.get("growthFactor", 1.1)
        scale = bounds.get("scale", 10.0)

        target = total * percentile
        cumulative = 0
        value_ms = 0.0

        for i, count in enumerate(bucket_counts):
            cumulative += count
            if cumulative >= target:
                if i == 0:
                    value_ms = 0.0
                else:
                    # Bucket i lower boundary = scale * growth^(i-1)
                    # Bucket i upper boundary = scale * growth^i
                    lower = scale * (growth ** (i - 1))
                    upper = scale * (growth ** i)
                    # Linear interpolation within bucket
                    bucket_start_count = cumulative - count
                    fraction = (target - bucket_start_count) / max(count, 1)
                    value_ms = lower + fraction * (upper - lower)
                break
        else:
            # Fallback to mean
            value_ms = entry["mean_sum"] / max(entry["count"], 1)

        points.append(MetricPoint(
            timestamp=timestamp,
            value=round(value_ms / unit_divisor, 4),
        ))

    return tuple(points)


def fetch_service_metrics(
    service: str,
    *,
    region: str,
    project: str | None = None,
    interval_seconds: int = 86400,
) -> ServiceMetrics:
    """Fetch all relevant metrics for a Cloud Run service."""
    kwargs = {
        "region": region,
        "project": project,
        "interval_seconds": interval_seconds,
    }

    # Fetch each metric type, tolerating failures
    raw_requests: list[dict[str, Any]] = []
    raw_cpu: list[dict[str, Any]] = []
    raw_memory: list[dict[str, Any]] = []
    raw_latency: list[dict[str, Any]] = []
    raw_instances: list[dict[str, Any]] = []
    raw_billable: list[dict[str, Any]] = []

    try:
        raw_requests = get_metrics(service, metric_type=REQUEST_COUNT, per_series_aligner="ALIGN_SUM", **kwargs)
    except Exception:
        pass

    try:
        raw_cpu = get_metrics(service, metric_type=CPU_UTILIZATION, per_series_aligner="ALIGN_PERCENTILE_99", **kwargs)
    except Exception:
        pass

    try:
        raw_memory = get_metrics(service, metric_type=MEMORY_UTILIZATION, per_series_aligner="ALIGN_PERCENTILE_99", **kwargs)
    except Exception:
        pass

    try:
        raw_latency = get_metrics(service, metric_type=REQUEST_LATENCIES, per_series_aligner="ALIGN_DELTA", **kwargs)
    except Exception:
        pass

    try:
        raw_instances = get_metrics(service, metric_type=INSTANCE_COUNT, per_series_aligner="ALIGN_MEAN", **kwargs)
    except Exception:
        pass

    try:
        raw_billable = get_metrics(service, metric_type=BILLABLE_INSTANCE_TIME, per_series_aligner="ALIGN_RATE", **kwargs)
    except Exception:
        pass

    # Separate request counts into total vs errors (5xx)
    error_series = [s for s in raw_requests if s.get("metric", {}).get("labels", {}).get("response_code_class") == "5xx"]
    all_request_series = raw_requests

    return ServiceMetrics(
        service_name=service,
        region=region,
        cpu_utilization=_extract_points(raw_cpu),
        memory_utilization=_extract_points(raw_memory),
        request_count=_extract_points(all_request_series),
        request_latency_p50=_extract_distribution_percentile(raw_latency, 0.5),
        request_latency_p95=_extract_distribution_percentile(raw_latency, 0.95),
        request_latency_p99=_extract_distribution_percentile(raw_latency, 0.99),
        instance_count=_extract_points(raw_instances),
        billable_instance_time=_extract_points(raw_billable),
        error_count=_extract_points(error_series),
    )
