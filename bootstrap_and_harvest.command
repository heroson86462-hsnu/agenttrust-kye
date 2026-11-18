#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"

LOG_FILE="LAST_VERIFICATION_LOG.txt"
exec > >(tee "$LOG_FILE") 2>&1

echo "=================================================================="
echo " 🛡️ A2A Data Matrix & AgentTrust KYE — Full Local Verification"
echo " Started at: $(date)"
echo "=================================================================="

if [ ! -d ".venv" ]; then
  echo "[Setup] Creating isolated Python virtual environment (.venv)..."
  python3 -m venv .venv
fi

echo "[Setup] Installing dependencies into .venv..."
.venv/bin/python -m pip install --upgrade pip -q
.venv/bin/python -m pip install -q -e ".[dev]"

echo ""
echo "------------------------------------------------------------------"
echo " [1/3] Testing Wave-1 Release Package (agenttrust-kye v1.0.0)"
echo "------------------------------------------------------------------"
.venv/bin/python -m pytest -v

if [ -f "../verify_all_mvps.py" ]; then
  echo ""
  echo "------------------------------------------------------------------"
  echo " [2/3] Testing All 5 Hardened v2.0 MVPs + Super-Router"
  echo "------------------------------------------------------------------"
  .venv/bin/python ../verify_all_mvps.py
fi

echo ""
echo "------------------------------------------------------------------"
echo " [3/3] Harvesting Live Public MCP Registries -> Report"
echo "------------------------------------------------------------------"
.venv/bin/python -m agenttrust_kye.harvester --limit 25 --report PUBLIC_MCP_TRUST_REPORT.md

echo ""
echo "=================================================================="
echo " ✅ ALL TESTS & LIVE MCP HARVEST COMPLETED SUCCESSFULLY!"
echo " 📄 Report saved to: $(pwd)/PUBLIC_MCP_TRUST_REPORT.md"
echo " 📋 Log saved to   : $(pwd)/$LOG_FILE"
echo "=================================================================="
