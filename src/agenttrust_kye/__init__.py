"""
AgentTrust KYE — Know-Your-Endpoint Runtime Firewall & Reputation SDK for AI Agents.
Operator: A2A Data Matrix Holdings Inc. (Founder: Edmund Hu <edmundhu@helloyunivia.com>)
"""

from typing import Any, Dict, Optional
import httpx

from .core_security import (
    compute_tools_pin_hash,
    scan_mcp_tools_for_poisoning,
    validate_safe_external_url,
)

__version__ = "1.0.0"
__all__ = [
    "__version__",
    "AgentTrustBlockedError",
    "guard_endpoint",
    "scan_mcp_tools_for_poisoning",
    "compute_tools_pin_hash",
    "validate_safe_external_url",
]


class AgentTrustBlockedError(RuntimeError):
    """Raised when an external MCP server or API fails the KYE trust threshold."""


def guard_endpoint(
    endpoint_slug_or_url: str,
    min_kye_score: int = 60,
    oracle_url: str = "https://agenttrust-kye-edge-gateway.a2a-data-matrix.workers.dev",
    payment_or_bearer_token: Optional[str] = None,
    timeout_sec: float = 3.0,
) -> Dict[str, Any]:
    """
    2-line drop-in firewall pre-check for LangChain, CrewAI, or Coinbase AgentKit tools.
    Raises AgentTrustBlockedError (with safe_fallback suggestion) if score < min_kye_score.
    """
    headers: Dict[str, str] = {}
    if payment_or_bearer_token:
        headers["X-Payment"] = payment_or_bearer_token

    with httpx.Client(timeout=timeout_sec) as client:
        resp = client.get(
            f"{oracle_url.rstrip('/')}/v1/kye/check",
            params={"endpoint": endpoint_slug_or_url},
            headers=headers,
        )
        if resp.status_code == 402:
            teaser = resp.json().get("free_diagnostic_teaser", {})
            if teaser.get("risk_preview_level") == "CRITICAL_DANGER":
                raise AgentTrustBlockedError(
                    f"KYE 402 Free Preview flagged CRITICAL_DANGER on {endpoint_slug_or_url}"
                )
            return resp.json()
        resp.raise_for_status()
        data = resp.json()
        score = data.get("kye_trust_verdict", {}).get("kye_score", 0)
        if score < min_kye_score:
            fb = data.get("kye_trust_verdict", {}).get("safe_fallback_endpoint")
            raise AgentTrustBlockedError(
                f"Blocked untrusted endpoint '{endpoint_slug_or_url}' (KYE={score} < {min_kye_score}). "
                f"Recommended safe fallback: {fb}"
            )
        return data
