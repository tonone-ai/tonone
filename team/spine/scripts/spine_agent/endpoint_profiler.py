"""HTTP endpoint response time profiler — uses httpx to measure p50/p95/p99."""

from __future__ import annotations

import os
import sys
import statistics
import time
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import Finding

# Thresholds in seconds
THRESHOLD_MEDIUM = 0.200   # >200ms p50
THRESHOLD_HIGH = 0.500     # >500ms p50
THRESHOLD_CRITICAL = 1.000  # >1000ms p50

DEFAULT_TIMEOUT = 5.0      # seconds per request
WARMUP_REQUESTS = 3
MEASURED_REQUESTS = 5


def _percentile(data: list[float], pct: float) -> float:
    """Return the pct-th percentile of sorted data."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (pct / 100) * (len(sorted_data) - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[lo]
    frac = idx - lo
    return sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo])


def _severity_for_p50(p50_s: float) -> Optional[str]:
    """Return severity string based on p50 latency, or None if below threshold."""
    if p50_s >= THRESHOLD_CRITICAL:
        return "CRITICAL"
    if p50_s >= THRESHOLD_HIGH:
        return "HIGH"
    if p50_s >= THRESHOLD_MEDIUM:
        return "MEDIUM"
    return None


def profile_endpoints(
    base_url: str,
    paths: list[str],
    timeout: float = DEFAULT_TIMEOUT,
    warmup: int = WARMUP_REQUESTS,
    measured: int = MEASURED_REQUESTS,
) -> list[Finding]:
    """
    Time each endpoint in paths against base_url.

    Returns a Finding for each endpoint that exceeds latency thresholds.
    Returns [] with a message on stderr if httpx is not installed or
    the server is unreachable.
    """
    try:
        import httpx  # noqa: F401 — checked for availability
    except ImportError:
        print(
            "httpx not installed. Install with:\n"
            "  pip install httpx",
            file=sys.stderr,
        )
        return []

    import httpx as _httpx

    findings: list[Finding] = []

    for path in paths:
        url = base_url.rstrip("/") + "/" + path.lstrip("/")
        timings: list[float] = []

        # Warmup
        for _ in range(warmup):
            try:
                with _httpx.Client(timeout=timeout) as client:
                    client.get(url)
            except _httpx.ConnectError:
                print(
                    f"Connection refused for {url}. Is the server running?",
                    file=sys.stderr,
                )
                return []
            except _httpx.TimeoutException:
                # Warmup timeout — treat as very slow (use threshold_critical)
                timings.append(timeout)
            except _httpx.RequestError:
                pass

        # Measured
        for _ in range(measured):
            t0 = time.perf_counter()
            try:
                with _httpx.Client(timeout=timeout) as client:
                    client.get(url)
                elapsed = time.perf_counter() - t0
            except _httpx.ConnectError:
                print(
                    f"Connection refused for {url}. Is the server running?",
                    file=sys.stderr,
                )
                return []
            except _httpx.TimeoutException:
                elapsed = timeout  # treat timeout as a full timeout value
            except _httpx.RequestError:
                elapsed = timeout
            timings.append(elapsed)

        if not timings:
            continue

        p50 = _percentile(timings, 50)
        p95 = _percentile(timings, 95)
        p99 = _percentile(timings, 99)

        severity = _severity_for_p50(p50)
        if severity is None:
            continue

        findings.append(Finding(
            id="SPINE-PERF-LATENCY",
            severity=severity,
            title=f"Slow endpoint: {path}",
            detail=(
                f"Endpoint `{url}` has high response times. "
                f"p50={p50 * 1000:.0f}ms  p95={p95 * 1000:.0f}ms  p99={p99 * 1000:.0f}ms "
                f"(measured over {measured} requests, {warmup} warmup)."
            ),
            location=url,
            recommendation=(
                "Profile with cProfile or py-spy. Look for N+1 queries, missing indexes, "
                "synchronous external calls, or missing caching on hot paths."
            ),
            effort="M",
        ))

    return findings
