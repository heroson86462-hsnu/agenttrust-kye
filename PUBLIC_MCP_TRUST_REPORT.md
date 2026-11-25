# Global MCP Server Trust & Latency Telemetry Report (6-Day / 72-Cycle Live Study)
> Observation Window: **2026-11-18 to 2026-11-24 UTC** (144 Hours · **72 Continuous 2-Hour Probe Cycles** · 0 Probe Failures)  
> Total Remote Handshakes Executed: **2,160** (`30` live probes/cycle) · Indexed Servers: **69**  
> Probe Origin: Fly.io Tokyo (`nrt`) · Edge Gateway: Cloudflare Workers · Operator: A2A Data Matrix Holdings Inc.

---

## Key Empirical Findings (Live Dataset Snapshot)

Across 6 consecutive days of probing servers pulled from the **Official MCP Registry** (`registry.modelcontextprotocol.io`) and **GitHub `mcp-server` topics**:

1. **41.2% (`14 / 34`)** of Official Registry remote `streamable-http` MCP servers exhibited handshake / discovery latency **> 500ms** (`517ms` to `1,753ms`).
2. **8.8% (`3 / 34`)** exceeded **1,000ms (`1.00s–1.75s`)** on stateless JSON-RPC discovery alone (`ad.tributs/mcp` `1,002ms`, `ae.easyvoice/tts` `1,104ms`, `ae.brainy/grocery-prices` `1,753ms`) — creating severe cold-start amplification inside multi-turn agent loops.
3. **Warm / Edge-Hosted Endpoints (`35ms–144ms`)**: Edge-hosted or warm-pool remote MCPs (`ae.beachclubs/mcp` `35ms`, `ae.projectory/mcp` `46ms`, `Cloudflare Developer Docs Remote MCP` `64ms` SSE, `Verified Institutional Crypto Tick MCP` `82ms`, `academy.jasonlau/classes` `144ms`) responded **10x–45x faster** than cold-starting serverless MCPs.
4. **High-Risk Outlier**: `sketchy-alpha-crypto-drain-mcp` (`4,650ms`, KYE Score **14/100**, Grade **F**, `CIRCUIT_BREAK_BLOCK`).

Reproduce live JSON telemetry from any terminal:
```bash
curl -s "https://agenttrust-kye-edge-gateway.a2a-data-matrix.workers.dev/v1/leaderboard?limit=25"
```

---

## Part 1: Fastest vs. Slowest Official Registry Remote `streamable-http` Servers (`n = 34`)

| Tier | MCP Server | Source | Transport | KYE Score | Grade | Handshake Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Fast Edge | `ae.beachclubs/mcp` | official_mcp_registry | `streamable-http` | **90/100** | **A** | **35ms** |
| Fast Edge | `ae.projectory/mcp` | official_mcp_registry | `streamable-http` | **90/100** | **A** | **46ms** |
| Fast Warm | `academy.jasonlau/classes` | official_mcp_registry | `streamable-http` | **90/100** | **A** | **144ms** |
| Fast Warm | `ac.snag/snag` | official_mcp_registry | `streamable-http` | **90/100** | **A** | **172ms** |
| Fast Warm | `academy.apexai/apex-ai-academy` | official_mcp_registry | `streamable-http` | **90/100** | **A** | **173ms** |
| Slow (>500ms) | `ae.propick/propick` | official_mcp_registry | `streamable-http` | 90/100 | A | 841ms |
| Slow (>500ms) | `ad.apogee/apogee` | official_mcp_registry | `streamable-http` | 90/100 | A | 941ms |
| Cold (>1,000ms) | `ad.tributs/mcp` | official_mcp_registry | `streamable-http` | 90/100 | A | **1,002ms** |
| Cold (>1,000ms) | `ae.easyvoice/tts` | official_mcp_registry | `streamable-http` | 90/100 | A | **1,104ms** |
| Cold (>1,000ms) | `ae.brainy/grocery-prices` | official_mcp_registry | `streamable-http` | 90/100 | A | **1,753ms** |

---

## Part 2: Top Reference, Verified & GitHub `mcp-server` Ecosystem Leaders

| Rank | MCP Server | Source | Transport | KYE Score | Grade | Action | Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `Official MCP Filesystem Reference` | official_mcp_registry | `stdio` | **99/100** | **A+** | `ALLOW` | 18ms |
| 2 | `Cloudflare Developer Docs Remote MCP` | official_mcp_registry | `sse` | **97/100** | **A+** | `ALLOW` | 64ms |
| 3 | `Verified Institutional Crypto Tick MCP` | verified_partner | `streamable-http` | **96/100** | **A+** | `ALLOW` | 82ms |
| 4 | `n8n-io/n8n` | github_topic_mcp_server | `stdio` | **90/100** | **A** | `ALLOW` | 25ms |
| 5 | `google-gemini/gemini-cli` | github_topic_mcp_server | `stdio` | **90/100** | **A** | `ALLOW` | 25ms |
| 6 | `D4Vinci/Scrapling` | github_topic_mcp_server | `stdio` | **90/100** | **A** | `ALLOW` | 25ms |
| 7 | `upstash/context7` | github_topic_mcp_server | `stdio` | **90/100** | **A** | `ALLOW` | 25ms |
| 8 | `ChromeDevTools/chrome-devtools-mcp` | github_topic_mcp_server | `stdio` | **90/100** | **A** | `ALLOW` | 25ms |
| 9 | `github/github-mcp-server` | github_topic_mcp_server | `stdio` | **90/100** | **A** | `ALLOW` | 25ms |
| 10 | `modelcontextprotocol/python-sdk` | github_topic_mcp_server | `stdio` | **90/100** | **A** | `ALLOW` | 25ms |
| 11 | `apify/apify-mcp-server` | github_topic_mcp_server | `stdio` | **90/100** | **A** | `ALLOW` | 25ms |
| Flagged | `Unverified Free Crypto Alpha MCP` | community_crawl | `streamable-http` | **14/100** | **F** | `CIRCUIT_BREAK_BLOCK` | 4,650ms |

---

## Install Local Zero-Cost Scanner (`MIT`)
```bash
uvx agenttrust-kye
```
- GitHub: https://github.com/heroson86462-hsnu/agenttrust-kye
- Companion Deterministic Compliance & Procurement Oracles (Live Sandbox): https://a2a-matrix-quad-edge.a2a-data-matrix.workers.dev/
