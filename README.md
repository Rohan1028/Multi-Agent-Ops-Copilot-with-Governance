# Multi-Agent Ops Copilot with Governance

## Overview
Multi-Agent Ops Copilot orchestrates a Planner, Executor, and Reviewer agent to automate operational workflows with built-in governance. The system blends retrieval-augmented generation (RAG), policy enforcement, audit logging, and budget tracking to keep automation explainable and controllable.

### Architecture
```
+---------------------------+        +-----------------------+
|        FastAPI API        |        |        Typed CLI       |
+------------+--------------+        +-----------+-----------+
             |                               |
             v                               v
      +-------------+                 +-------------+
      |   Runtime   |<--------------->|  Governance |
      | (Agents +   |                 |  SQLite DB  |
      |  Orchestr.) |                 +-------------+
      +------+------+                        |
             |                               |
   +---------+---------+             +-------+-------+
   |   RAG Retriever   |             |  Tool Adapters |
   |  (BM25 + Corpus)  |             |  (GitHub/Jira) |
   +---------+---------+             +-------+-------+
             |                               |
             v                               v
        Local Markdown                Sandbox Repo / APIs
```

## Quickstart
1. **Install dependencies**
   ```bash
   make setup
   ```
2. **Seed demo data**
   ```bash
   python scripts/seed_demo.py
   ```
3. **Run the API**
   ```bash
   make run
   ```
4. **Try the CLI**
   ```bash
   python -m app.main demo
   ```

## Developer Workflow
- `make format` / `make lint` / `make test` keep code healthy.
- `make index` rebuilds the RAG index.
- `make bench` executes the evaluation harness.
- `make clean` removes runtime artefacts.

## Docker
```
docker compose up api
```
Runs FastAPI behind Uvicorn with live reload mounts. Add `web` service to start the Next.js dashboard (see below).

## Benchmarks
Execute the harness for baseline vs governed comparisons:
```bash
python scripts/run_benchmarks.py
```
Reports are written to `reports/harness_report.json` with success, hallucination, latency, and cost deltas. **Disclaimer:** metrics are simulated for reproducibility and reflect the stub provider, not any external API.

## Web Dashboard
```
cd web
npm install
npm run dev
```
The app proxies through `/app/api/proxy` to `http://localhost:8000`. Docker Compose users can run `docker compose up web api` which sets `NEXT_PUBLIC_API_BASE` automatically.

## Switching LLM Providers
Set `LLM_PROVIDER` in `.env`:
- `stub` (default, deterministic)
- `openai`
- `azure`

For OpenAI set `OPENAI_API_KEY` (optionally `OPENAI_MODEL`, defaults to `gpt-4o-mini`, and `OPENAI_API_BASE` for private endpoints). Azure requires `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` (and optional `AZURE_OPENAI_MODEL`). Missing secrets gracefully fall back to the stub provider, so the system keeps running even if the real API is unreachable.

Rate limiting and retries are handled automatically:
- `LLM_RATE_LIMIT_PER_MIN` caps provider calls per minute (defaults to 60).
- Tool policies (`runtime/policies.yaml`) supply additional throttles (e.g., GitHub/Jira approvals).
- When OpenAI/Azure return 429/5xx responses, the runtime will back off, retry, and finally fall back to the stub provider while recording the failure in metrics.

LLM usage metrics (tokens, latency, estimated cost) are logged to SQLite. The FastAPI service exposes:
- `GET /metrics/llm/summary` – aggregated spend/latency.
- `GET /metrics/llm/recent?limit=20` – recent invocations with provider/model details.

## Real GitHub / Jira Integrations
Populate the corresponding environment variables and the runtime will switch from mocks to real adapters:
- GitHub: `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`
- Jira: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`

Tokens are masked in audit logs. Least-privilege scopes are recommended (`repo:status`, `issues` for GitHub; project-level write for Jira). Approval gates remain required even when real clients are active.

## Resilience & Governance
- Planner decomposes tasks and flags high-risk tool usage for approval.
- Executor respects tool policies, budget limits, and prompt sanitisation.
- Reviewer enforces citations, blocks prompt-injection attempts, and logs decisions.
- Audits, budgets, and approvals are backed by SQLite for easy inspection.

## Repository Hygiene
- Follow Conventional Commits (see `CONTRIBUTING.md`).
- Keep files ASCII unless existing content requires otherwise.
- Update tests alongside new behaviours.

Enjoy building with the Ops Copilot!

## Live Telemetry Dashboard (Grafana)

To visualise real-time governance stats:
1. Run the API (make run).
2. In Grafana, add a data source using the JSON API plugin (or SimpleJson) pointing at http://localhost:8000/metrics.
3. Use /metrics/llm/timeseries for time-series panels (cost, latency, tokens) and /metrics/governance/summary for approval/reviewer stats.
4. Example panel queries:
   - GET /metrics/llm/timeseries ? transform points[*].created_at into the x-axis, points[*].cost_usd or points[*].total_tokens as series.
   - GET /metrics/governance/summary ? pie bar for approvals using pprovals.pending, pprovals.approved, pprovals.rejected.
5. Optionally schedule python scripts/export_metrics.py if you also want static CSV/JSON snapshots.

Suggested dashboards include:
- LLM Spend & Latency: dual-axis chart of cost_usd vs latency_ms.
- Approval Queue Health: bar for pending/approved/rejected.
- Reviewer Outcomes: stacked chart using counts from audit actions (llm_reject, eview_passed, etc.).

