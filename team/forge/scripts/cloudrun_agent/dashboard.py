"""Generate a self-contained HTML dashboard from overview data."""

import html
import json
from typing import Any

# SVG severity indicators (inline, 14x14)
_SEVERITY_ICONS = {
    "critical": '<svg class="sev-icon sev-crit" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="currentColor"/></svg>',
    "warning": '<svg class="sev-icon sev-warn" viewBox="0 0 16 16"><path d="M8 2L1.5 13h13L8 2z" fill="currentColor"/></svg>',
    "info": '<svg class="sev-icon sev-info" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 7v4M8 5.5v0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    "ok": '<svg class="sev-icon sev-ok" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M5.5 8l2 2 3-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}

# SVG group icons (inline, 18x18)
_GROUP_SVGS = {
    "security": '<svg class="g-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "resources": '<svg class="g-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2M15 20v2M2 15h2M20 15h2M9 2v2M9 20v2M2 9h2M20 9h2"/></svg>',
    "performance": '<svg class="g-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "traffic": '<svg class="g-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    "pricing": '<svg class="g-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
}

_GROUP_META = {
    "security": {
        "icon": _GROUP_SVGS["security"],
        "label": "Security",
        "color": "#ef4444",
        "desc": "Access control, secrets, IAM policies",
    },
    "resources": {
        "icon": _GROUP_SVGS["resources"],
        "label": "Resource Efficiency",
        "color": "#eab308",
        "desc": "CPU, memory allocation and utilization",
    },
    "performance": {
        "icon": _GROUP_SVGS["performance"],
        "label": "Performance",
        "color": "#14b8a6",
        "desc": "Latency, cold starts, error rates",
    },
    "traffic": {
        "icon": _GROUP_SVGS["traffic"],
        "label": "Traffic & Scaling",
        "color": "#3b82f6",
        "desc": "Request patterns, instance scaling",
    },
    "pricing": {
        "icon": _GROUP_SVGS["pricing"],
        "label": "Cost Optimization",
        "color": "#22c55e",
        "desc": "Spend breakdown and savings",
    },
}


def _e(text: Any) -> str:
    return html.escape(str(text))


def _pct(val: float | None) -> str:
    return f"{val:.1%}" if val is not None else "&mdash;"


def _lat(val: float | None) -> str:
    if val is None:
        return "&mdash;"
    return f"{val*1000:.0f}ms" if val < 1 else f"{val:.2f}s"


def _cost(val: float) -> str:
    return "&lt;$0.01" if val < 0.01 else f"${val:.2f}"


def _reqs(val: int) -> str:
    if val >= 1_000_000:
        return f"{val/1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val/1_000:.1f}k"
    return str(val)


def _health_score(svc: dict[str, Any]) -> tuple[int, str]:
    """Compute 0-100 health score and letter grade."""
    fc = svc.get("findings_count", {})
    score = (
        100
        - fc.get("critical", 0) * 20
        - fc.get("warning", 0) * 5
        - fc.get("info", 0) * 1
    )
    score = max(0, min(100, score))
    if score >= 90:
        return score, "A"
    if score >= 75:
        return score, "B"
    if score >= 60:
        return score, "C"
    if score >= 40:
        return score, "D"
    return score, "F"


def _build_infra_cards(fleet: dict[str, Any]) -> str:
    infra = fleet.get("infrastructure", {})
    regions = infra.get("regions", {})
    ingress = infra.get("ingress_breakdown", {})

    region_tags = " ".join(
        f'<span class="tag">{_e(r)} <strong>{c}</strong></span>'
        for r, c in sorted(regions.items())
    )
    ingress_tags = " ".join(
        f'<span class="tag {("tag-warn" if k == "all" else "tag-ok")}">{_e(k)} <strong>{c}</strong></span>'
        for k, c in ingress.items()
    )

    sa_class = " infra-bad" if infra.get("services_using_default_sa", 0) > 0 else ""

    return f"""
    <div class="infra-grid">
        <div class="infra-card fade-in">
            <div class="infra-label">Compute Allocated</div>
            <div class="infra-row"><span class="infra-num">{infra.get('total_vcpu_allocated', 0)}</span> vCPUs</div>
            <div class="infra-row"><span class="infra-num">{infra.get('total_memory_gib', 0)}</span> GiB RAM</div>
        </div>
        <div class="infra-card fade-in">
            <div class="infra-label">Scaling</div>
            <div class="infra-row"><span class="infra-num">{infra.get('max_instance_capacity', 0)}</span> max instance cap</div>
            <div class="infra-row"><span class="infra-num">{infra.get('services_with_min_instances', 0)}</span>/{fleet['total_services']} with min &gt; 0</div>
            <div class="infra-row"><span class="infra-num">{infra.get('single_concurrency_services', 0)}</span> single-concurrency</div>
        </div>
        <div class="infra-card fade-in">
            <div class="infra-label">Regions</div>
            <div class="infra-tags">{region_tags}</div>
        </div>
        <div class="infra-card fade-in">
            <div class="infra-label">Network &amp; Access</div>
            <div class="infra-row">Ingress: {ingress_tags}</div>
            <div class="infra-row"><span class="infra-num">{infra.get('services_with_vpc', 0)}</span>/{fleet['total_services']} VPC connected</div>
        </div>
        <div class="infra-card fade-in">
            <div class="infra-label">Security Posture</div>
            <div class="infra-row"><span class="infra-num">{infra.get('unique_service_accounts', 0)}</span> service accounts</div>
            <div class="infra-row{sa_class}"><span class="infra-num">{infra.get('services_using_default_sa', 0)}</span> using default SA</div>
            <div class="infra-row"><span class="infra-num">{infra.get('services_with_threat_detection', 0)}</span>/{fleet['total_services']} threat detection</div>
        </div>
        <div class="infra-card fade-in">
            <div class="infra-label">Features</div>
            <div class="infra-row"><span class="infra-num">{infra.get('services_with_startup_boost', 0)}</span>/{fleet['total_services']} startup CPU boost</div>
        </div>
    </div>"""


def _build_svc_rows(services: list[dict[str, Any]]) -> str:
    rows = ""
    for svc in services:
        if svc.get("status") == "error":
            rows += f'<tr class="svc-row"><td>{_e(svc["name"])}</td><td colspan="11">Error: {_e(svc.get("error",""))}</td></tr>'
            continue

        score, grade = _health_score(svc)
        grade_class = (
            "grade-a"
            if grade in ("A", "B")
            else ("grade-c" if grade == "C" else "grade-f")
        )

        err_cell = ""
        er = svc.get("error_rate")
        if er is not None and er > 0:
            err_class = "val-bad" if er > 0.05 else ("val-warn" if er > 0.01 else "")
            err_cell = f'<span class="{err_class}">{er:.1%}</span>'
        else:
            err_cell = "&mdash;"

        cpu_class = ""
        cpu_val = svc.get("avg_cpu_util")
        if cpu_val is not None and cpu_val < 0.1:
            cpu_class = "val-warn"

        sa = svc.get("service_account", "")
        sa_short = sa.split("@")[0] if sa else "&mdash;"
        if sa.endswith("-compute@developer.gserviceaccount.com"):
            sa_short = '<span class="val-bad">default</span>'

        rows += f"""<tr class="svc-row" data-service="{_e(svc['name'])}">
            <td class="svc-name">{_e(svc['name'])}</td>
            <td>{_e(svc['region'])}</td>
            <td class="mono">{_e(svc['cpu'])}</td>
            <td class="mono">{_e(svc['memory'])}</td>
            <td class="mono">{svc['min_instances']}/{svc['max_instances']}</td>
            <td class="num">{_reqs(svc['daily_requests'])}</td>
            <td class="num {cpu_class}">{_pct(cpu_val)}</td>
            <td class="num">{_lat(svc.get('latency_p99_s'))}</td>
            <td class="num">{err_cell}</td>
            <td class="num">{_cost(svc['monthly_cost'])}</td>
            <td class="svc-sa">{sa_short}</td>
            <td class="grade-cell"><span class="grade {grade_class}">{grade}</span></td></tr>"""
    return rows


def _build_findings_sections(
    findings_by_group: dict[str, list[dict[str, Any]]],
    total: int,
) -> str:
    group_order = ["security", "resources", "performance", "traffic"]
    sections = ""

    for gk in group_order:
        findings = findings_by_group.get(gk, [])
        meta = _GROUP_META.get(
            gk, {"icon": "", "label": gk.title(), "color": "#a1a1aa", "desc": ""}
        )

        crit = sum(1 for f in findings if f["severity"] == "critical")
        warn = sum(1 for f in findings if f["severity"] == "warning")
        info = sum(1 for f in findings if f["severity"] == "info")

        badges = ""
        if crit:
            badges += f'<span class="badge critical">{crit} critical</span>'
        if warn:
            badges += f'<span class="badge warning">{warn} warning</span>'
        if info:
            badges += f'<span class="badge info">{info} info</span>'
        if not findings:
            badges = '<span class="badge ok-badge">all clear</span>'

        rows = ""
        for f in findings:
            sev = f["severity"]
            affected = f.get("affected_services", [])
            count = len(affected)
            scope_text = f"all {total}" if count >= total else f"{count}/{total}"
            scope_pct = count / max(total, 1) * 100
            bar_class = (
                "bar-crit"
                if sev == "critical"
                else ("bar-warn" if sev == "warning" else "bar-info")
            )

            rows += f"""<div class="finding-row">
                <div class="finding-sev">{_SEVERITY_ICONS.get(sev, '')}</div>
                <div class="finding-body">
                    <div class="finding-title">{_e(f['category'].replace('_', ' ').title())}</div>
                    <div class="finding-detail">{_e(f['message'])}</div>
                    <div class="finding-fix">{_e(f['recommendation'])}</div>
                </div>
                <div class="finding-scope">
                    <div class="scope-text">{scope_text} services</div>
                    <div class="scope-bar"><div class="scope-fill {bar_class}" style="width:{scope_pct:.0f}%"></div></div>
                </div>
            </div>"""

        sections += f"""
        <div class="finding-group fade-in" data-group="{gk}">
            <div class="group-header" style="border-left:3px solid {meta['color']}">
                <div class="group-icon" style="color:{meta['color']}">{meta['icon']}</div>
                <div>
                    <div class="group-title">{meta['label']}</div>
                    <div class="group-desc">{meta['desc']}</div>
                </div>
                <div class="group-badges">{badges}</div>
                <div class="group-chevron"></div>
            </div>
            <div class="group-body">
                {rows if rows else '<div class="no-findings">No issues detected</div>'}
            </div>
        </div>"""

    return sections


def _delta(
    cur: float | int, prev: float | int, fmt: str = "num", invert: bool = False
) -> str:
    """Format a delta between current and previous values."""
    diff = cur - prev
    if diff == 0 or prev == 0:
        return ""
    pct = diff / abs(prev) * 100

    is_good = diff < 0 if not invert else diff > 0
    color = "var(--ok)" if is_good else "var(--crit)"
    arrow = "&#x25B2;" if diff > 0 else "&#x25BC;"

    if fmt == "cost":
        return f'<span class="delta" style="color:{color}">{arrow} ${abs(diff):.2f} ({abs(pct):.0f}%)</span>'
    if fmt == "pct":
        return (
            f'<span class="delta" style="color:{color}">{arrow} {abs(pct):.0f}%</span>'
        )
    return f'<span class="delta" style="color:{color}">{arrow} {abs(diff):.0f} ({abs(pct):.0f}%)</span>'


def _build_comparison_banner(comparison: dict[str, Any]) -> str:
    """Build a comparison banner showing changes since last run."""
    fd = comparison.get("fleet_delta", {})
    prev_ts = comparison.get("previous_timestamp", "")

    ts_display = prev_ts[:16].replace("T", " ") if prev_ts else "unknown"

    cost_from = fd.get("monthly_cost", {}).get("from", 0)
    cost_to = fd.get("monthly_cost", {}).get("to", 0)
    crit_from = fd.get("critical", {}).get("from", 0)
    crit_to = fd.get("critical", {}).get("to", 0)
    warn_from = fd.get("warnings", {}).get("from", 0)
    warn_to = fd.get("warnings", {}).get("to", 0)
    req_from = fd.get("daily_requests", {}).get("from", 0)
    req_to = fd.get("daily_requests", {}).get("to", 0)

    added = comparison.get("services_added", [])
    removed = comparison.get("services_removed", [])
    changed = comparison.get("service_changes", [])

    changes_html = ""
    if added:
        changes_html += f'<span class="delta-tag new">+{len(added)} new</span>'
    if removed:
        changes_html += (
            f'<span class="delta-tag removed">-{len(removed)} removed</span>'
        )
    if changed:
        changes_html += f'<span class="delta-tag changed">{len(changed)} changed</span>'

    return f"""
    <div class="comparison-banner fade-in">
        <div class="comp-label">vs previous run ({ts_display} UTC)</div>
        <div class="comp-deltas">
            <div class="comp-item">
                <span class="comp-key">Cost</span>
                {_delta(cost_to, cost_from, "cost")}
            </div>
            <div class="comp-item">
                <span class="comp-key">Critical</span>
                {_delta(crit_to, crit_from)}
            </div>
            <div class="comp-item">
                <span class="comp-key">Warnings</span>
                {_delta(warn_to, warn_from)}
            </div>
            <div class="comp-item">
                <span class="comp-key">Req/day</span>
                {_delta(req_to, req_from, invert=True) or '<span class="delta" style="color:var(--dim)">&mdash;</span>'}
            </div>
            <div class="comp-item">{changes_html}</div>
        </div>
    </div>"""


def generate_dashboard(
    data: dict[str, Any],
    *,
    comparison: dict[str, Any] | None = None,
) -> str:
    """Generate a self-contained HTML dashboard string."""
    fleet = data["fleet"]
    services = data["services"]
    findings_by_group = data.get("findings_by_group", {})
    fc = fleet["findings_summary"]

    svc_rows = _build_svc_rows(services)
    findings_html = _build_findings_sections(findings_by_group, fleet["total_services"])
    infra_html = _build_infra_cards(fleet)
    comparison_html = _build_comparison_banner(comparison) if comparison else ""

    chart_data = json.dumps(
        {
            svc["name"]: svc.get("time_series", {})
            for svc in services
            if svc.get("status") != "error"
        }
    )

    total_findings = fc.get("critical", 0) * 3 + fc.get("warning", 0)
    max_expected = fleet["total_services"] * 6
    health_pct = max(
        0, min(100, int(100 - (total_findings / max(max_expected, 1)) * 100))
    )

    health_color = (
        "var(--ok)"
        if health_pct >= 75
        else ("var(--warn)" if health_pct >= 50 else "var(--crit)")
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cloud Run Fleet Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
/* ===== OBSIDIAN + TEAL THEME ===== */
:root {{
    --bg:#09090b; --surface:#18181b; --surface2:#27272a; --surface3:#3f3f46;
    --text:#fafafa; --muted:#a1a1aa; --dim:#52525b; --border:#27272a;
    --crit:#ef4444; --warn:#eab308; --info:#3b82f6; --ok:#22c55e;
    --accent:#14b8a6; --accent-dim:rgba(20,184,166,0.1);
    --crit-bg:#450a0a; --crit-fg:#fca5a5;
    --warn-bg:#422006; --warn-fg:#fde047;
    --info-bg:#172554; --info-fg:#93c5fd;
    --ok-bg:#052e16; --ok-fg:#86efac;
    --radius:8px;
    --font-body:'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    --font-mono:'JetBrains Mono','SF Mono',Monaco,'Cascadia Code',monospace;
}}
@media(prefers-color-scheme:light) {{
    :root {{
        --bg:#fafafa; --surface:#ffffff; --surface2:#f4f4f5; --surface3:#e4e4e7;
        --text:#09090b; --muted:#71717a; --dim:#a1a1aa; --border:#e4e4e7;
        --accent:#0d9488; --accent-dim:rgba(13,148,136,0.08);
        --crit-bg:#fef2f2; --crit-fg:#dc2626;
        --warn-bg:#fefce8; --warn-fg:#a16207;
        --info-bg:#eff6ff; --info-fg:#2563eb;
        --ok-bg:#f0fdf4; --ok-fg:#16a34a;
    }}
}}

/* ===== RESET ===== */
*{{margin:0;padding:0;box-sizing:border-box}}

/* ===== ANIMATIONS ===== */
@keyframes fadeUp{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
.fade-in{{animation:fadeUp .4s ease-out both}}
.fade-in:nth-child(1){{animation-delay:.03s}}.fade-in:nth-child(2){{animation-delay:.06s}}
.fade-in:nth-child(3){{animation-delay:.09s}}.fade-in:nth-child(4){{animation-delay:.12s}}
.fade-in:nth-child(5){{animation-delay:.15s}}.fade-in:nth-child(6){{animation-delay:.18s}}
@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation-duration:.01ms!important;animation-delay:0ms!important;transition-duration:.01ms!important}}}}

/* ===== BASE ===== */
body{{font-family:var(--font-body);background:var(--bg);color:var(--text);line-height:1.5;
    padding:32px;max-width:1440px;margin:0 auto}}
h1{{font-size:1.4rem;font-weight:700;letter-spacing:-.03em}}

/* ===== HEADER ===== */
.header{{display:flex;align-items:center;gap:20px;margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid var(--border)}}
.header-info{{flex:1;min-width:0}}
.header-sub{{color:var(--muted);font-size:.75rem;margin-top:2px}}
.header-sub strong{{color:var(--text);font-weight:500}}
.header-right{{text-align:right;flex-shrink:0}}
.header-right .label{{color:var(--dim);font-family:var(--font-mono);font-size:.6rem;text-transform:uppercase;letter-spacing:.08em}}
.header-right .cost{{font-size:1.5rem;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums}}

/* Health ring */
.health-ring{{width:56px;height:56px;position:relative;flex-shrink:0}}
.health-ring svg{{transform:rotate(-90deg)}}
.health-ring .ring-track{{fill:none;stroke:var(--surface2);stroke-width:4}}
.health-ring .ring-fill{{fill:none;stroke-width:4;stroke-linecap:round;transition:stroke-dasharray .6s ease}}
.health-ring .ring-text{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:.8rem;font-weight:700}}

/* ===== SECTION HEADERS ===== */
.section-title{{font-family:var(--font-mono);font-size:.65rem;font-weight:600;color:var(--dim);text-transform:uppercase;letter-spacing:.1em;margin:32px 0 12px;display:flex;align-items:center;gap:10px}}
.section-title::after{{content:'';flex:1;height:1px;background:var(--border)}}

/* ===== KPI ROW ===== */
.kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:24px}}
.kpi{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 18px;transition:border-color .15s}}
.kpi:hover{{border-color:var(--surface3)}}
.kpi .k-label{{color:var(--dim);font-family:var(--font-mono);font-size:.6rem;text-transform:uppercase;letter-spacing:.06em}}
.kpi .k-value{{font-size:1.75rem;font-weight:700;margin-top:4px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}}
.kpi .k-value.crit{{color:var(--crit)}}.kpi .k-value.warn{{color:var(--warn)}}
.kpi .k-value.ok{{color:var(--ok)}}

/* ===== INFRASTRUCTURE GRID ===== */
.infra-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;margin-bottom:24px}}
.infra-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 18px}}
.infra-label{{color:var(--dim);font-family:var(--font-mono);font-size:.6rem;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}}
.infra-row{{font-size:.82rem;margin:4px 0;color:var(--muted)}}
.infra-num{{font-weight:600;color:var(--text);font-variant-numeric:tabular-nums;font-family:var(--font-mono)}}
.infra-bad{{color:var(--crit)}}
.infra-bad .infra-num{{color:var(--crit)}}
.infra-tags{{display:flex;flex-wrap:wrap;gap:4px}}
.tag{{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:99px;font-size:.7rem;font-family:var(--font-mono);background:var(--surface2);color:var(--muted)}}
.tag strong{{color:var(--text);font-weight:600}}
.tag-warn{{background:var(--warn-bg);color:var(--warn-fg)}}.tag-ok{{background:var(--ok-bg);color:var(--ok-fg)}}

/* ===== TABLE ===== */
.table-wrap{{border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;background:var(--surface)}}
.table-scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
table{{width:100%;border-collapse:collapse}}
th{{background:var(--surface2);padding:8px 12px;text-align:left;font-family:var(--font-mono);font-size:.6rem;
    text-transform:uppercase;letter-spacing:.06em;color:var(--dim);white-space:nowrap;font-weight:600}}
td{{padding:8px 12px;border-top:1px solid var(--border);font-size:.8rem}}
.svc-row{{cursor:pointer;transition:background .15s}}
.svc-row:hover{{background:var(--surface2)}}.svc-row.selected{{background:var(--accent-dim)}}
.svc-name{{font-weight:600;white-space:nowrap}}
.svc-sa{{color:var(--dim);font-family:var(--font-mono);font-size:.7rem;max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.num{{text-align:right;font-variant-numeric:tabular-nums;font-family:var(--font-mono);font-size:.75rem}}
.mono{{font-family:var(--font-mono);font-size:.72rem;color:var(--muted)}}
.val-bad{{color:var(--crit);font-weight:600}}.val-warn{{color:var(--warn)}}
.grade-cell{{text-align:center}}
.grade{{display:inline-block;width:26px;height:26px;line-height:26px;border-radius:99px;font-family:var(--font-mono);font-size:.7rem;font-weight:700;text-align:center}}
.grade-a{{background:var(--ok-bg);color:var(--ok-fg)}}.grade-c{{background:var(--warn-bg);color:var(--warn-fg)}}.grade-f{{background:var(--crit-bg);color:var(--crit-fg)}}

/* ===== BADGES ===== */
.badge{{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:99px;font-family:var(--font-mono);font-size:.6rem;font-weight:600;margin-left:4px}}
.badge.critical{{background:var(--crit-bg);color:var(--crit-fg)}}.badge.warning{{background:var(--warn-bg);color:var(--warn-fg)}}
.badge.info{{background:var(--info-bg);color:var(--info-fg)}}.badge.ok-badge{{background:var(--ok-bg);color:var(--ok-fg)}}

/* ===== FINDING GROUPS ===== */
.finding-group{{margin-bottom:8px}}
.group-header{{display:flex;align-items:center;gap:12px;padding:14px 18px;background:var(--surface);
    border:1px solid var(--border);border-radius:var(--radius);cursor:pointer;transition:background .15s,border-color .15s;user-select:none}}
.group-header:hover{{background:var(--surface2);border-color:var(--surface3)}}
.group-icon{{flex-shrink:0}}
.g-icon{{width:18px;height:18px}}
.group-title{{font-weight:600;font-size:.88rem}}.group-desc{{color:var(--dim);font-size:.7rem;margin-top:1px}}
.group-badges{{margin-left:auto;display:flex;gap:4px;flex-shrink:0}}
.group-chevron{{width:16px;color:var(--dim);transition:transform .2s;font-size:.55rem;flex-shrink:0}}
.group-chevron::after{{content:'\\25BC'}}
.finding-group.collapsed .group-chevron{{transform:rotate(-90deg)}}
.group-body{{overflow:hidden;transition:max-height .3s}}
.finding-group.collapsed .group-body{{display:none}}

/* ===== FINDING ROWS ===== */
.finding-row{{display:flex;gap:12px;padding:12px 18px;border-top:1px solid var(--border);background:var(--surface);align-items:flex-start}}
.finding-row:last-child{{border-radius:0 0 var(--radius) var(--radius)}}
.finding-sev{{flex-shrink:0;margin-top:2px}}
.sev-icon{{width:14px;height:14px}}
.sev-crit{{color:var(--crit)}}.sev-warn{{color:var(--warn)}}.sev-info{{color:var(--info)}}.sev-ok{{color:var(--ok)}}
.finding-body{{flex:1;min-width:0}}
.finding-title{{font-weight:600;font-size:.82rem}}
.finding-detail{{color:var(--muted);font-size:.75rem;margin-top:3px;line-height:1.5}}
.finding-fix{{color:var(--dim);font-size:.7rem;margin-top:5px;font-style:italic}}
.finding-scope{{width:100px;flex-shrink:0;text-align:right}}
.scope-text{{font-family:var(--font-mono);font-size:.65rem;color:var(--muted);margin-bottom:4px}}
.scope-bar{{height:4px;background:var(--surface2);border-radius:2px;overflow:hidden}}
.scope-fill{{height:100%;border-radius:2px;transition:width .4s ease}}
.bar-crit{{background:var(--crit)}}.bar-warn{{background:var(--warn)}}.bar-info{{background:var(--info)}}
.no-findings{{padding:18px;color:var(--dim);font-size:.8rem}}

/* ===== CHARTS ===== */
.charts-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:8px;margin-top:12px}}
.chart-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px}}
.chart-card h3{{font-family:var(--font-mono);font-size:.65rem;color:var(--dim);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}}
.chart-card canvas{{width:100%!important;height:180px!important}}
.filter-hint{{color:var(--dim);font-size:.6rem;font-weight:400;text-transform:none;letter-spacing:0;margin-left:8px}}

/* ===== FOOTER ===== */
.footer{{margin-top:48px;padding:20px 0;border-top:1px solid var(--border);text-align:center}}
.footer-brand{{font-size:.8rem;color:var(--muted);margin-bottom:4px}}
.footer-brand strong{{color:var(--text)}}
.footer-meta{{font-size:.65rem;color:var(--dim)}}
.footer-meta code{{background:var(--surface2);border:1px solid var(--border);padding:2px 8px;border-radius:4px;font-family:var(--font-mono);font-size:.6rem;color:var(--muted)}}
.footer-sep{{margin:0 8px;opacity:0.3}}

/* ===== COMPARISON BANNER ===== */
.comparison-banner{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px 18px;margin-bottom:24px}}
.comp-label{{font-family:var(--font-mono);font-size:.6rem;color:var(--dim);text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px}}
.comp-deltas{{display:flex;flex-wrap:wrap;gap:18px;align-items:center}}
.comp-item{{display:flex;align-items:center;gap:6px}}
.comp-key{{font-size:.75rem;color:var(--muted)}}
.delta{{font-family:var(--font-mono);font-size:.75rem;font-weight:600}}
.delta-tag{{display:inline-flex;align-items:center;padding:3px 10px;border-radius:99px;font-family:var(--font-mono);font-size:.6rem;font-weight:600;margin-left:2px}}
.delta-tag.new{{background:var(--ok-bg);color:var(--ok-fg)}}
.delta-tag.removed{{background:var(--crit-bg);color:var(--crit-fg)}}
.delta-tag.changed{{background:var(--info-bg);color:var(--info-fg)}}

/* ===== RESPONSIVE ===== */
@media(max-width:768px){{
    body{{padding:16px}}
    .header{{flex-wrap:wrap;gap:12px}}
    .header-right{{width:100%;text-align:left}}
    .kpi-row{{grid-template-columns:repeat(2,1fr)}}
    .infra-grid{{grid-template-columns:1fr}}
    .charts-grid{{grid-template-columns:1fr}}
    .finding-row{{flex-wrap:wrap}}
    .finding-scope{{width:100%;text-align:left;margin-top:8px}}
}}
</style>
</head><body>

<div class="header fade-in">
    <div class="health-ring">
        <svg width="56" height="56" viewBox="0 0 56 56">
            <circle class="ring-track" cx="28" cy="28" r="23"/>
            <circle class="ring-fill" cx="28" cy="28" r="23"
                stroke="{health_color}"
                stroke-dasharray="{health_pct * 1.445} 145" />
        </svg>
        <div class="ring-text" style="color:{health_color}">{health_pct}</div>
    </div>
    <div class="header-info">
        <h1>Cloud Run Fleet Report</h1>
        <div class="header-sub"><strong>Engineering Team</strong> &rsaquo; Cloud Architecture &rsaquo; Cloud Run Specialist &mdash; {fleet['total_services']} services</div>
    </div>
    <div class="header-right">
        <div class="label">Est. Monthly Cost</div>
        <div class="cost">${fleet['total_monthly_cost']:.2f}</div>
    </div>
</div>

{comparison_html}

<div class="kpi-row">
    <div class="kpi fade-in"><div class="k-label">Daily Requests</div><div class="k-value">{_reqs(fleet['total_daily_requests'])}</div></div>
    <div class="kpi fade-in"><div class="k-label">Critical Issues</div><div class="k-value crit">{fc.get('critical',0)}</div></div>
    <div class="kpi fade-in"><div class="k-label">Warnings</div><div class="k-value warn">{fc.get('warning',0)}</div></div>
    <div class="kpi fade-in"><div class="k-label">Informational</div><div class="k-value ok">{fc.get('info',0)}</div></div>
</div>

<div class="section-title">Infrastructure Overview</div>
{infra_html}

<div class="section-title">Services</div>
<div class="table-wrap fade-in">
<div class="table-scroll">
<table>
<thead><tr>
    <th>Service</th><th>Region</th><th>CPU</th><th>Mem</th><th>Min/Max</th>
    <th>Req/day</th><th>CPU Util</th><th>P99</th><th>Errors</th><th>$/mo</th><th>SA</th><th>Health</th>
</tr></thead>
<tbody>{svc_rows}</tbody>
</table>
</div></div>

<div class="section-title">Findings by Category</div>
{findings_html}

<div class="section-title">Metrics (24h)<span class="filter-hint">click a service row to filter</span></div>
<div class="charts-grid">
    <div class="chart-card fade-in"><h3>Requests / Hour</h3><canvas id="c-req"></canvas></div>
    <div class="chart-card fade-in"><h3>CPU Utilization</h3><canvas id="c-cpu"></canvas></div>
    <div class="chart-card fade-in"><h3>Latency &mdash; P50 (solid) &bull; P99 (dashed)</h3><canvas id="c-lat"></canvas></div>
    <div class="chart-card fade-in"><h3>Active Instances</h3><canvas id="c-inst"></canvas></div>
</div>

<div class="footer">
    <div class="footer-brand">
        <strong>Engineering Team</strong>
        <span class="footer-sep">&middot;</span>
        Cloud Architecture
        <span class="footer-sep">&middot;</span>
        <span style="color:var(--accent)">Cloud Run Specialist</span>
    </div>
    <div class="footer-meta">
        The infrastructure review your team never has time for
        <span class="footer-sep">&middot;</span>
        <code>uvx cloudrun-agent install</code>
    </div>
</div>

<script>
document.querySelectorAll('.group-header').forEach(h=>h.addEventListener('click',()=>h.parentElement.classList.toggle('collapsed')));

const D={chart_data};
const isDark=window.matchMedia('(prefers-color-scheme:dark)').matches||!window.matchMedia('(prefers-color-scheme:light)').matches;
const C=isDark?['#14b8a6','#22d3ee','#a78bfa','#f472b6','#fbbf24','#34d399','#60a5fa','#fb923c','#94a3b8']
              :['#0d9488','#0891b2','#7c3aed','#db2777','#d97706','#059669','#2563eb','#ea580c','#64748b'];
const gridC=isDark?'#27272a':'#e4e4e7';
const tickC=isDark?'#52525b':'#a1a1aa';
const tooltipBg=isDark?'#27272a':'#ffffff';
const tooltipTitle=isDark?'#fafafa':'#09090b';
const tooltipBody=isDark?'#a1a1aa':'#71717a';
const tooltipBorder=isDark?'#3f3f46':'#e4e4e7';
const legendC=isDark?'#a1a1aa':'#71717a';

const base={{responsive:true,animation:{{duration:400,easing:'easeOutQuart'}},interaction:{{mode:'index',intersect:false}},
    plugins:{{legend:{{labels:{{color:legendC,boxWidth:10,padding:8,font:{{size:10,family:"'DM Sans',sans-serif"}}}}}},
        tooltip:{{backgroundColor:tooltipBg,titleColor:tooltipTitle,bodyColor:tooltipBody,borderColor:tooltipBorder,borderWidth:1,padding:10,cornerRadius:6,
            titleFont:{{family:"'DM Sans',sans-serif",size:11,weight:'600'}},bodyFont:{{family:"'JetBrains Mono',monospace",size:10}}}}}},
    scales:{{x:{{type:'time',time:{{tooltipFormat:'MMM d, HH:mm'}},grid:{{color:gridC,lineWidth:0.5}},ticks:{{color:tickC,font:{{size:9,family:"'JetBrains Mono',monospace"}},maxRotation:0}}}},
        y:{{grid:{{color:gridC,lineWidth:0.5}},ticks:{{color:tickC,font:{{size:9,family:"'JetBrains Mono',monospace"}}}},beginAtZero:true}}}}
}};
function ds(k,f){{let r=[],i=0;for(const[s,t]of Object.entries(D)){{if(f&&s!==f)continue;const p=t[k];if(!p||!p.length)continue;
    r.push({{label:s,data:p.map(v=>({{x:new Date(v.t),y:v.v}})),borderColor:C[i%C.length],borderWidth:1.5,pointRadius:1.5,pointHoverRadius:5,tension:0.3,fill:false}});i++}}return r}}
function lds(f){{let r=[],i=0;for(const[s,t]of Object.entries(D)){{if(f&&s!==f)continue;const c=C[i%C.length];
    if(t.latency_p50?.length)r.push({{label:s+' P50',data:t.latency_p50.map(v=>({{x:new Date(v.t),y:v.v}})),borderColor:c,borderWidth:1.5,pointRadius:1.5,tension:0.3,fill:false}});
    if(t.latency_p99?.length)r.push({{label:s+' P99',data:t.latency_p99.map(v=>({{x:new Date(v.t),y:v.v}})),borderColor:c,borderDash:[5,3],borderWidth:1.5,pointRadius:1.5,tension:0.3,fill:false}});i++}}return r}}
let ch={{}};
function render(f){{Object.values(ch).forEach(c=>c.destroy());ch={{}};
    const yl=l=>({{...base,scales:{{...base.scales,y:{{...base.scales.y,title:{{display:true,text:l,color:tickC,font:{{size:9,family:"'JetBrains Mono',monospace"}}}}}}}}}});
    ch.r=new Chart(document.getElementById('c-req'),{{type:'line',data:{{datasets:ds('request_count',f)}},options:yl('req')}});
    ch.c=new Chart(document.getElementById('c-cpu'),{{type:'line',data:{{datasets:ds('cpu_utilization',f)}},
        options:{{...yl('%'),scales:{{...yl('%').scales,y:{{...yl('%').scales.y,max:1,ticks:{{...yl('%').scales.y.ticks,callback:v=>(v*100)+'%'}}}}}}}}}});
    ch.l=new Chart(document.getElementById('c-lat'),{{type:'line',data:{{datasets:lds(f)}},options:yl('sec')}});
    ch.i=new Chart(document.getElementById('c-inst'),{{type:'line',data:{{datasets:ds('instance_count',f)}},options:yl('inst')}})}}
render(null);
let sel=null;
document.querySelectorAll('.svc-row').forEach(r=>r.addEventListener('click',()=>{{
    const s=r.dataset.service;if(sel===s){{sel=null;r.classList.remove('selected')}}
    else{{document.querySelectorAll('.svc-row').forEach(x=>x.classList.remove('selected'));sel=s;r.classList.add('selected')}}
    render(sel)}}));
</script>
</body></html>"""
