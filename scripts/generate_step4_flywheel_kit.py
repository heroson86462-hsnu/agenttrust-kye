"""
generate_step4_flywheel_kit.py — Generates the weekly Step 4 Cold-Start Viral
Acquisition Kit (Show HN, Reddit, X Thread & Top-20 Maintainer Dynamic Badge Outreach)
strictly from real SQLite probe telemetry in kye_production.db.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import os
import sqlite3
import statistics
from typing import Any, Dict, List

EDGE_BASE_URL = "https://agenttrust-kye-edge-gateway.a2a-data-matrix.workers.dev"
GITHUB_URL = "https://github.com/heroson86462-hsnu/agenttrust-kye"
PYPI_URL = "https://pypi.org/project/agenttrust-kye/"
MCPSO_URL = "https://mcp.so/servers/agenttrust-kye"
DEFAULT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src",
    "agenttrust_kye",
    "kye_production.db",
)


def _pct(part: int, total: int) -> str:
    return f"{(part / total * 100):.1f}%" if total > 0 else "0.0%"


def compute_telemetry(db_path: str) -> Dict[str, Any]:
    """Query kye_production.db and compute exact live probe & leaderboard metrics."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM kye_endpoints").fetchall()]
    conn.close()

    by_source = Counter(r["registry_source"] for r in rows)
    by_grade = Counter(r["security_grade"] for r in rows)
    by_action = Counter(r["recommended_action"] for r in rows)

    remote_rows = [
        r
        for r in rows
        if r["registry_source"] == "official_mcp_registry" and r["transport_type"] != "stdio"
    ]
    live_jsonrpc = [r for r in remote_rows if "Live JSON-RPC tools/list verified" in r["diagnostic_notes"]]
    auth_gated = [
        r for r in remote_rows if any(code in r["diagnostic_notes"] for code in ("HTTP 401", "HTTP 403"))
    ]
    loop_hazards = [r for r in remote_rows if "LOOP_HAZARD" in r["diagnostic_notes"]]
    unreachable = [
        r
        for r in remote_rows
        if "Probe timeout/connection error" in r["diagnostic_notes"]
        or "HTTP 5" in r["diagnostic_notes"]
        or r["uptime_pct"] < 80.0
    ]
    live_rug_pulls = [
        r for r in rows if r["rug_pull_detected"] == 1 and r["registry_source"] != "community_crawl"
    ]

    remote_latencies = sorted(int(r["latency_ms"]) for r in remote_rows if int(r["latency_ms"]) > 0)
    p50_ms = int(statistics.median(remote_latencies)) if remote_latencies else 0
    max_ms = max(remote_latencies) if remote_latencies else 0

    top20_candidates = sorted(
        [
            r
            for r in rows
            if r["security_grade"] in ("A+", "A")
            and r["recommended_action"] == "ALLOW"
            and r["registry_source"] in ("official_mcp_registry", "github_topic_mcp_server")
        ],
        key=lambda x: (-int(x["kye_score"]), -int(x["stars_or_popularity"]), int(x["latency_ms"])),
    )[:20]

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total_indexed": len(rows),
        "by_source": dict(by_source),
        "by_grade": dict(by_grade),
        "by_action": dict(by_action),
        "remote_total": len(remote_rows),
        "live_jsonrpc": live_jsonrpc,
        "auth_gated": auth_gated,
        "loop_hazards": loop_hazards,
        "unreachable": unreachable,
        "live_rug_pulls": live_rug_pulls,
        "p50_ms": p50_ms,
        "max_ms": max_ms,
        "top20": top20_candidates,
    }


def _format_rug_pull_note(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "0 mid-flight SHA-256 tool schema mutations detected in this batch."
    items = [f"`{r['service_name']}` ({r['latency_ms']}ms, score {r['kye_score']}/100)" for r in rows]
    return "; ".join(items)


def render_kit_markdown(t: Dict[str, Any]) -> str:
    """Render the complete Step 4 Cold-Start Viral Acquisition Kit Markdown."""
    n_remote = t["remote_total"]
    n_jsonrpc = len(t["live_jsonrpc"])
    n_auth = len(t["auth_gated"])
    n_loop = len(t["loop_hazards"])
    n_down = len(t["unreachable"])
    n_rug = len(t["live_rug_pulls"])
    n_gh = t["by_source"].get("github_topic_mcp_server", 0)
    n_reg = t["by_source"].get("official_mcp_registry", 0)
    rug_note = _format_rug_pull_note(t["live_rug_pulls"])

    outreach_rows: List[str] = []
    for idx, r in enumerate(t["top20"], start=1):
        slug = r["slug"]
        badge_md = (
            f"[![AgentTrust KYE](https://img.shields.io/endpoint?url="
            f"{EDGE_BASE_URL}/v1/badge/{slug})]({EDGE_BASE_URL})"
        )
        outreach_rows.append(
            f"| {idx} | `{r['service_name']}` | `{r['registry_source']}` | "
            f"**{r['kye_score']}/100 ({r['security_grade']})** | {r['stars_or_popularity']} | "
            f"`{slug}` | `{badge_md}` |"
        )
    outreach_table = "\n".join(outreach_rows)

    return f"""# 🚀 AgentTrust KYE — Step 4 Cold-Start Viral Acquisition & Maintainer Outreach Kit
> Generated: {t['generated_at']} | Data Source: Live SQLite Canary Telemetry (`kye_production.db`)

---

## 1. Real Live Telemetry Summary (Verified First-Principles Data)

| Metric | Live Observed Value | Notes |
| :--- | :--- | :--- |
| **Total Indexed MCP Servers** | **{t['total_indexed']}** | Official MCP Registry: {n_reg} · GitHub `topic:mcp-server`: {n_gh} |
| **Live Remote HTTP/SSE Probes** | **{n_remote}** | Non-destructive JSON-RPC `tools/list` canary checks |
| **Verified Live `tools/list` Endpoints** | **{n_jsonrpc} / {n_remote} ({_pct(n_jsonrpc, n_remote)})** | Returned valid MCP tool schemas + pinned SHA-256 hash |
| **Auth-Gated (`HTTP 401/403`)** | **{n_auth} / {n_remote} ({_pct(n_auth, n_remote)})** | Clean JSON error (not HTML loop) |
| **Unreachable / Probe Timeout / `5xx`** | **{n_down} / {n_remote} ({_pct(n_down, n_remote)})** | Connection error or timeout >5s |
| **HTML 200 Reasoning-Loop Hazards** | **{n_loop} / {n_remote} ({_pct(n_loop, n_remote)})** | `text/html` returned with HTTP 200 |
| **Mid-Flight Schema Hash Mutations** | **{n_rug}** | {rug_note} |
| **Remote Probe Latency (p50 / max)** | **{t['p50_ms']}ms / {t['max_ms']}ms** | Measured over live TLS endpoints |

---

## 2. Hacker News (`Show HN`) Draft

**Title**:
`Show HN: AgentTrust KYE – Runtime firewall & SHA-256 tool pinning for MCP servers`

**Body**:
```text
Hi HN,

Static scanners only inspect an MCP server once when you install it. In practice, remote MCP endpoints can mutate their `tools/list` schema mid-flight (CVE-2025-54136 style rug pulls), return HTML login/error pages with HTTP 200 (trapping agents in expensive reasoning loops), or hide prompt-injection payloads and invisible Unicode smuggling inside tool descriptions.

I built AgentTrust KYE (Know-Your-Endpoint), an open-source runtime MCP firewall + public canary oracle:
- GitHub: {GITHUB_URL}
- PyPI (`uvx agenttrust-kye`): {PYPI_URL}
- Live Leaderboard (Cloudflare Edge + Fly.io Tokyo): {EDGE_BASE_URL}
- MCP.so Listing: {MCPSO_URL}

We just ran a live probe across {t['total_indexed']} indexed MCP servers ({n_gh} high-star GitHub `topic:mcp-server` repos + {n_reg} entries from the Official MCP Registry, including {n_remote} remote HTTP/SSE endpoints):
- {n_jsonrpc}/{n_remote} ({_pct(n_jsonrpc, n_remote)}) remote endpoints returned live, parseable JSON-RPC `tools/list` schemas (p50 latency {t['p50_ms']}ms, max {t['max_ms']}ms).
- {n_auth}/{n_remote} ({_pct(n_auth, n_remote)}) were auth-gated (401/403).
- {n_down}/{n_remote} ({_pct(n_down, n_remote)}) timed out or failed connection checks.
- {n_rug} remote endpoint(s) triggered a mid-flight SHA-256 `tools/list` hash mutation alert compared to our prior canary pin ({rug_note}).

What you can run locally for free in 5 seconds (zero cloud dependency for scanning):
  "mcpServers": {{ "agenttrust-kye": {{ "command": "uvx", "args": ["agenttrust-kye"] }} }}

It exposes `scan_mcp_tools_locally` (sub-ms offline poisoning/Unicode smuggling scan + canonical SHA-256 hash) alongside `check_endpoint_kye_trust` and a Python `guard_endpoint()` helper. Public leaderboard & Shields.io badge endpoints are free at the Cloudflare edge; high-frequency automated runtime SLA checks use optimistic x402 (0.005 USDC on Base, <2ms verify, 10-min idempotency).

Would love feedback on the pinning heuristic and which edge failure modes you've seen in production MCP deployments.
```

---

## 3. Reddit (`r/LocalLLaMA` & `r/ClaudeAI`) Draft

**Title**:
`We probed {n_remote} live remote MCP servers (and {t['total_indexed']} total indexed) for tool poisoning, timeouts & mid-flight schema mutations — here's the open-source firewall + data`

**Post Markdown**:
```markdown
Static MCP audits break the moment a remote MCP server changes its `tools/list` JSON a week after you installed it, or starts returning a Cloudflare/login HTML page with HTTP `200 OK` (causing Claude/Cursor/autonomous agents to burn tokens retrying).

We open-sourced **AgentTrust KYE** (`uvx agenttrust-kye`) — a local `stdio` MCP security firewall + live runtime canary leaderboard:

- **GitHub (MIT)**: {GITHUB_URL}
- **Live Edge Leaderboard**: {EDGE_BASE_URL}
- **Official MCP Registry**: `io.github.heroson86462-hsnu/agenttrust-kye`

### What our live canary probe ({t['generated_at']}) found across {t['total_indexed']} servers:
- **{n_remote} remote HTTP/SSE endpoints** probed with non-destructive JSON-RPC `tools/list`:
  - **{n_jsonrpc} ({_pct(n_jsonrpc, n_remote)})** returned valid live `tools/list` JSON schemas (median latency **{t['p50_ms']}ms**, max **{t['max_ms']}ms**).
  - **{n_auth} ({_pct(n_auth, n_remote)})** returned clean `401/403` auth challenges.
  - **{n_down} ({_pct(n_down, n_remote)})** were unreachable or timed out (>5s).
  - **{n_loop} ({_pct(n_loop, n_remote)})** returned `text/html` with HTTP `200` (reasoning-loop hazard).
  - **{n_rug}** triggered a **mid-flight SHA-256 schema hash mutation** alert vs. our earlier pin: {rug_note}.

### Add free local scanning to Claude Desktop / Cursor in 5 seconds:
```json
{{
  "mcpServers": {{
    "agenttrust-kye": {{
      "command": "uvx",
      "args": ["agenttrust-kye"]
    }}
  }}
}}
```
Full source, SSRF guards, Unicode zero-width smuggling scanner, and Python `guard_endpoint()` wrapper are in the repo. Happy to add any public MCP server to the canary probe list!
```

---

## 4. X / Twitter 5-Post Thread Draft

1. **Hook**:
   `Static MCP security checks fail on day 7. We probed {n_remote} live remote MCP endpoints (and indexed {t['total_indexed']} servers across the Official MCP Registry + GitHub) for timeouts, HTML-200 loops, tool poisoning & mid-flight schema changes. Thread 🧵👇`
2. **Data**:
   `Live probe breakdown ({t['generated_at']}):`
   `• {n_jsonrpc}/{n_remote} ({_pct(n_jsonrpc, n_remote)}) returned valid live tools/list JSON (p50: {t['p50_ms']}ms)`
   `• {n_auth}/{n_remote} auth-gated (401/403)`
   `• {n_down}/{n_remote} timed out / unreachable`
   `• {n_rug} mid-flight SHA-256 tool schema mutation detected ({rug_note})`
3. **Architecture**:
   `Every MCP tool call is vulnerable if descriptions contain hidden exfil prompts, zero-width Unicode chars, or mutated schemas. AgentTrust KYE computes deterministic SHA-256 tool pins + runs sub-ms poisoning scans before your agent executes or pays.`
4. **5-Second Install**:
   `Free local firewall for Claude Desktop / Cursor / Windsurf in 5 seconds:`
   `uvx agenttrust-kye`
   `Python LangChain/CrewAI/AgentKit 2-liner:`
   `from agenttrust_kye import guard_endpoint`
   `guard_endpoint("cloudflare-docs-remote-mcp", min_kye_score=75)`
5. **CTA**:
   `Open-source (MIT), live on PyPI + Official MCP Registry + MCP.so:`
   `GitHub: {GITHUB_URL}`
   `Live Leaderboard: {EDGE_BASE_URL}`

---

## 5. Top 20 `A+` / `A` MCP Projects — Dynamic Shields.io Badge Outreach Kit

Every badge below connects live to `GET {EDGE_BASE_URL}/v1/badge/<slug>` (cached at Cloudflare Edge, `$0` cost):

| Rank | MCP Server | Source | KYE Score | Stars / Pop | Slug | Ready-to-Paste Markdown Badge |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{outreach_table}

### Maintainer Outreach Message Template (Polite, Zero-Spam GitHub Discussion / Issue)

> **Subject**: `AgentTrust KYE Runtime Verification Score: {{SCORE}}/100 ({{GRADE}}) for {{PROJECT_NAME}}`
>
> Hi maintainers 👋,
>
> Congratulations — **{{PROJECT_NAME}}** scored **{{SCORE}}/100 ({{GRADE}})** in our latest public [Global MCP Trust & Security Leaderboard]({EDGE_BASE_URL}) (`Official MCP Registry` + GitHub canary checks for schema stability, zero prompt-injection/Unicode-smuggling patterns, and uptime).
>
> If you'd like to display a live runtime-verified badge in your `README.md`, here is a dynamic Shields.io endpoint badge backed by Cloudflare Edge (no API key or account needed):
>
> ```markdown
> [![AgentTrust KYE](https://img.shields.io/endpoint?url={EDGE_BASE_URL}/v1/badge/{{SLUG}})]({EDGE_BASE_URL})
> ```
>
> Everything is open-source (MIT) at {GITHUB_URL} (`uvx agenttrust-kye`). Feel free to close or ignore if you prefer not to add third-party badges — and thank you for building reliable MCP tooling!
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Step 4 Cold-Start Viral Acquisition Kit")
    parser.add_argument("--db", type=str, default=DEFAULT_DB, help="Path to kye_production.db")
    parser.add_argument("--out", type=str, required=True, help="Output Markdown path")
    args = parser.parse_args()

    telemetry = compute_telemetry(args.db)
    content = render_kit_markdown(telemetry)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(content)
    print(
        f"[Step 4 Flywheel Kit] Generated {args.out} "
        f"(total_indexed={telemetry['total_indexed']}, remote_probed={telemetry['remote_total']})"
    )


if __name__ == "__main__":
    main()
