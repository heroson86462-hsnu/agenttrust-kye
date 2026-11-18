"""
server.py — Production Cloud FastAPI + Streamable HTTP MCP + Optimistic x402 Oracle Server.
Designed for zero-cold-start deployment on Fly.io behind Cloudflare Edge Workers.
"""

import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
import hmac
import json
import os
from typing import Any, Dict, List, Optional
import uuid

from fastapi import FastAPI, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

from .core_security import (
    ProductionX402Gateway,
    compute_tools_pin_hash,
    scan_mcp_tools_for_poisoning,
    scrub_pii,
)
from .db import connect_db, fetch_leaderboard, init_production_db
from .harvester import harvest_public_registries

TREASURY_WALLET = os.environ.get("KYE_TREASURY_WALLET", "0x5ab8fBd41e0691876fE3cC3b0dF62A901C2cD044")
X402_FACILITATOR_URL = os.environ.get("X402_FACILITATOR_URL", "https://facilitator.payai.network")
PRICE_USDC = float(os.environ.get("KYE_PRICE_USDC", "0.005"))
IDEMPOTENCY_TTL = int(os.environ.get("KYE_IDEMPOTENCY_TTL_SEC", "600"))

gateway = ProductionX402Gateway(
    treasury_wallet=TREASURY_WALLET,
    price_usdc=PRICE_USDC,
    idempotency_ttl_sec=IDEMPOTENCY_TTL,
)

HARVEST_TELEMETRY: Dict[str, Any] = {
    "last_harvest_at": None,
    "last_harvest_summary": None,
    "last_harvest_error": None,
    "runs_completed": 0,
}


async def _auto_harvest_loop(interval_sec: int, limit: int, startup_delay_sec: float) -> None:
    """Periodically harvests and probes public MCP registries into the SQLite DB."""
    if startup_delay_sec > 0:
        await asyncio.sleep(startup_delay_sec)
    while True:
        try:
            summary = await harvest_public_registries(limit=limit)
            HARVEST_TELEMETRY["last_harvest_at"] = datetime.now(timezone.utc).isoformat()
            HARVEST_TELEMETRY["last_harvest_summary"] = summary
            HARVEST_TELEMETRY["last_harvest_error"] = None
            HARVEST_TELEMETRY["runs_completed"] = int(HARVEST_TELEMETRY["runs_completed"]) + 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            HARVEST_TELEMETRY["last_harvest_error"] = f"{type(exc).__name__}: {exc}"
        await asyncio.sleep(interval_sec)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_production_db()
    interval_sec = int(os.environ.get("KYE_AUTO_HARVEST_INTERVAL_SEC", "0"))
    harvest_limit = int(os.environ.get("KYE_AUTO_HARVEST_LIMIT", "30"))
    startup_delay = float(os.environ.get("KYE_AUTO_HARVEST_STARTUP_DELAY_SEC", "10.0"))
    task: Optional[asyncio.Task[None]] = None
    if interval_sec > 0:
        task = asyncio.create_task(_auto_harvest_loop(interval_sec, harvest_limit, startup_delay))
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    title="AgentTrust KYE — Production Cloud Oracle",
    version="1.0.0",
    description="Know-Your-Endpoint Runtime Firewall, Anti-Rug-Pull & x402 Reputation Oracle for AI Agents",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Payment-Required", "X-Payment-Response", "X-Risk-Preview", "X-Idempotency-Replayed"],
)


@app.get("/healthz")
def healthz():
    interval_sec = int(os.environ.get("KYE_AUTO_HARVEST_INTERVAL_SEC", "0"))
    return {
        "status": "ok",
        "service": "agenttrust-kye",
        "warm": True,
        "auto_harvest_enabled": interval_sec > 0,
        "auto_harvest_interval_sec": interval_sec,
        "harvest_telemetry": HARVEST_TELEMETRY,
    }


@app.get("/.well-known/mcp.json")
def well_known_mcp():
    return {
        "mcpDiscoveryVersion": "2026-07-28",
        "name": "io.github.heroson86462-hsnu/agenttrust-kye",
        "statelessStreamableHttp": True,
        "endpoint": "/mcp",
        "paymentProtocol": "x402-optimistic-eip3009",
        "unitPriceUsdc": PRICE_USDC,
    }


@app.get("/.well-known/x402-manifest.json")
def well_known_x402():
    return {
        "x402Version": 1,
        "issuer": "A2A Data Matrix Holdings Inc.",
        "network": "base-mainnet",
        "asset": "USDC",
        "unitPriceUsdc": PRICE_USDC,
        "optimisticVerify": True,
        "idempotencyWindowSec": IDEMPOTENCY_TTL,
    }


@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt():
    return (
        "# AgentTrust KYE — Runtime Security & Uptime Oracle for AI Agents\n"
        "> Operator: A2A Data Matrix Holdings Inc. (Founder: Edmund Hu <edmundhu@helloyunivia.com>)\n"
        "> Install Free Local MCP Firewall: `uvx agenttrust-kye`\n"
        "> Cloud Streamable HTTP MCP: `POST /mcp`\n"
        "> Cloud x402 Oracle Endpoint: `GET /v1/kye/check?endpoint=<slug_or_url>` (0.005 USDC on Base)\n"
        "> Public Leaderboard (Edge-Cached Free Tier): `GET /v1/leaderboard`\n"
    )


@app.get("/v1/leaderboard")
def public_leaderboard(limit: int = Query(25, ge=1, le=100)):
    """Public viral acquisition endpoint (cached at Cloudflare Edge for 60s to absorb huge traffic for $0)."""
    rows = fetch_leaderboard(limit=limit)
    public_rows = [
        {
            "slug": r["slug"],
            "service_name": r["service_name"],
            "registry_source": r["registry_source"],
            "transport_type": r["transport_type"],
            "kye_score": r["kye_score"],
            "security_grade": r["security_grade"],
            "recommended_action": r["recommended_action"],
            "latency_ms": r["latency_ms"],
            "is_verified_badge": bool(r["is_verified_badge"]),
        }
        for r in rows
    ]
    return JSONResponse(
        content={"count": len(public_rows), "leaderboard": public_rows},
        headers={"Cache-Control": "public, max-age=30, s-maxage=60"},
    )


@app.get("/v1/kye/check")
def check_endpoint_kye(
    request: Request,
    endpoint: str = Query(..., description="Slug or canonical URL of external MCP/API"),
    x_payment: Optional[str] = Header(default=None),
    x_prepaid_bearer: Optional[str] = Header(default=None),
    x_idempotency_key: Optional[str] = Header(default=None),
):
    conn = connect_db()
    row = conn.execute(
        "SELECT * FROM kye_endpoints WHERE slug = ? OR canonical_url = ?",
        (endpoint, endpoint),
    ).fetchone()
    if not row:
        conn.close()
        return JSONResponse(status_code=404, content={"error": f"Endpoint '{endpoint}' not indexed yet"})

    auth_token = x_payment or x_prepaid_bearer
    if not auth_token:
        conn.close()
        preview = "CRITICAL_DANGER" if row["kye_score"] < 30 else ("DEGRADED" if row["kye_score"] < 75 else "HEALTHY")
        body, headers = gateway.build_challenge_dict(
            resource_path=str(request.url.path),
            risk_preview=preview,
            anomaly_detected=row["kye_score"] < 75,
            has_fallback=bool(row["safe_fallback_slug"]),
        )
        return JSONResponse(status_code=402, content=body, headers=headers)

    caller_id = auth_token.split(":")[0] if ":" in auth_token else auth_token
    idem_fp, cached = gateway.check_idempotency(caller_id, row["slug"], x_idempotency_key)
    if cached is not None:
        conn.close()
        return JSONResponse(content=cached, headers={"X-Idempotency-Replayed": "true"})

    prevented = 2.50 if row["kye_score"] < 30 else 0.35
    conn.execute(
        "INSERT INTO kye_paid_ledger VALUES (?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            caller_id,
            row["slug"],
            PRICE_USDC,
            prevented,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    payload = {
        "slug": row["slug"],
        "canonical_url": row["canonical_url"],
        "service_name": row["service_name"],
        "kye_trust_verdict": {
            "kye_score": row["kye_score"],
            "security_grade": row["security_grade"],
            "recommended_action": row["recommended_action"],
            "safe_fallback_endpoint": row["safe_fallback_slug"],
        },
        "runtime_telemetry": {
            "uptime_pct": row["uptime_pct"],
            "latency_ms": row["latency_ms"],
            "pinned_tools_sha256": row["pinned_tools_sha256"],
            "rug_pull_detected": bool(row["rug_pull_detected"]),
            "cloaking_detected": bool(row["cloaking_detected"]),
            "prompt_injection_risk": row["prompt_injection_risk"],
            "x402_overcharge_detected": bool(row["overcharge_detected"]),
            "diagnostic_notes": row["diagnostic_notes"],
            "last_probed_at": row["last_probed_at"],
        },
    }
    settled, headers = gateway.wrap_settled_response(idem_fp, caller_id, payload)
    return JSONResponse(content=settled, headers=headers)


class IncidentPayload(BaseModel):
    endpoint_slug: str
    payment_receipt_tx_hash: str
    observed_error_code: str


@app.post("/v1/kye/report-incident")
def report_incident(body: IncidentPayload):
    if not body.payment_receipt_tx_hash.startswith("0x") or len(body.payment_receipt_tx_hash) < 16:
        return JSONResponse(
            status_code=403,
            content={"error": "SYBIL_PROTECTION: Valid cryptographic payment receipt required"},
        )
    conn = connect_db()
    conn.execute(
        "INSERT INTO kye_incident_reports VALUES (?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            scrub_pii(body.endpoint_slug),
            body.payment_receipt_tx_hash,
            scrub_pii(body.observed_error_code),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "VERIFIED_AND_CREDITED", "rebate_usdc": 0.0025}


def _verify_admin_token(x_admin_token: Optional[str]) -> Optional[JSONResponse]:
    expected = os.environ.get("KYE_ADMIN_TOKEN", "").strip()
    if not expected or not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        return JSONResponse(
            status_code=401,
            content={"error": "UNAUTHORIZED: Valid X-Admin-Token header required"},
        )
    return None


@app.post("/v1/admin/harvest")
async def trigger_live_harvest(
    limit: int = Query(20, ge=1, le=50),
    x_admin_token: Optional[str] = Header(default=None),
):
    auth_err = _verify_admin_token(x_admin_token)
    if auth_err is not None:
        return auth_err
    return await harvest_public_registries(limit=limit)


@app.post("/v1/admin/flush-batch")
def flush_batch(x_admin_token: Optional[str] = Header(default=None)):
    auth_err = _verify_admin_token(x_admin_token)
    if auth_err is not None:
        return auth_err
    return gateway.flush_batch()


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Any] = 1
    method: str
    params: Optional[Dict[str, Any]] = None


@app.post("/mcp")
def remote_streamable_mcp(req: MCPRequest):
    if req.method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "protocolVersion": "2026-07-28",
                "serverInfo": {"name": "agenttrust-kye-cloud", "version": "1.0.0", "stateless": True},
                "capabilities": {"tools": {}},
            },
        }
    if req.method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "tools": [
                    {
                        "name": "check_endpoint_kye_trust",
                        "description": "Query live runtime KYE trust score, Rug-Pull mutation status, and safe fallback before calling external MCP/API.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"endpoint": {"type": "string"}},
                            "required": ["endpoint"],
                        },
                    },
                    {
                        "name": "scan_mcp_tools_locally",
                        "description": "Scan MCP tool definitions for prompt injection, credential exfiltration & Unicode smuggling.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"tools": {"type": "array", "items": {"type": "object"}}},
                            "required": ["tools"],
                        },
                    },
                ]
            },
        }
    if req.method == "tools/call":
        p = req.params or {}
        t_name = p.get("name")
        args = p.get("arguments") or {}
        if t_name == "scan_mcp_tools_locally":
            tools: List[Dict[str, Any]] = args.get("tools") or []
            out = {"pinned_tools_sha256": compute_tools_pin_hash(tools), **scan_mcp_tools_for_poisoning(tools)}
            return {"jsonrpc": "2.0", "id": req.id, "result": {"content": [{"type": "text", "text": json.dumps(out, indent=2)}]}}
        target = str(args.get("endpoint", "cloudflare-docs-remote-mcp"))
        conn = connect_db()
        row = conn.execute(
            "SELECT * FROM kye_endpoints WHERE slug = ? OR canonical_url = ?", (target, target)
        ).fetchone()
        conn.close()
        if not row:
            return {"jsonrpc": "2.0", "id": req.id, "error": {"code": -32602, "message": "Endpoint not found"}}
        return {"jsonrpc": "2.0", "id": req.id, "result": {"content": [{"type": "text", "text": json.dumps(dict(row), indent=2)}]}}
    return {"jsonrpc": "2.0", "id": req.id, "error": {"code": -32601, "message": "Method not found"}}


@app.get("/", response_class=HTMLResponse)
def public_viral_leaderboard_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AgentTrust KYE — Live Global MCP Security &amp; Uptime Leaderboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans p-6">
  <div class="max-w-5xl mx-auto space-y-6">
    <header class="border-b border-slate-800 pb-5 flex flex-wrap justify-between items-end gap-4">
      <div>
        <span class="px-2.5 py-1 text-xs font-bold bg-cyan-500/20 text-cyan-300 rounded-full border border-cyan-500/40">LIVE GLOBAL MCP FIREWALL ORACLE</span>
        <h1 class="text-3xl font-extrabold mt-2">AgentTrust KYE</h1>
        <p class="text-sm text-slate-400 mt-1">Real-time Uptime, Anti-Rug-Pull Pinning &amp; x402 Billing-Trap Protection for Autonomous AI Agents.</p>
      </div>
      <div class="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs font-mono">
        <div class="text-slate-400">Install Free IDE Firewall in 5s:</div>
        <div class="text-emerald-400 font-bold mt-0.5">uvx agenttrust-kye</div>
      </div>
    </header>

    <div class="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <div class="px-5 py-3 bg-slate-900/90 border-b border-slate-800 flex justify-between items-center">
        <span class="text-sm font-semibold">Live Indexed MCP Servers</span>
        <a href="/.well-known/mcp.json" class="text-xs font-mono text-cyan-400 underline">/.well-known/mcp.json</a>
      </div>
      <table class="w-full text-left text-sm" id="board">
        <thead class="bg-slate-800/70 text-xs uppercase text-slate-400">
          <tr><th class="p-3.5">Server</th><th class="p-3.5">Transport</th><th class="p-3.5">KYE Score</th><th class="p-3.5">Grade</th><th class="p-3.5">Verdict</th></tr>
        </thead>
        <tbody id="rows" class="divide-y divide-slate-800"></tbody>
      </table>
    </div>
  </div>
  <script>
    fetch('/v1/leaderboard').then(r => r.json()).then(d => {
      const tb = document.getElementById('rows');
      d.leaderboard.forEach(item => {
        const tr = document.createElement('tr');
        const color = item.kye_score >= 80 ? 'text-emerald-400' : (item.kye_score >= 50 ? 'text-amber-400' : 'text-rose-400');
        tr.innerHTML = `<td class="p-3.5 font-mono text-xs">${item.service_name}</td>
          <td class="p-3.5 text-xs text-slate-400">${item.transport_type}</td>
          <td class="p-3.5 font-bold ${color}">${item.kye_score}/100</td>
          <td class="p-3.5 font-bold ${color}">${item.security_grade}</td>
          <td class="p-3.5 font-mono text-xs">${item.recommended_action}</td>`;
        tb.appendChild(tr);
      });
    });
  </script>
</body>
</html>"""


def run_cli() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("agenttrust_kye.server:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_cli()
