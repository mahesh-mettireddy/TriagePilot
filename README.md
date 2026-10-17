# TriagePilot™ — Autonomous Incident Analyst & Verifiable Evidentiary Bridge

> *"Every conclusion ships with proof, or it doesn't ship."*

[![Live Cloud Run Service](https://img.shields.io/badge/Live%20Platform-Cloud%20Run%20Active-success?style=for-the-badge&logo=googlecloud)](https://triagepilot-ywgad5nv3a-uc.a.run.app)
[![Live Benchmark](https://img.shields.io/badge/Live%20Vertex%20AI%20Eval-8%2F8%20Passed%20(100%25)-10b981?style=for-the-badge&logo=googlecloud)](https://triagepilot-ywgad5nv3a-uc.a.run.app)
[![Verification Suite](https://img.shields.io/badge/Pytest%20Suite-205%20Passing-emerald?style=for-the-badge&logo=pytest)](eval/tests/)
[![AI Core](https://img.shields.io/badge/Vertex%20AI-Gemini%202.5%20Pro%20%2B%20Flash%20%2B%20Vision-4285F4?style=for-the-badge&logo=googlecloud)](engine/)
[![Agent Interop](https://img.shields.io/badge/Multi--Agent-Google%20ADK%20%2B%20A2A%20v0.2-teal?style=for-the-badge&logo=google)](api/a2a.py)
[![Audit Integrity](https://img.shields.io/badge/Audit%20Ledger-SHA--256%20Hash%20Chain-teal?style=for-the-badge)](https://triagepilot-ywgad5nv3a-uc.a.run.app/api/audit/verify)

- **Live Production URL (Google Cloud Run):** [https://triagepilot-ywgad5nv3a-uc.a.run.app](https://triagepilot-ywgad5nv3a-uc.a.run.app)
- **Production Readiness, Codeflow & 3-Minute Pitch Playbook:** [`READINESS.md`](READINESS.md)
- **Interactive 3-Minute Demo Script:** [`DEMO_WALKTHROUGH.md`](DEMO_WALKTHROUGH.md)
- **Full Architecture & Technical Specification:** [`ARCHITECTURE_AND_SPEC.md`](ARCHITECTURE_AND_SPEC.md)
- **Google A2A Agent Card (`v0.2`):** [`GET /.well-known/agent.json`](https://triagepilot-ywgad5nv3a-uc.a.run.app/.well-known/agent.json)

---

## 📌 Problem & Solution Overview

In enterprise software and financial infrastructure, production incident response gets trapped in the **L1 → L2 → L3 escalation waterfall**:
- **L1 Support** receives ambiguous customer tickets (*"transfers failing!"*) and escalates without technical context.
- **L2 Operations** manually correlates distributed logs, transaction ledgers, and often-outdated runbooks.
- **L3 Engineering** is paged to inspect Git commit history and blame lines from scratch.

Standard LLM chatbots fail in production support because they hallucinate file paths, confuse mere pointer existence with causal proof, trust stale documentation over actual code, and fall victim to adversarial prompt injections hidden inside tickets or application logs.

**TriagePilot™** moves from *plausible diagnosis to a defensible next decision*. It cross-examines customer claims against operational logs, pinned Git source code, masked ledger snapshots, visual error screenshots, and domain runbooks—**verifying every citation deterministically in Python and grading its evidentiary truth level** before selecting an allowlisted next check, synthesizing a root-cause verdict, and gating write-back behind revision-bound human approval.

### 🏆 Key Architectural Innovations
1. **True Live Repository, In-Browser Live Code Studio & Auto-Probe Telemetry ([`engine/adapters/live_adapter.py`](engine/adapters/live_adapter.py)):** Lets developers edit [`transfers-demo-app/app/`](transfers-demo-app/app) in the **Live Code Studio** (or IDE), commits into an isolated Git mirror (`data/live/clientrepo`) with a real 40-char SHA, automatically runs a live probe transaction, emits structured JSONL logs + PII-masked ledger records, and verifies `[LIVE GIT FIX VERIFIED]` (`CHK-LIVE-FIX-VERIFIED`) when a fix resolves the runtime bug.
2. **Google ADK `ParallelAgent` Topology & Deterministic Parallel Specialist Runner ([`engine/adk_orchestration.py`](engine/adk_orchestration.py)):** Registers 5 domain specialists (`HistoryAgent`, `KnowledgeAgent`, `LogsAgent`, `CodeAgent`, `RecordAgent`) under a Google ADK `ParallelAgent` topology (`TriagePilotSpecialistSwarm`) wrapped in a shared 12-call `ToolBudget`, dynamically pruning unnecessary specialists per ticket class and executing active specialists concurrently via the deterministic Python runner (`asyncio.gather`) so every tool call is strictly budgeted and auditable.
3. **Google A2A (Agent2Agent) Protocol v0.2 ([`api/a2a.py`](api/a2a.py)):** Publishes a standards-compliant Agent Card at `GET /.well-known/agent.json` and accepts JSON-RPC 2.0 task delegations at `POST /a2a` (`tasks/send`, `tasks/get`), returning verified evidence artifacts.
4. **Three-Tier Evidentiary Truth Labels & Provenance-Deduplicated Trust Gate ([`engine/verifier.py`](engine/verifier.py), [`engine/trust.py`](engine/trust.py)):** Drops any unverified model citation on the spot, classifies every verified card into **`SOURCE_VALIDATED`**, **`CLAIM_SUPPORTED`**, or **`CAUSE_REPRODUCED`** (with explicit `limitations`), deduplicates identical source pointers by `provenance_key`, and enforces 4 hard conclusion gates (`REPRODUCED_IN_FIXTURE`, `SUPPORTED_HYPOTHESIS`, `NEED_EVIDENCE`, `BLOCKED`) with **Principled Abstention** when $T < 0.45$.
5. **Interactive Multi-Turn HITL Loop, Allowlisted Next Check & Contradictory Evidence Withdrawal ([`engine/next_check.py`](engine/next_check.py), [`engine/orchestrator.py`](engine/orchestrator.py)):** Supports natural-language **`DEV_STEER`** (`CHK-STEER-DIRECTIVE-VERIFIED`), **`CLIENT_REPLY`** (resuming abstained investigations), and **`EVIDENCE_UPDATE`** (withdrawing superseded conclusions via `WithdrawnConclusion`, incrementing `report_revision`, invalidating stale approvals, and sealing every transition in a **Firestore SHA-256 hash chain**).

---

## 📊 Verified Live Vertex AI Benchmark & Runnable Ablation Scorecard

All 8 Golden Scenarios (`5 DEV / 3 TEST`) plus the Live Target Service (`LIVE`) execute end-to-end against live **Vertex AI (`gemini-2.5-flash` + `gemini-2.5-pro`)** on Google Cloud Run (`POST /api/eval/run?execution_mode=live_evaluation`), including a runnable head-to-head comparison against a **Single-Agent Baseline (`Arm B`)** (`eval/ablations.py`):

| Benchmark Metric | Single-Agent Baseline (`Arm B`) | TriagePilot™ Engine (`Arm C`) | Verification Method |
| :--- | :--- | :--- | :--- |
| **Root-Cause Hit Rate** | `50.0%` (`4 / 8`) | **100.0% (`8 / 8` Passed)** | Exact match against ground-truth culprit file & commit SHA (`+50.0%` lift) |
| **Ticket Classification Accuracy** | `75.0%` (`6 / 8`) | **100.0% (`8 / 8` Passed)** | `CODE_DEFECT`, `DATA_ISSUE`, `KNOWN_ERROR`, `HOW_TO_USER_ERROR`, `INSUFFICIENT_INFO` |
| **False Conclusion Rate** | `50.0%` (`S01, S04, S06, S11`) | **0.0%** | Zero incorrect conclusions ever marked `HIGH` trust |
| **Prompt Injection Defense Rate** | `0.0%` (`0 / 2` Blocked) | **100.0% (`2 / 2` Blocked)** | Quarantines both ticket injection (`S03`) and adversarial log injection (`S04`) |
| **Post-Verifier Citation Validity** | `37.5%` (`62.5%` Unverified) | **96.9% (`100%` of shipped claims)** | Unverified citations are deterministically dropped by `verifier.py` before synthesis |
| **Allowlisted Next-Check Coverage** | `0.0%` | **100.0% (`8 / 8` Scenarios)** | Deterministic `NextCheck` selected from closed allowlist in `engine/next_check.py` |
| **Principled Abstention & Revision** | `0.0%` (Guesses on `S11`) | **100.0% (`S11` + `EVIDENCE_UPDATE`)** | Abstains on `S11` (`0.22 LOW`); withdraws stale conclusions on `EVIDENCE_UPDATE` |
| **Token & Cost Telemetry** | Untracked | **Tracked per call (`~$0.008 / run`)** | Real `usage_metadata` token & USD cost accounting per Gemini Flash/Pro operation |

---

## 🖥️ Intuitive 3-Step Command Center UI

The web interface is designed as a streamlined, self-explanatory **3-Step Guided Workspace** so SREs, support analysts, and first-time reviewers can immediately see and feel the backend pipeline in action:

```text
+----------------------------------------------------------------------------------------------------------------------------+
|  🧭 TriagePilot™   [Investigate Incident]   [Evaluation & Benchmark]   [System Architecture]     [Vertex AI • ADK • A2A]  |
+----------------------------------------------------------------------------------------------------------------------------+
|  5-PHASE PIPELINE:  [✓ 1. Privacy Shield] ──► [✓ 2. Smart Router] ──► [✓ 3. Python Verifier] ──► [✓ 4. Trust] ──► [✓ 5. Gate]|
|  ⚡ LIVE ACTIVITY TICKER: Real-time SSE stream of active agent tool calls, verifications & Gemini 2.5 synthesis            |
+------------------------------------+-------------------------------------------+-------------------------------------------+
|  STEP 1: SELECT OR TRIGGER INCIDENT|  STEP 2: 4-WAY CROSS-EXAMINATION & TRACE  |  STEP 3: VERDICT, NEXT CHECK & PROOFS     |
|  • Source Mode:                    |  • 4-Way Reality Cross-Examination Matrix:|  • Withdrawn Conclusion Banner (if Rev>1) |
|    [Queue (8)] [Live App] [Custom] |    1. Client Claim   2. Logs & Ledger     |  • Verified Root-Cause Verdict (Rev #1):  |
|  • Live Demo App & Git Bridge:     |    3. Pinned Git AST 4. Runbooks & History|    CAUSE_REPRODUCED | daily_limit.py      |
|    - Sync Live Code Edits & Diff   |  • Backend Execution Inspector Tabs:      |  • Next Useful Check (Allowlisted):       |
|    - Run Live Payment & Ticket     |    [Agent Swarm] [Live Trace] [AI Calls]  |    CHK-INSPECT-BOUNDARY • LOW EFFORT      |
|  • Customer Ticket & Pre-LLM Gate  |  • 4-Tab Operator Controls:               |  • Evidentiary Trust Gate:                |
|    (Shows PII & Injection Scrub)   |    [Maker-Checker Gate] [Engineer Steer]  |    0.86 HIGH | GATE: REPRODUCED_IN_FIXTURE|
|  • [▶ Analyze Incident]            |    [Client Follow-Up]                     |  • Output Drafts & Verified Proof Cards:  |
|  • [🔗 Run via A2A Protocol]       |    [Contradictory Evidence (Withdraw)]    |    [CAUSE REPRODUCED] [CLAIM SUPPORTED]   |
+------------------------------------+-------------------------------------------+-------------------------------------------+
```

---

## 📖 Quick-Start Guide: Using TriagePilot™

### 1. Using the Live Web Command Center

1. **Open the Live Platform:**
   - Visit **[https://triagepilot-ywgad5nv3a-uc.a.run.app](https://triagepilot-ywgad5nv3a-uc.a.run.app)** (or `http://localhost:8080` locally).
   - The top bar confirms live backend readiness (`Vertex AI • Gemini 2.5`, `Firestore Native`, `ADK • A2A v0.2`, and `SHA-256 Ledger` block count).
2. **Step 1 — Select or Trigger an Incident (Left Column):**
   - **Queue (`#1` → `#8`):** Pick any of the 8 realistic fintech incidents (`S01` through `S11`) from the queue or 1-click signature scenario cards.
   - **Live App (`LIVE`):** Click **`Live App`**, edit any Python file in [`transfers-demo-app/app/`](transfers-demo-app/app) (or use the built-in payment simulator), click **`1. Run Live Payment & Generate Ticket`**, and click **`Analyze Incident (LIVE)`**. TriagePilot™ syncs the live Git repo, emits real JSONL logs and ledger records, and verifies the exact culpable file, line number, and commit SHA.
   - **Custom (`+ Custom`):** Paste any free-form incident description or transaction ID (`TXN-*`, `BATCH-*`).
   - Click **`Analyze Incident`** (or **`Run via A2A Protocol`** to run through the JSON-RPC 2.0 `tasks/send` endpoint).
3. **Step 2 — Watch Live 4-Way Cross-Examination & Operator Controls (Center Column):**
   - Watch the **Live Backend Activity Ticker** stream every specialist tool call (`HistoryAgent`, `KnowledgeAgent`, `LogsAgent`, `CodeAgent`, `RecordAgent`), deterministic verification result, and Gemini 2.5 Pro/Flash synthesis step in real time.
   - Compare **1. What Customer Claimed**, **2. What Logs & Ledger Show**, **3. What Git Code Actually Runs**, and **4. What Runbook & Docs Promise** side-by-side in the **4-Way Reality Cross-Check**, automatically highlighting contradictions (`TIME_MISMATCH`, `STALE_DOC_FLAG`, `BEHAVIOUR_MISMATCH`).
   - Use the **4-Tab Operator Controls** at the bottom of Step 2:
     - **`Maker-Checker Gate`**: Approve & commit write-back bound to `report_revision` and `report_hash`.
     - **`Engineer Steer`**: Steer specialists toward a specific file or commit (`DEV_STEER`).
     - **`Client Follow-Up`**: Ingest client clarification (`CLIENT_REPLY`) on abstained tickets (`S11`).
     - **`Contradictory Evidence`**: Ingest late-arriving contradictory telemetry (`EVIDENCE_UPDATE`) to watch TriagePilot™ withdraw its prior conclusion (`WithdrawnConclusion`), increment `report_revision`, and invalidate any prior approval on the superseded report.
4. **Step 3 — Inspect 3-Tier Proofs, Next Useful Check & Trust Gate (Right Column):**
   - Review the **Verified Root Cause** with its evidentiary tier badge (`CAUSE_REPRODUCED`, `CLAIM_SUPPORTED`, `SOURCE_VALIDATED`) and the allowlisted **Next Useful Check** card (`CHK-*`).
   - Expand **`Inspect Trust Formula Breakdown`** to see the deduplicated provenance count (`unique_provenance_count`), conclusion gate outcome (`REPRODUCED_IN_FIXTURE`, `SUPPORTED_HYPOTHESIS`, `NEED_EVIDENCE`, `BLOCKED`), and exact mathematical weights ($c_{\text{ver}}, c_{\text{div}}, c_{\text{spec}}, c_{\text{time}}, p_{\text{contra}}, p_{\text{unver}}$).
   - Click any card in **Verified Proof Citations** to open the **Proof Inspector Modal** showing its 3-tier `evidence_level`, `provenance_key`, `limitations`, Git commit SHA, line range, or multimodal Vision OCR screenshot.

---

### 2. Using the REST, SSE & Google A2A APIs Directly

```bash
# 1. Check service health, Live Connectors & Google A2A Agent Card
curl -fsS https://triagepilot-ywgad5nv3a-uc.a.run.app/readyz
curl -fsS https://triagepilot-ywgad5nv3a-uc.a.run.app/api/connectors/status
curl -fsS https://triagepilot-ywgad5nv3a-uc.a.run.app/.well-known/agent.json

# 2. Trigger a live transaction against transfers-demo-app & sync live Git edits
curl -fsS -X POST https://triagepilot-ywgad5nv3a-uc.a.run.app/api/live/trigger \
  -H "Content-Type: application/json" \
  -d '{"amount": 100000, "tier": "standard", "transfer_type": "same_day", "simulate_utc_hour": 11}'

# 3. Launch a LIVE or preset investigation
curl -fsS -X POST "https://triagepilot-ywgad5nv3a-uc.a.run.app/api/investigations?wait=true" \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "LIVE", "text": "Transfer of INR 100000 failed with DAILY_LIMIT_EXCEEDED", "mode": "live"}'

# 4. Delegate an incident investigation via Google A2A Protocol (JSON-RPC 2.0)
curl -fsS -X POST https://triagepilot-ywgad5nv3a-uc.a.run.app/a2a \
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

# 5. Inspect persisted engineering issues & verify the SHA-256 audit ledger
curl -fsS https://triagepilot-ywgad5nv3a-uc.a.run.app/api/live/issues
curl -fsS https://triagepilot-ywgad5nv3a-uc.a.run.app/api/audit/verify
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

    subgraph VerifierEngine ["3. 3-TIER VERIFICATION, 4-WAY RECONCILIATION & HARD TRUST GATES"]
        S1 & S2 & S3 & S4 & S5 --> VERIFIER["Deterministic Python Verifier (verifier.py)<br/>Grades SOURCE_VALIDATED, CLAIM_SUPPORTED & CAUSE_REPRODUCED"]
        VERIFIER --> RECONCILER["4-Way Reconciler (reconcile.py + Gemini 2.5 Pro)<br/>Flags TIME_MISMATCH, STALE_DOC_FLAG & BEHAVIOUR_MISMATCH"]
        RECONCILER --> TRUST["Provenance-Deduplicated Trust Engine (trust.py)<br/>T = clamp(c_ver + c_div + c_spec + c_time - p_contra - p_unver, 0, 1)"]
    end

    subgraph HumanGate ["4. ALLOWLISTED NEXT CHECK, SYNTHESIS & MAKER-CHECKER"]
        TRUST --> POLICY{"Hard Conclusion Gates (policy.py)<br/>HIGH >= 0.70 | MEDIUM 0.45..0.69 | LOW < 0.45"}
        POLICY --> NEXT["Next Useful Check Selector (next_check.py)<br/>+ Report Builder (report_agent.py) + LeakCheck (leakcheck.py)"]
        NEXT --> GATE["Revision-Bound Maker-Checker & Conclusion Withdrawal<br/>Binds Approval to report_revision, report_hash & decision_id"]
        GATE --> WRITE["LiveWriteAdapter (/api/live/issues & GitHub Issues REST API)"]
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

| # | Ticket ID | Scenario | Severity | Class | Matched Runbook / Proof | Key Verification & Defense Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **LIVE** | `LIVE-*` | **Live Service & Git Bridge (`transfers-demo-app`)** | `Dynamic` | `Dynamic` | `DOC-LIMITS-01` / `DOC-FEES-01` / `DOC-CUTOFF-01` | Syncs live IDE edits in `transfers-demo-app/app/`, verifies new 40-char Git SHA, diff line numbers, live JSONL logs & masked records |
| **#1** | `TCK-1001` | **S01:** Same-day transfers rejected after 4 PM IST | `P1` | `CODE_DEFECT` | `DOC-CUTOFF-01` | Flags `TIME_MISMATCH`; pins UTC vs IST bug in `app/transfers/cutoff.py` (`CAUSE_REPRODUCED`) |
| **#2** | `TCK-2041` | **S02:** Fee off by 0.01 on transfer `TXN-2041` | `P2` | `DATA_ISSUE` | `DOC-FEES-01` | Cross-checks `RecordPort` snapshot with float rounding in `app/fees/calculator.py` (`CAUSE_REPRODUCED`) |
| **#3** | `TCK-3003` | **S03:** Duplicate debit + Prompt Injection Guard | `P1` | `CODE_DEFECT` | `DOC-IDEMPOTENCY-01` | Quarantines ticket prompt injection; identifies missing check in `idempotency.py` (`CAUSE_REPRODUCED`) |
| **#4** | `TCK-4004` | **S04:** Beneficiary SMS never sent + Stale Runbook | `P2` | `CODE_DEFECT` | `DOC-SMS-01` | Quarantines log injection; flags `STALE_DOC_FLAG` & `BEHAVIOUR_MISMATCH` on `DOC-SMS-01` |
| **#5** | `TCK-6006` | **S06:** Transfer blocked at ₹1,00,000 + Vision OCR | `P2` | `CODE_DEFECT` | `DOC-LIMITS-01` | Live Gemini 2.5 Flash Vision OCR on `screenshot.png`; rejects innocent `httpx` commit & pins `>=` bug in `daily_limit.py` |
| **#6** | `TCK-9009` | **S09:** Bank-holiday NEFT settlement delay (`KE-104`) | `P3` | `KNOWN_ERROR` | `KE-104` | Fast-path match on `KE-104`; prunes `CodeAgent` and `RecordAgent` |
| **#7** | `TCK-1010` | **S10:** How to add an international beneficiary | `P4` | `HOW_TO_USER_ERROR` | `DOC-BEN-02` | Activates only `KnowledgeAgent` (`DOC-BEN-02`); prunes 4 unnecessary specialists |
| **#8** | `TCK-1111` | **S11:** Underspecified ticket → Abstain → Turn-2 Resume | `P2` | `INSUFFICIENT_INFO` | Turn 2 → `DOC-CUTOFF-01` | Turn 1 abstains (`Trust: 0.22`); Turn-2 client clarification resolves `cutoff.py` |

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
# Run all 205 backend unit, adversarial judge, ADK/A2A, Live Connector & integration tests
pytest -q

# Run the 8-scenario automated evaluation & Single-Agent vs TriagePilot ablation benchmark
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
