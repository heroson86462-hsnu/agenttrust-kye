# 🚀 Wave 1 開路先鋒（AgentTrust KYE）真實雲端上線與冷啟動獲客作戰手冊

本目錄（`wave1-agenttrust-kye-release/`）是一個**完全獨立、可直接 `git init` 推送並發布至 PyPI、Official MCP Registry、Smithery、Fly.io 與 Cloudflare Workers** 的生產級發行包。

---

## Step 1：在本機一鍵跑完測試 ＋ 抓取全球第一批真實公開 MCP 註冊表（3 分鐘）

打開 Mac 終端機執行：

```bash
cd "/Users/edmundhu/Library/CloudStorage/GoogleDrive-heroson86462@gmail.com/我的雲端硬碟/antigravity-projects/a2a-data-ventures/wave1-agenttrust-kye-release"

# 1. 安裝套件與測試工具並執行 6 大資安與協定單元測試
python3 -m pip install -e ".[dev]"
pytest -v

# 2. 連線真實 Official MCP Registry + GitHub API 抓取首批熱門 MCP 並產出病毒行銷報告！
agenttrust-kye-harvest --limit 30 --report PUBLIC_MCP_TRUST_REPORT.md
```

執行後目錄下會自動生成 **`PUBLIC_MCP_TRUST_REPORT.md`**（真實公開 MCP 伺服器的信任評分與延遲排行榜）與本地資料庫！

---

## Step 2：部署「零冷啟動」雲端 Oracle 至 Fly.io ＋ Cloudflare 全球邊緣快取（10 分鐘）

### A. 部署後端至 Fly.io（已預設 `min_machines_running = 1` 消除冷啟動超時）
```bash
# 登入 Fly.io 並建立應用程式與 3GB NVMe 持久化磁碟區（東京節點 nrt）
fly auth login
fly apps create agenttrust-kye-oracle
fly volumes create kye_data --region nrt --size 3 --app agenttrust-kye-oracle

# 收款錢包已預設寫入 fly.toml (0x5ab8fBd41e0691876fE3cC3b0dF62A901C2cD044)
# 且預設採用免註冊 Keyless Open x402 Facilitator (https://facilitator.payai.network)，無需申請 Coinbase CDP 金鑰！
fly secrets set KYE_TREASURY_WALLET="0x5ab8fBd41e0691876fE3cC3b0dF62A901C2cD044" --app agenttrust-kye-oracle

# 一鍵打包 Docker 並部署上線！
fly deploy
```

### B. 部署 Cloudflare Worker 全球 `<15ms` 邊緣閘道（綁定 `kye.helloyunivia.com`）
```bash
cd cloudflare-worker
npx wrangler login
npx wrangler deploy
```
接著至 Cloudflare 後台 `Workers & Pages -> agenttrust-kye-edge-gateway -> Settings -> Domains & Routes` 新增自訂子網域 **`kye.helloyunivia.com`**，全球 300+ 節點即刻生效！

---

## Step 3：發布開源引流木馬至 PyPI 與三大 MCP 市集（5 分鐘）

### 1. 推送至 GitHub 並自動發布 PyPI（使全球開發者可執行 `uvx agenttrust-kye`）
```bash
git init
git add .
git commit -m "feat: initial production release of agenttrust-kye v1.0.0"
git branch -M main
git remote add origin https://github.com/a2a-data-matrix/agenttrust-kye.git
git push -u origin main

# 打上版本標籤，觸發 GitHub Actions 自動建置並上架 PyPI
git tag v1.0.0
git push origin v1.0.0
```
*(首次上架前，至 `pypi.org -> Manage -> Publishing` 新增 Pending Publisher：`Owner: a2a-data-matrix`, `Repo: agenttrust-kye`, `Workflow: ci-and-publish.yml` 即可免金鑰自動發布！)*

### 2. 一鍵登錄全球三大 MCP 市集（零廣告費自然流量入口）
1. **Official MCP Registry**：專案根目錄已備妥符合官方規範之 `server.json`，使用官方 CLI 執行 `mcp-publisher login github && mcp-publisher publish` 即刻上架。
2. **Smithery.ai**：專案根目錄已內建 `smithery.yaml`，登入 `https://smithery.ai/new` 連結此 GitHub Repo 即可開啟一鍵安裝頁。
3. **Glama.ai / MCP.so**：貼上 GitHub Repo 網址提交，系統會自動抓取 `server.json` 與 `LICENSE`（MIT 授權可拿滿合規高分）。

---

## Step 4：Day 1–Day 14 零廣告費「冷啟動病毒獲客飛輪」執行清單

1. **「免費本地掃描吸粉 → 雲端即時 SLA 變現」漏斗**：
   * 個人開發者在 Cursor / Claude Desktop 免費安裝 `uvx agenttrust-kye` 掃描本地工具。
   * 當企業團隊把 `guard_endpoint()` 放進生產環境的採購／交易 Agent 迴圈時，高頻即時查詢自動轉為 `0.005 USDC` `x402` 現金流或企業預付月費。
2. **每週自動發布《Global MCP Ecosystem Uptime & Rug-Pull Report》**：
   * 將 `agenttrust-kye-harvest` 產出的真實數據（例如：「本週我們實測了 200 個公開遠端 MCP 伺服器，發現 14% 會吐出 HTML 錯誤頁害 Agent 死循環、3 個發生未宣告 Schema 突變」）發佈至 Reddit `r/LocalLLaMA`、`r/ClaudeAI`、Hacker News (`Show HN`) 與 X。
3. **反向發送「A+ KYE Verified 徽章」PR 給高星開源專案**：
   * 對排行榜前 20 名獲得 `A+` 評分的熱門 MCP 專案發送友善 Issue 或宣傳提及，邀請維護者貼上 `AgentTrust KYE Verified A+` 徽章——每一個貼上徽章的專案都會成為我們永久的免費反向連結與品牌背書！
