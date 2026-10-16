# TriagePilot™ — Autonomous Incident Analyst & Verifiable Evidentiary Bridge

> *"Every conclusion ships with proof, or it doesn't ship."*

[![Live Cloud Run Service](https://img.shields.io/badge/Live%20Platform-Cloud%20Run%20Active-success?style=for-the-badge&logo=googlecloud)](https://triagepilot-ywgad5nv3a-uc.a.run.app)
[![Verification Suite](https://img.shields.io/badge/Pytest%20Suite-197%20Passing-emerald?style=for-the-badge&logo=pytest)](eval/tests/)
[![AI Core](https://img.shields.io/badge/Vertex%20AI-Gemini%202.5%20Pro%20%2B%20Flash%20%2B%20Vision-4285F4?style=for-the-badge&logo=googlecloud)](engine/)
[![Agent Interop](https://img.shields.io/badge/Multi--Agent-Google%20ADK%20%2B%20A2A%20v0.2-teal?style=for-the-badge&logo=google)](api/a2a.py)
[![Audit Integrity](https://img.shields.io/badge/Audit%20Ledger-SHA--256%20Hash%20Chain-teal?style=for-the-badge)](https://triagepilot-ywgad5nv3a-uc.a.run.app/api/audit/verify)

- **Live Production URL:** [https://triagepilot-ywgad5nv3a-uc.a.run.app](https://triagepilot-ywgad5nv3a-uc.a.run.app)
- **Interactive Walkthrough Guide:** [`DEMO_WALKTHROUGH.md`](DEMO_WALKTHROUGH.md)
- **Architecture Specification:** [`ARCHITECTURE_AND_SPEC.md`](ARCHITECTURE_AND_SPEC.md)

---

## 📌 Overview

In enterprise software and financial infrastructure, incident response is bottlenecked by the **L1 → L2 → L3 escalation waterfall**:
- **L1 Support** receives ambiguous customer tickets (*"transfers failing!"*) and escalates without technical context.
- **L2 Operations** manually correlates distributed logs, transaction ledgers, and often-outdated runbooks.
- **L3 Engineering** is paged to inspect Git commit history and blame lines from scratch.

**TriagePilot™** acts as an autonomous initial analyst and evidentiary bridge. It cross-examines customer claims against operational logs, pinned Git source code, ledger snapshots, visual error screenshots, and runbooks—verifying every citation deterministically in Python before synthesizing a root-cause verdict, customer-safe response, and engineering bug draft.

### Key Architectural Differentiators
1. **True Live Repository & Telemetry Connectors (`engine/adapters/live_adapter.py`):** Dynamically syncs developer edits in [`transfers-demo-app/app/`](transfers-demo-app/app) into an isolated Git mirror, executes live payment requests without server restarts, emits structured JSONL logs + masked ledger records, and verifies exact modified line numbers and 40-character Git SHAs.
2. **Google ADK `ParallelAgent` Specialist Swarm (`engine/adk_orchestration.py`):** Orchestrates 5 domain specialists (`HistoryAgent`, `KnowledgeAgent`, `LogsAgent`, `CodeAgent`, `RecordAgent`) wrapped in a shared 12-call `ToolBudget`.
3. **Google A2A (Agent2Agent) Protocol v0.2 (`api/a2a.py`):** Publishes a standards-compliant Agent Card at `GET /.well-known/agent.json` and accepts JSON-RPC 2.0 task delegations at `POST /a2a` (`tasks/send`, `tasks/get`).
4. **Zero-Hallucination Python Verifier & Mathematical Trust Gate (`engine/verifier.py`, `engine/trust.py`):** Drops any unverified model citation and computes a deterministic Trust Score $T \in [0, 1]$, triggering **Principled Abstention** when $T < 0.45$.

---

## 🖥️ Triage Command Center UI

```text
+----------------------------------------------------------------------------------------------------------------------------+
|  🧭 TriagePilot™ v1.0 ENTERPRISE   [Triage Command Center]  [Quality & Ablation]  [Architecture & Integration]  [SHA-256]  |
+----------------------------------------------------------------------------------------------------------------------------+
|  10-STAGE VERIFIABLE PIPELINE: [✓ 01 PII Mask] [✓ 02 Flash Router] ... [✓ 06 Pro Hypotheses] ... [10 Maker-Checker]        |
+------------------------------------+-------------------------------------------+-------------------------------------------+
|  COLUMN 1: INCIDENT INGESTION      |  COLUMN 2: SWARM, 4-WAY MATRIX & STREAM   |  COLUMN 3: TRUST, VERDICT & PROOF BOARD   |
|  • Mode: [Queue] [Live] [+ Custom] |  • Runtime Provenance (Vertex AI Calls)   |  • Mathematical Trust Score:              |
|  • Live Service & Git Bridge:      |  • ADK 5-Agent Dynamic Router Bar         |    0.77 HIGH BAND | POLICY: CONCLUDE      |
|    - Target Repo @ 288c17a / Diff  |    [History] [Knowledge] [Logs] [Code]    |  • Verified Root-Cause Verdict:           |
|    - Trigger Live Payment Request  |    ⚡ PRUNED: RecordAgent                 |    app/transfers/cutoff.py @ 142e868d     |
|  • Raw Customer Ticket Composer    |  • 4-Way Reality Cross-Examination Matrix |  • Sortable & Filterable Evidence Board:  |
|  • Pre-LLM Gate Preview            |    1. Client Claim   2. Logs & Ledger     |    [All] [Root-Cause] [Supports] [Dropped]|
|  • Attached UI Screenshot (Vision) |    3. Pinned Git AST 4. Runbooks & History|    [All Sources] [Code] [Log] [Doc] [Vis] |
|  • [▶ Run Autonomous Triage]       |  • Execution Trace Stream (Filterable)    |  • Output Drafts:                         |
|  • [🔗 Delegate via Google A2A]    |  • Maker-Checker Gate / Steer / Follow-Up |    [Customer Reply] [Jira Bug Draft]      |
+------------------------------------+-------------------------------------------+-------------------------------------------+
```

---

## 📖 How to Use TriagePilot™

### 1. Using the Web Command Center

1. **Open the Command Center:**
   - Visit **[https://triagepilot-ywgad5nv3a-uc.a.run.app](https://triagepilot-ywgad5nv3a-uc.a.run.app)** (or `http://localhost:8080` when running locally).
   - Check the top-right status bar to confirm live backend readiness (`Vertex AI • Gemini 2.5`, `Firestore Native`, `ADK • A2A v0.2`, and `SHA-256 Ledger` block count).
2. **Ingest an Incident Ticket (Column 1):**
   - **Option A — Ingested Queue (`Queue (8)`):**
     - Filter tickets using the search box or sort via the dropdown (`Sort: #1 → #8`, `Sort: P1 → P4`, `Sort: Class`).
     - Select any ticket (`#1 · TCK-1001` through `#8 · TCK-1111`) to load its raw customer text, metadata, and any attached screenshot (e.g., `#5 · TCK-6006` includes `screenshot.png` for Gemini 2.5 Flash Vision OCR).
   - **Option B — Live Service & Git Telemetry Bridge (`Live Service`):**
     - Edit any Python module in [`transfers-demo-app/app/`](transfers-demo-app/app) (for example, introduce a fee multiplier bug in `app/fees/calculator.py`) and click **`Sync Repo`**.
     - The bridge immediately detects **`LIVE CODE DIFF DETECTED`** and commits your change to the isolated live Git mirror with a genuine 40-character SHA.
     - Click **`Trigger Live Payment Request & Populate Ticket`** (or manually write your own customer issue in the text area) and click **`Run Autonomous Triage (LIVE)`**.
   - **Option C — Direct Custom Ticket (`+ Custom`):**
     - Click **`+ Custom`**, select the target service module (`transfers`, `fees`, `notifications`, `limits`, `settlement`), and paste any custom incident description or transaction reference (`TXN-*`, `BATCH-*`).
   - Review the **Pre-LLM Gate Preview** box to see which PII tokens and prompt-injection patterns will be scrubbed in Stage 01.
   - Click **`Run Autonomous Triage`** or **`Delegate via Google A2A Protocol (tasks/send)`**.
3. **Monitor Live Execution & 4-Way Cross-Examination (Column 2):**
   - Watch the **10-Stage Verifiable Triage Pipeline** bar progress from `01 PII Mask` to `09 SHA-256 Ledger`.
   - Inspect the **Runtime Execution Provenance** card showing each live Gemini call (`ticket_classification`, `multimodal_vision_extraction`, `hypothesis_reconciliation`, `report_synthesis`) with model name and latency in milliseconds.
   - Review the **4-Way Reality Cross-Examination Matrix** comparing `1. Client Claim`, `2. Logs & Ledger State`, `3. Pinned Git AST`, and `4. Runbooks & History`.
4. **Inspect Verified Proofs & Trust Breakdown (Column 3):**
   - Click **`Inspect Trust Formula Breakdown`** inside the **Evidentiary Trust Score** card to view the exact positive weights ($c_{\text{ver}}, c_{\text{div}}, c_{\text{spec}}, c_{\text{time}}$) and penalties ($p_{\text{contra}}, p_{\text{unver}}$).
   - Filter the **Verified Evidentiary Cards** board by stance (`All`, `Root-Cause`, `Supports`, `Contradicts`, `Dropped`) or by source (`code`, `log`, `doc`, `record`, `visual`, `ticket`).
   - Click any evidence card (`Inspect Proof`) to open the **Proof Inspector Modal**, showing the exact Git commit SHA, line numbers, snippet, or multimodal screenshot image.
5. **Execute Pilot-in-the-Middle & Maker-Checker Actions (Bottom of Column 2):**
   - **Maker-Checker Gate:** Click **`Approve & Commit Write-Back (Jira + Reply)`** (or **`Edit Drafts`** first) to cryptographically bind your approval to `report_revision` and `report_hash` and persist the issue via `LiveWriteAdapter`.
   - **Engineer Steer:** Switch to the **`Engineer Steer`** tab to inject domain guidance and re-run the investigation.
   - **Client Follow-Up (Turn-2 Resume):** On underspecified tickets like `#8 · TCK-1111` (`ABSTAIN`), the **`Client Follow-Up`** tab activates automatically. Click **`Ingest Client Clarification & Resume Triage`** to supply the missing transaction ID/timestamp and watch trust jump from `0.22 LOW` (`ABSTAIN`) to `HIGH` (`CONCLUDE`).

---

### 2. Using the REST, SSE & Google A2A APIs Directly

```bash
# 1. Check service health, Live Connectors & Google A2A Agent Card
curl -fsS http://localhost:8080/readyz
curl -fsS http://localhost:8080/api/connectors/status
curl -fsS http://localhost:8080/.well-known/agent.json

# 2. Trigger a live transaction against transfers-demo-app & sync live Git edits
curl -fsS -X POST http://localhost:8080/api/live/trigger \
  -H "Content-Type: application/json" \
  -d '{"amount": 10000, "tier": "standard", "transfer_type": "same_day"}'

# 3. Launch a LIVE or preset investigation
curl -fsS -X POST "http://localhost:8080/api/investigations?wait=true" \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "LIVE", "text": "Customer charged 4x fee on standard transfer", "mode": "live"}'

# 4. Delegate an incident investigation via Google A2A Protocol (JSON-RPC 2.0)
curl -fsS -X POST http://localhost:8080/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "req-1",
    "method": "tasks/send",
    "params": {
      "id": "a2a-demo-01",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Same-day transfer TXN-1009 rejected at 16:02 IST with CUTOFF_EXCEEDED"}],
        "metadata": {"scenario_id": "S01"}
      }
    }
  }'

# 5. Verify the SHA-256 hash-chained audit ledger
curl -fsS http://localhost:8080/api/audit/verify
```

---

## 🏛️ System Architecture

TriagePilot™ uses a **Hexagonal Architecture (Ports and Adapters)** in [`engine/ports/base.py`](engine/ports/base.py), orchestrated by **Google ADK** ([`engine/adk_orchestration.py`](engine/adk_orchestration.py)) and exposed via the **Google A2A Protocol** ([`api/a2a.py`](api/a2a.py)).

```mermaid
flowchart TD
    subgraph Ingestion ["1. INGESTION, A2A PROTOCOL & PRE-LLM GUARDRAILS"]
        TKT[("Customer Ticket / Live Service / A2A Task")] --> PII["Deterministic PII Scrubber (masking.py)<br/>Masks Accounts, PAN, IFSC, Phone, Email, Aadhaar"]
        PII --> GUARD["Prompt-Injection Quarantine<br/>Neutralizes Untrusted Instruction Overrides"]
    end

    subgraph Core ["2. INTELLIGENT ROUTING & GOOGLE ADK 5-AGENT SWARM"]
        GUARD --> ROUTER["Dynamic Planner (planner.py • Gemini 2.5 Flash)<br/>Classifies Ticket, Enforces 12-Call Tool Budget & Prunes Agents"]
        ROUTER --> ADK["TriagePilotSpecialistSwarm (Google ADK ParallelAgent)"]
        ADK --> S1["HistoryAgent → LiveGitHistoryAdapter"]
        ADK --> S2["KnowledgeAgent → KnowledgePort + Vision OCR"]
        ADK --> S3["LogsAgent → LiveLogAdapter (JSONL)"]
        ADK --> S4["CodeAgent → LiveGitCodeAdapter (Pinned Git SHA & Diffs)"]
        ADK --> S5["RecordAgent → LiveRecordAdapter (Masked Snapshots)"]
    end

    subgraph VerifierEngine ["3. DETERMINISTIC VERIFICATION & 4-WAY RECONCILIATION"]
        S1 & S2 & S3 & S4 & S5 --> VERIFIER["Deterministic Python Verifier (verifier.py)<br/>Validates Commit SHAs, Line Ranges, Log IDs & Visual Attachments"]
        VERIFIER --> RECONCILER["4-Way Reconciler (reconcile.py + Gemini 2.5 Pro)<br/>Flags TIME_MISMATCH, STALE_DOC_FLAG & BEHAVIOUR_MISMATCH"]
        RECONCILER --> TRUST["Mathematical Trust Engine (trust.py)<br/>T = clamp(0.40*c_ver + 0.25*c_div + 0.20*c_spec + 0.15*c_time - 0.30*p_contra - 0.20*p_unver)"]
    end

    subgraph HumanGate ["4. REPORT SYNTHESIS, LEAKCHECK & MAKER-CHECKER"]
        TRUST --> POLICY{"Policy Gate (policy.py)<br/>HIGH >= 0.70: CONCLUDE<br/>LOW < 0.45: ABSTAIN"}
        POLICY --> DRAFT["Report Builder (report_agent.py • Gemini 2.5 Flash)<br/>+ Post-Synthesis PII Mask & LeakCheck (leakcheck.py)"]
        DRAFT --> GATE["Revision-Bound Maker-Checker Gate<br/>Binds Approval to report_revision, report_hash & decision_id"]
        GATE --> WRITE["LiveWriteAdapter (GitHub Issues REST API & Local Issue Ledger)"]
    end

    subgraph AuditLog ["5. CRYPTOGRAPHIC AUDITABILITY"]
        Ingestion -.-> AUDIT["Firestore SHA-256 Hash-Chained Audit Ledger (audit.py)"]
        Core -.-> AUDIT
        VerifierEngine -.-> AUDIT
        HumanGate -.-> AUDIT
    end
```

---

## 🎯 Verified Incident Scenarios (`#1` → `#8` + `LIVE`)

| # | Ticket ID | Scenario | Severity | Class | Key Verification & Defense Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LIVE** | `LIVE-*` | **Live Service & Git Bridge (`transfers-demo-app`)** | `Dynamic` | `Dynamic` | Syncs live IDE edits in `transfers-demo-app/app/`, verifies new 40-char Git SHA, diff line numbers, live JSONL logs & masked records |
| **#1** | `TCK-1001` | **S01:** Same-day transfers rejected after 4 PM IST | `P1` | `CODE_DEFECT` | Flags `TIME_MISMATCH`; pins UTC vs IST bug in `app/transfers/cutoff.py` |
| **#2** | `TCK-2041` | **S02:** Fee off by 0.01 on transfer `TXN-2041` | `P2` | `DATA_ISSUE` | Cross-checks `RecordPort` snapshot with float rounding in `app/fees/calculator.py` |
| **#3** | `TCK-3003` | **S03:** Duplicate debit + Prompt Injection Guard | `P1` | `CODE_DEFECT` | Quarantines ticket prompt injection; identifies missing check in `idempotency.py` |
| **#4** | `TCK-4004` | **S04:** Beneficiary SMS never sent + Stale Runbook | `P2` | `CODE_DEFECT` | Quarantines log injection; flags `STALE_DOC_FLAG` & `BEHAVIOUR_MISMATCH` on `DOC-SMS-01` |
| **#5** | `TCK-6006` | **S06:** Transfer blocked at ₹1,00,000 + Vision OCR | `P2` | `CODE_DEFECT` | Live Gemini 2.5 Flash Vision OCR on `screenshot.png`; pins `>=` bug in `daily_limit.py` |
| **#6** | `TCK-9009` | **S09:** Bank-holiday NEFT settlement delay (`KE-104`) | `P3` | `KNOWN_ERROR` | Fast-path match on `KE-104`; prunes `CodeAgent` and `RecordAgent` |
| **#7** | `TCK-1010` | **S10:** How to add an international beneficiary | `P4` | `HOW_TO_USER_ERROR` | Activates only `KnowledgeAgent` (`DOC-BEN-02`); prunes 4 unnecessary specialists |
| **#8** | `TCK-1111` | **S11:** Underspecified ticket → Abstain → Turn-2 Resume | `P2` | `INSUFFICIENT_INFO` | Turn 1 abstains (`Trust: 0.22`); Turn-2 client clarification resolves `cutoff.py` |

---

## 🚀 Local Setup, Testing & Cloud Run Deployment

### 1. Local Python + Vite Setup
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Build the React frontend bundle
cd ui && npm install && npm run build && cd ..

# 3. Start the unified FastAPI + Static UI server on port 8080
python -m uvicorn api.main:app --host 0.0.0.0 --port 8080
```
Or use the convenience scripts:
```powershell
# Windows PowerShell
.\scripts\run_local.ps1

# Linux / macOS
./scripts/run_local.sh
```

### 2. Run the Test & Benchmark Suites
```bash
# Run all 197 backend unit, ADK/A2A, Live Connector & integration tests
pytest -q

# Run the 8-scenario automated evaluation benchmark
python scripts/run_eval.py

# Verify Python bytecode compilation
python -m compileall -q engine api eval
```

### 3. Deploy to Google Cloud Run
```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/deploy_cloudrun.ps1 -ProjectId triagepilot-dev -Region us-central1

# Linux / macOS
GCP_PROJECT_ID=triagepilot-dev ./scripts/deploy_cloudrun.sh
```
