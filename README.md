<!--
mcp-name: io.github.heroson86462-hsnu/agenttrust-kye
-->

# 🛡️ AgentTrust KYE (`agenttrust-kye`)

**Know-Your-Endpoint (KYE) Runtime Firewall, Anti-Rug-Pull & `x402` Billing-Trap Oracle for AI Agents.**

[![MCP Compatible](https://img.shields.io/badge/MCP-2026--07--28-00b4d8)](https://modelcontextprotocol.io)
[![x402 Ready](https://img.shields.io/badge/HTTP%20402-x402%20USDC-10b981)](https://x402.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Static scanners only inspect an MCP server once at install time. **AgentTrust KYE** protects autonomous AI agents **at runtime** against:
1. **Mid-Flight "Rug Pull" Schema Mutations (`CVE-2025-54136`)** — servers that pass day-1 review and inject malicious instructions on day 7.
2. **HTML 502/503 Reasoning Loops** — flaky wrappers returning Cloudflare HTML pages as `HTTP 200`, causing agents to burn dollars in retry loops.
3. **MCP03 Tool Poisoning & Invisible Unicode Smuggling** — hidden credential exfiltration (`~/.ssh`, `.env`) and wallet-drain prompts.
4. **Dishonest `x402` Overcharge Traps** — endpoints demanding 100x their advertised micropayment price.

---

## ⚡ 5-Second Free IDE Firewall Install (Claude Desktop / Cursor / Windsurf / Antigravity)

Add `agenttrust-kye` to your `mcp_config.json` via `uvx` (zero manual setup):

```json
{
  "mcpServers": {
    "agenttrust-kye": {
      "command": "uvx",
      "args": ["agenttrust-kye"]
    }
  }
}
```

### Included MCP Tools
* `scan_mcp_tools_locally` *(100% Free Offline)* — Sub-millisecond local scan of any MCP `tools/list` payload + canonical SHA-256 pinning hash.
* `check_endpoint_kye_trust` — Live `0–100` KYE Trust Score, uptime SLA, Rug-Pull check, and verified safe fallback routing.
* `list_top_trusted_mcp_servers` — Discover `A+` verified MCP servers by category.

---

## 🐍 2-Line Python Firewall for LangChain / CrewAI / Coinbase AgentKit

```python
from agenttrust_kye import guard_endpoint

# Automatically raises AgentTrustBlockedError (with safe fallback) if KYE score < 60
verdict = guard_endpoint("cloudflare-docs-remote-mcp", min_kye_score=75)
```

---

## 🌐 Remote Cloud Oracle (`MCP` + Optimistic `x402`)

* **Streamable HTTP MCP**: `POST https://agenttrust-kye-edge-gateway.a2a-data-matrix.workers.dev/mcp`
* **Paid KYE Check (`0.005 USDC` on Base, `<2ms` Optimistic Verify, 10-Min Idempotency)**:  
  `GET https://agenttrust-kye-edge-gateway.a2a-data-matrix.workers.dev/v1/kye/check?endpoint=<slug_or_url>`
* **Free Edge-Cached Leaderboard**: `GET https://agenttrust-kye-edge-gateway.a2a-data-matrix.workers.dev/v1/leaderboard`

---

## 🏅 Add the "KYE Verified" Badge to Your MCP Server

Maintainers of reliable MCP servers can embed live KYE trust status in their README:

```markdown
[![KYE Trust Score](https://img.shields.io/badge/AgentTrust_KYE-Verified_A%2B-10b981)](https://agenttrust-kye-edge-gateway.a2a-data-matrix.workers.dev)
```

---

Built by **A2A Data Matrix Holdings Inc.** · Maintainer: Edmund Hu (`edmundhu@helloyunivia.com`)
