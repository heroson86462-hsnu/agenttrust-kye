"""
db.py — High-Concurrency WAL-Mode SQLite Persistence Layer for AgentTrust KYE Production Release.
"""

from datetime import datetime, timezone
import os
import sqlite3
from typing import Any, Dict, List, Optional
import uuid


def get_db_path() -> str:
    return os.environ.get(
        "KYE_DB_PATH",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "kye_production.db"),
    )


def connect_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    target = db_path or get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    conn = sqlite3.connect(target, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_production_db(db_path: Optional[str] = None) -> None:
    conn = connect_db(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS kye_endpoints (
            slug TEXT PRIMARY KEY,
            canonical_url TEXT UNIQUE NOT NULL,
            service_name TEXT NOT NULL,
            registry_source TEXT NOT NULL,
            transport_type TEXT NOT NULL,
            category TEXT NOT NULL,
            stars_or_popularity INTEGER DEFAULT 0,
            kye_score INTEGER NOT NULL,
            security_grade TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            uptime_pct REAL NOT NULL,
            latency_ms INTEGER NOT NULL,
            is_valid_json_or_mcp INTEGER NOT NULL,
            pinned_tools_sha256 TEXT,
            rug_pull_detected INTEGER DEFAULT 0,
            cloaking_detected INTEGER DEFAULT 0,
            prompt_injection_risk REAL DEFAULT 0.0,
            overcharge_detected INTEGER DEFAULT 0,
            diagnostic_notes TEXT NOT NULL,
            safe_fallback_slug TEXT,
            is_verified_badge INTEGER DEFAULT 0,
            first_seen_at TEXT NOT NULL,
            last_probed_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_kye_category_score ON kye_endpoints(category, kye_score DESC);
        CREATE INDEX IF NOT EXISTS idx_kye_url ON kye_endpoints(canonical_url);

        CREATE TABLE IF NOT EXISTS kye_paid_ledger (
            tx_id TEXT PRIMARY KEY,
            caller_id TEXT NOT NULL,
            endpoint_slug TEXT NOT NULL,
            amount_usdc REAL NOT NULL,
            loss_prevented_usd REAL NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS kye_incident_reports (
            report_id TEXT PRIMARY KEY,
            endpoint_slug TEXT NOT NULL,
            receipt_tx_hash TEXT NOT NULL,
            error_code TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    cur.execute("SELECT COUNT(*) as cnt FROM kye_endpoints")
    if cur.fetchone()["cnt"] == 0:
        now = datetime.now(timezone.utc).isoformat()
        seeds = [
            (
                "modelcontextprotocol-filesystem-ref",
                "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
                "Official MCP Filesystem Reference",
                "official_mcp_registry",
                "stdio",
                "devtools",
                18500,
                99,
                "A+",
                "ALLOW",
                100.0,
                18,
                1,
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                0,
                0,
                0.0,
                0,
                "Official reference implementation; deterministic tool schema pinned; zero injection vectors.",
                None,
                1,
                now,
                now,
            ),
            (
                "cloudflare-docs-remote-mcp",
                "https://docs.mcp.cloudflare.com/sse",
                "Cloudflare Developer Docs Remote MCP",
                "official_mcp_registry",
                "sse",
                "cloud_docs",
                4200,
                97,
                "A+",
                "ALLOW",
                99.98,
                64,
                1,
                "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                0,
                0,
                0.0,
                0,
                "Enterprise edge-hosted MCP; strict TLS 1.3 and stable tool manifest.",
                None,
                1,
                now,
                now,
            ),
            (
                "sketchy-alpha-crypto-drain-mcp",
                "https://free-alpha-quotes-unverified.example/mcp",
                "Unverified Free Crypto Alpha MCP",
                "community_crawl",
                "streamable-http",
                "crypto_data",
                12,
                14,
                "F",
                "CIRCUIT_BREAK_BLOCK",
                76.2,
                4650,
                0,
                "deadbeef0000111122223333444455556666777788889999aaaabbbbccccdddd",
                1,
                1,
                0.94,
                1,
                "CRITICAL: Mid-flight Rug-Pull schema mutation + hidden wallet-drain directive + x402 overcharge trap.",
                "verified-coinmetrics-mcp",
                0,
                now,
                now,
            ),
            (
                "verified-coinmetrics-mcp",
                "https://mcp.institutional-tickdata.example/v2",
                "Verified Institutional Crypto Tick MCP",
                "verified_partner",
                "streamable-http",
                "crypto_data",
                980,
                96,
                "A+",
                "ALLOW",
                99.95,
                82,
                1,
                "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
                0,
                0,
                0.0,
                0,
                "Verified Vendor Badge; deterministic schema & honest x402 billing.",
                None,
                1,
                now,
                now,
            ),
        ]
        for s in seeds:
            cur.execute(
                """
                INSERT INTO kye_endpoints VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                s,
            )
        conn.commit()
    conn.close()


def upsert_endpoint_record(record: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    """Upserts a harvested/probed MCP server and automatically detects Rug-Pull hash mutations!"""
    conn = connect_db(db_path)
    cur = conn.cursor()
    existing = cur.execute(
        "SELECT pinned_tools_sha256, first_seen_at, rug_pull_detected FROM kye_endpoints WHERE slug = ?",
        (record["slug"],),
    ).fetchone()

    now = datetime.now(timezone.utc).isoformat()
    first_seen = existing["first_seen_at"] if existing else now
    rug_pull = int(record.get("rug_pull_detected", 0))
    notes = record["diagnostic_notes"]

    if (
        existing
        and existing["pinned_tools_sha256"]
        and record.get("pinned_tools_sha256")
        and existing["pinned_tools_sha256"] != record["pinned_tools_sha256"]
    ):
        rug_pull = 1
        record["kye_score"] = min(record["kye_score"], 25)
        record["security_grade"] = "F"
        record["recommended_action"] = "CIRCUIT_BREAK_BLOCK"
        notes = f"RUG_PULL_HASH_MUTATION_DETECTED (prev={existing['pinned_tools_sha256'][:10]}...) | {notes}"

    cur.execute(
        """
        INSERT INTO kye_endpoints VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(slug) DO UPDATE SET
            canonical_url=excluded.canonical_url,
            service_name=excluded.service_name,
            stars_or_popularity=excluded.stars_or_popularity,
            kye_score=excluded.kye_score,
            security_grade=excluded.security_grade,
            recommended_action=excluded.recommended_action,
            uptime_pct=excluded.uptime_pct,
            latency_ms=excluded.latency_ms,
            is_valid_json_or_mcp=excluded.is_valid_json_or_mcp,
            pinned_tools_sha256=COALESCE(excluded.pinned_tools_sha256, kye_endpoints.pinned_tools_sha256),
            rug_pull_detected=excluded.rug_pull_detected,
            prompt_injection_risk=excluded.prompt_injection_risk,
            diagnostic_notes=excluded.diagnostic_notes,
            last_probed_at=excluded.last_probed_at
        """,
        (
            record["slug"],
            record["canonical_url"],
            record["service_name"],
            record.get("registry_source", "official_mcp_registry"),
            record.get("transport_type", "streamable-http"),
            record.get("category", "general"),
            int(record.get("stars_or_popularity", 0)),
            int(record["kye_score"]),
            record["security_grade"],
            record["recommended_action"],
            float(record.get("uptime_pct", 100.0)),
            int(record.get("latency_ms", 120)),
            int(record.get("is_valid_json_or_mcp", 1)),
            record.get("pinned_tools_sha256"),
            rug_pull,
            int(record.get("cloaking_detected", 0)),
            float(record.get("prompt_injection_risk", 0.0)),
            int(record.get("overcharge_detected", 0)),
            notes,
            record.get("safe_fallback_slug"),
            int(record.get("is_verified_badge", 0)),
            first_seen,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return {"slug": record["slug"], "kye_score": record["kye_score"], "rug_pull_detected": bool(rug_pull)}


def fetch_leaderboard(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = connect_db(db_path)
    rows = conn.execute(
        "SELECT * FROM kye_endpoints ORDER BY kye_score DESC, stars_or_popularity DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
