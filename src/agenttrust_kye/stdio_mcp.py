"""
stdio_mcp.py — Cold-Start Developer Trojan Horse (`uvx agenttrust-kye`).
Runs as a zero-config local `stdio` MCP server inside Claude Desktop, Cursor, Windsurf, Cline, or Antigravity.
Provides:
  1. Free instant local `scan_mcp_tools_locally` (wins developer love & viral installs!)
  2. Live `check_endpoint_kye_trust` (queries local DB + cloud x402 Oracle for runtime SLA, Rug-Pull & fallback!)
  3. `list_top_trusted_mcp_servers` (drives verified vendor badge ecosystem!)
"""

import json
import os
import sys
from typing import Any, Dict, Optional

import httpx

from .core_security import compute_tools_pin_hash, scan_mcp_tools_for_poisoning
from .db import connect_db, fetch_leaderboard, init_production_db

DEFAULT_ORACLE_URL = os.environ.get("KYE_ORACLE_URL", "https://agenttrust-kye-edge-gateway.a2a-data-matrix.workers.dev")
PREPAID_BEARER = os.environ.get("KYE_PREPAID_BEARER", "")


def handle_jsonrpc_message(msg: Dict[str, Any], db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    method = msg.get("method", "")
    req_id = msg.get("id")

    # Notifications (no id) require no response
    if req_id is None and method.startswith("notifications/"):
        return None

    if method == "initialize":
        init_production_db(db_path)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "serverInfo": {"name": "agenttrust-kye", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "scan_mcp_tools_locally",
                        "description": "Free instant local security audit: scans any MCP `tools/list` JSON array for hidden prompt injection, credential exfiltration, Unicode smuggling, and computes a SHA-256 Rug-Pull pin hash.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "tools": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                    "description": "List of MCP tool objects ({name, description, inputSchema})",
                                }
                            },
                            "required": ["tools"],
                        },
                    },
                    {
                        "name": "check_endpoint_kye_trust",
                        "description": "Pre-call firewall check: returns 0-100 KYE runtime trust score, mid-flight Rug-Pull status, x402 overcharge warning, and safe fallback MCP server.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "endpoint": {
                                    "type": "string",
                                    "description": "Endpoint slug or canonical URL to verify before calling",
                                }
                            },
                            "required": ["endpoint"],
                        },
                    },
                    {
                        "name": "list_top_trusted_mcp_servers",
                        "description": "Returns top-ranked A+ verified MCP servers sorted by live KYE Trust Score.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"limit": {"type": "integer", "default": 10}},
                        },
                    },
                ]
            },
        }

    if method == "tools/call":
        params = msg.get("params") or {}
        tool_name = params.get("name")
        args = params.get("arguments") or {}

        if tool_name == "scan_mcp_tools_locally":
            tools = args.get("tools") or []
            scan = scan_mcp_tools_for_poisoning(tools)
            pin = compute_tools_pin_hash(tools)
            result_payload = {"pinned_tools_sha256": pin, **scan}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result_payload, indent=2)}]},
            }

        if tool_name == "check_endpoint_kye_trust":
            target = str(args.get("endpoint", "")).strip()
            init_production_db(db_path)
            conn = connect_db(db_path)
            row = conn.execute(
                "SELECT * FROM kye_endpoints WHERE slug = ? OR canonical_url = ?", (target, target)
            ).fetchone()
            conn.close()
            if row:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(dict(row), indent=2)}]},
                }
            # Fallback to cloud KYE Oracle
            headers = {"X-Prepaid-Bearer": PREPAID_BEARER} if PREPAID_BEARER else {}
            try:
                with httpx.Client(timeout=3.5) as client:
                    r = client.get(f"{DEFAULT_ORACLE_URL.rstrip('/')}/v1/kye/check", params={"endpoint": target}, headers=headers)
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"content": [{"type": "text", "text": r.text}]},
                    }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {"status": "UNKNOWN_ENDPOINT_CAUTION", "endpoint": target, "detail": str(exc)}
                                ),
                            }
                        ]
                    },
                }

        if tool_name == "list_top_trusted_mcp_servers":
            init_production_db(db_path)
            top = fetch_leaderboard(limit=int(args.get("limit", 10)), db_path=db_path)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(top, indent=2)}]},
            }

        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main() -> None:
    """Standard line-delimited JSON-RPC 2.0 stdio loop."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            resp = handle_jsonrpc_message(msg)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
