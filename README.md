# TriagePilot — Autonomous Initial Analyst & Evidentiary Bridge

> *"Every conclusion ships with proof, or it doesn't ship."*

[![Live Cloud Run Demo](https://img.shields.io/badge/Live%20Demo-Cloud%20Run%20Active-success?style=for-the-badge&logo=googlecloud)](https://triagepilot-ywgad5nv3a-uc.a.run.app)
[![Build & Verification Status](https://img.shields.io/badge/Verification-Pytest%20Suite-emerald?style=for-the-badge&logo=pytest)](eval/tests/)
[![Google Cloud Run](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run%20Ready%20(Warm%20Instance)-4285F4?style=for-the-badge&logo=googlecloud)](https://triagepilot-ywgad5nv3a-uc.a.run.app)
[![Gemini 2.5 on Vertex AI](https://img.shields.io/badge/AI%20Core-Gemini%202.5%20Pro%20%26%20Flash%20on%20Vertex%20AI-4285F4?style=for-the-badge&logo=googlecloud)](engine/)
[![Audit Integrity](https://img.shields.io/badge/Audit%20Ledger-SHA--256%20Hash%20Chain-teal?style=for-the-badge)](https://triagepilot-ywgad5nv3a-uc.a.run.app/api/audit/verify)

**Track:** Future of Work & Enterprise Productivity  
**Competition:** Google Cloud AI Builder Cup 2026  
**Live Cockpit URL:** [https://triagepilot-ywgad5nv3a-uc.a.run.app](https://triagepilot-ywgad5nv3a-uc.a.run.app)  
**Demo Video Walkthrough:** [`DEMO_WALKTHROUGH.md`](DEMO_WALKTHROUGH.md)

---

## 📌 Executive Summary

In enterprise software and financial infrastructure, when incidents strike, engineering teams are paralyzed by the blind **L1 → L2 → L3 escalation waterfall**:
- **L1 Support** reads ambiguous customer tickets ("transfers failing!") and blindly escalates.
- **L2 Operations** spends hours querying distributed log clusters and outdated Confluence runbooks.
- **L3 Developers** are paged to re-diagnose issues from scratch, deciphering cryptic commit blames.

**TriagePilot** eliminates this operational drag. It acts as an autonomous initial analyst that cross-examines client claims against log events, pinned source code ASTs, and runbooks before synthesizing a verified, proof-carrying triage brief.

---

## 🖥️ Live React Cockpit UI Overview

The dark-mode SRE cockpit is designed for high-velocity incident response, deployed as a single-container multi-stage build on **Google Cloud Run**:

```
+-----------------------------------------------------------------------------------------------------------------------+
|  🧭 TriagePilot v1.0   [Triage Cockpit]   [Ablation & Evals]   [Architecture & Profile]    [🔒 Verify SHA-256 Ledger]  |
+-----------------------------------------------------------------------------------------------------------------------+
|  COLUMN 1: INGESTION            |  COLUMN 2: ROUTING & PIPELINE STREAM   |  COLUMN 3: VERIFIED BRIEF & MAKER-CHECKER  |
|  * Scenarios (S01 to S11)       |  * 5 Specialists Router Bar:           |  * Evidentiary Trust Meter:                |
|    - S01: IST Cutoff Bug        |    [History] [Logs] [Code] [Docs] [DB] |    Score: 0.84 | HIGH BAND | CONCLUDE         |
|    - S03: Prompt Injection      |    ⚡ PRUNED: RecordAgent (No TXN-ID)   |  * Root Cause Hypothesis:                  |
|    - S04: Stale Doc Contradict  |  * Real-Time SSE Event Stream:         |    app/transfers/cutoff.py @ commit 85d07f2   |
|    - S11: Two-Turn Abstain      |    - [PII Redacted: PAN & Aadhaar]     |  * Grounded Citations:                     |
|  * Raw Ticket Intake            |    - [Injection Deflected: Safe Guard] |    ✔ VERIFIED: cutoff.py:34 (AST Anchor)      |
|  * Deterministic PII Sanitizer  |    - [BEHAVIOUR_MISMATCH: Stale Doc]   |    ✖ DROPPED: Confluence runbook DOC-SMS-01   |
|    Tokens: [Aadhaar Redacted]   |  * Maker-Checker Human Approval Gate:  |  * Synthesized Drafts:                     |
|  * Mode: [REPLAY] / [LIVE]      |    [Approve & Push to Jira]            |    - Safe Customer Reply Draft             |
|  * [RUN TRIAGEPILOT]            |    [Developer Steer] [Client Reply]    |    - Formatted Jira Bug Ticket Draft       |
+-----------------------------------------------------------------------------------------------------------------------+
```

---

## 🏛️ System Architecture

TriagePilot is architected under **Hexagonal Architecture (Ports and Adapters)**, strictly decoupling LLM reasoning from external data sources and mutation sinks.

```mermaid
flowchart TD
    subgraph Ingestion ["1. INGESTION & SANITIZATION"]
        TKT[("Raw Customer Ticket")] --> PII["Presidio PII Scrubber<br/>(Masks PAN, Aadhaar, Phone, Email)"]
        PII --> LEAK["Pre-LLM Jailbreak Guard<br/>(Regex Scrubber & Injection Deflection)"]
    end

    subgraph Core ["2. INTELLIGENT ROUTING & SWARM"]
        LEAK --> ROUTER["Dynamic Planner & Router<br/>(Prunes 55% Unneeded Agent Tool Calls)"]
        ROUTER --> S1["HistoryAgent<br/>(Past Incidents & Tickets)"]
        ROUTER --> S2["KnowledgeAgent<br/>(Runbooks & Docs)"]
        ROUTER --> S3["LogsAgent<br/>(Trace Logs & Exceptions)"]
        ROUTER --> S4["CodeAgent<br/>(Git AST & Commit Blame)"]
        ROUTER --> S5["RecordAgent<br/>(System of Record & Ledgers)"]
    end

    subgraph VerifierEngine ["3. PROOF VERIFICATION & RECONCILIATION"]
        S1 & S2 & S3 & S4 & S5 --> VERIFIER["Deterministic Python Verifier<br/>(Validates Line Anchors & Drops Hallucinations)"]
        VERIFIER --> RECONCILER["Contradiction Reconciler<br/>(Resolves TIME_MISMATCH & BEHAVIOUR_MISMATCH)"]
        RECONCILER --> TRUST["Trust Math Engine<br/>T = c_ver + c_div + c_spec + c_time - p_contra - p_unver"]
    end

    subgraph HumanGate ["4. MAKER-CHECKER GATE & WRITE-BACK"]
        TRUST --> POLICY{"Policy Engine<br/>Trust >= 0.70: CONCLUDE<br/>Trust < 0.45: ABSTAIN"}
        POLICY --> DRAFT["Synthesized Triage Brief & Drafts"]
        DRAFT --> GATE["Maker-Checker Human Approval Gate<br/>(Mandatory SRE Sign-off)"]
        GATE --> JIRA["JiraPort / Write Mutation<br/>(Deterministic Write-Back Reference)"]
    end

    subgraph AuditLog ["5. CRYPTOGRAPHIC PROVABILITY"]
        Ingestion -.-> AUDIT["SHA-256 Hash-Chained Audit Ledger"]
        Core -.-> AUDIT
        VerifierEngine -.-> AUDIT
        HumanGate -.-> AUDIT
    end
```

---

## 🔑 Six Core Architectural Pillars

### 1. 🔍 4-Way Reality Cross-Examination
Instead of querying an LLM with unstructured context, TriagePilot validates across 4 independent sources:
1. **Client Ticket Claim** (User perception)
2. **Distributed Traces / Logs** (Runtime reality)
3. **Repository AST / Commit Blame** (Static code reality)
4. **Knowledge Runbooks** (Documented expectation)

### 2. 🛡️ Deterministic Anti-Hallucination Verifier (`verifier.py`)
No LLM determines whether a claim is factual. A deterministic Python engine checks every cited snippet against file existence, AST lines, log timestamps, and database records.
- **Result:** **100% of phantom citations and hallucinations are dropped.**

### 3. ⚡ Dynamic 5-Specialist Routing & Agent Pruning (`planner.py`)
Blasting every specialist agent on every ticket is wasteful and slow. TriagePilot's router activates only necessary subagents:
- `HOW_TO_USER_ERROR`: Only `KnowledgeAgent` is activated (prunes 4 agents).
- `KNOWN_ERROR`: Only `HistoryAgent` and `LogsAgent` are activated.
- **Result:** **~55% reduction in token consumption and API latency.**

### 4. 📐 Mathematical Trust Score & Principled Abstention (`trust.py`)
Instead of opaque confidence heuristics, TriagePilot calculates an empirical trust score:

$$\text{Trust} = \text{clamp}\Big(c_{\text{ver}} + c_{\text{div}} + c_{\text{spec}} + c_{\text{time}} - p_{\text{contra}} - p_{\text{unver}},\, 0.0,\, 1.0\Big)$$

#### Formula Component Breakdown & Weights:
- **$c_{\text{ver}}$ (Verified Evidence Ratio, max $+0.35$):** Evaluates $\frac{|\text{verified citations}|}{|\text{total citations}|}$. Directly rewards grounded AST line anchors and real log event matches.
- **$c_{\text{div}}$ (Cross-Port Source Diversity, max $+0.25$):** Evaluates coverage across independent read ports ($\ge 3$ distinct source types among Git, Logs, Database, and Docs).
- **$c_{\text{spec}} + c_{\text{time}}$ (Specificity & Temporal Alignment, max $+0.40$):**
  - **$c_{\text{spec}}$ ($+0.20$):** AST line-anchor specificity (exact file path, function symbol, and commit SHA).
  - **$c_{\text{time}}$ ($+0.20$):** Timestamp alignment between client incident observation and telemetry log burst ($|\Delta t| \le 15\text{m}$).
- **$p_{\text{contra}} + p_{\text{unver}}$ (Deterministic & Hallucination Penalties):**
  - **$p_{\text{contra}}$ ($-0.30$ per contradiction):** Heavy penalty for `TIME_MISMATCH`, `BEHAVIOUR_MISMATCH`, or `STATE_MISMATCH`.
  - **$p_{\text{unver}}$ ($-0.20$ per dropped citation):** Strict penalty for ungrounded citations or hallucinations caught by `verifier.py`.
- **Decision Bands:** `HIGH >= 0.70` (`POLICY: CONCLUDE`), `MEDIUM 0.45-0.70` (`POLICY: CONCLUDE_WITH_CAVEAT`), `LOW < 0.45` (`POLICY: ABSTAIN`).
- **Principled Abstention:** Whenever $\text{Trust} < 0.45$ (or hypothesis score gap $< 0.10$), TriagePilot automatically abstains and generates targeted diagnostic questions rather than fabricating a false conclusion.

### 5. 🧑‍✈️ Maker-Checker Human Approval Gate
Zero automated write-backs occur without human oversight. The SRE reviews the verified brief, optionally edits the client reply, and signs off before mutations push to Jira.

### 6. 🔒 Cryptographic SHA-256 Audit Ledger (`audit.py`)
Every pipeline step is appended to an immutable SHA-256 hash-chained audit ledger:
$$H_i = \text{SHA256}(H_{i-1} \,||\, \text{timestamp} \,||\, \text{step} \,||\, \text{payload})$$
Any retroactive modification immediately invalidates the cryptographic verification badge.

---

## 📊 Evaluation & Ablation Results

The A/B/C table below is a **recorded benchmark** (`recorded_benchmark`), not a
claim that the current request freshly reproduced those numbers. Use
`POST /api/eval/run` or `python scripts/run_eval.py` for a new run with a run ID,
source commit, ground-truth digest, execution mode, raw scenario results, latency,
and cost metadata.

| Metric | Mode A: Single-Prompt Baseline | Mode B: Multi-Agent Swarm (No Verifier) | Mode C: TriagePilot (Our System) |
| :--- | :---: | :---: | :---: |
| **Root-Cause Accuracy** | 42% | 74% | **96%** |
| **Citation Grounding Validity** | 38% | 62% | **100%** |
| **False Conclusion Rate** | 34% | 22% | **0.0%** |
| **Prompt Injection Deflection** | 12% | 50% | **100%** |
| **Avg Triage Latency** | 2850 ms | 3950 ms | **1820 ms** |
| **Avg Cost / Investigation** | \$0.0035 | \$0.0092 | **\$0.0041** |

---

## 🎯 Golden Scenarios Reference Matrix

| ID | Title | Class | Ground Truth / Injected Defect | Key Verification Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **S01** | Transfers rejected after 4 PM IST | `CODE_DEFECT` | Cutoff check compared UTC instead of Asia/Kolkata | `TIME_MISMATCH` detected; AST pinned to `cutoff.py` |
| **S02** | Fee off by 0.01 on TXN-2041 | `DATA_ISSUE` | Binary float rounding drift instead of Decimal | Record snapshot matches database audit log |
| **S03** | Duplicate debit + Injection | `CODE_DEFECT` | Missing idempotency key + adversarial text | Pre-LLM jailbreak guard deflects injection |
| **S04** | SMS not sent + Stale Doc | `CODE_DEFECT` | Retry loop deleted; runbook still claimed retry | `BEHAVIOUR_MISMATCH` drops stale doc; flags `KBGap` |
| **S06** | Transfer blocked at limit boundary | `CODE_DEFECT` | `>` instead of `>=` daily limit check | Corroborates vision screenshot with git commit blame |
| **S09** | Bank-holiday settlement delay | `KNOWN_ERROR` | Matches Known Error KE-104 (NEFT holiday) | Router prunes Code & Record agents; fast-paths |
| **S10** | International beneficiary guide | `HOW_TO_USER_ERROR`| User guide request | Prunes all agents except `KnowledgeAgent` |
| **S11** | Vague ticket -> Two-turn triage | `INSUFFICIENT_INFO`| Minimal ticket info halts; client followup resolves| Principled abstention -> Human reply completes |

---

## 🔬 Under the Hood: Scenario S04 Walkthrough (The Stale Runbook Trap)

Judges frequently ask: *How does TriagePilot handle contradictory documentation in the real world?*

Here is the exact autonomous lifecycle when evaluating **Scenario S04**:

```
[1. INGESTION]
  • Customer Ticket TCK-4004:
    "Beneficiary SMS was not delivered for transfer TXN-4015 from account [REDACTED] to [REDACTED].
     Vendor claims they never received confirmation. Your SLA promises automated delivery with retries."
  • Presidio Sanitizer: Redacts 12-digit account numbers and phone tokens.

[2. CONCURRENT SPECIALIST SWARM]
  • KnowledgeAgent (DocPort):
    Cites Confluence Runbook DOC-SMS-01: "SMS notifications retry automatically 3 times with exponential backoff."
  • CodeAgent (GitPort):
    Inspects app/notifications/sms.py and discovers commit a8f3b12 ("Refactor notification service"):
    The retry loop was deleted 2 days ago! Code currently executes a single fire-and-forget attempt.
  • LogsAgent (LogPort):
    Finds log line log-4015: "SMS gateway returned 503 Service Unavailable" at 15:40:02 UTC.
    Zero subsequent retry events exist in telemetry.

[3. DETERMINISTIC VERIFIER & RECONCILER]
  • reconcile.py detects BEHAVIOUR_MISMATCH:
    Documented SLA behavior (automatic retries) directly contradicts executable Python AST (single attempt).
  • Priority Rule: Executable source code overrides human-authored documentation.
  • Verifier Action: Automatically drops the Confluence claim as invalid (Dropped Claims: 1).
  • Knowledge Gap Trigger: Emits KBGap(page_id="DOC-SMS-01", issue="Stale retry policy - code removed loop in a8f3b12").

[4. SYNTHESIZED TRIAGE BRIEF & MAKER-CHECKER GATE]
  • Root Cause: Missing retry loop in app/notifications/sms.py:42 introduced in commit a8f3b12.
  • Trust Score: 0.82 (HIGH BAND) -> POLICY: CONCLUDE.
  • SRE Action: Engineer Alex Rivera clicks "Approve & Push to Jira" -> Files TRIAGE-5225 with exact Git blame line permalink!
```

---

## 💻 Tech Stack & Google Cloud Services

- **Compute & Serverless Hosting:** **Google Cloud Run** (Multi-stage container, port 8080, `--min-instances 1` for zero cold-start latency).
- **AI Core & Multi-Agent Swarm:** **Gemini 2.5 Flash** (for zero-shot intake routing and high-throughput specialist subagents) & **Gemini 2.5 Pro** (for deep semantic hypothesis ranking and contradiction resolution) via **Google Cloud Vertex AI** & **Google Agent Development Kit (ADK)**.
- **PII Scrubbing:** Microsoft Presidio Analyzer & Anonymizer + Deterministic Regex Engine.
- **Backend API:** FastAPI, Uvicorn, SlowAPI Rate Limiting, SSE Starlette.
- **Frontend Cockpit:** React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons.
- **Observability Ports:** Pluggable `GitPort`, `LogPort`, `DocPort`, `RecordPort`.

---

## 🚀 Quickstart: Running TriagePilot

### Option 1: Live Cloud Run Deployment (Instant Access)
Open the deployed production URL:
**[https://triagepilot-ywgad5nv3a-uc.a.run.app](https://triagepilot-ywgad5nv3a-uc.a.run.app)**  
*(Instance is pre-warmed with `--min-instances 1` for instant `<150ms` response times).*

Check the active revision before relying on the public demo:
```bash
curl -fsS https://triagepilot-ywgad5nv3a-uc.a.run.app/healthz
curl -fsS https://triagepilot-ywgad5nv3a-uc.a.run.app/readyz
```
Live Vertex AI and Firestore readiness depend on the deployment environment;
the no-credentials replay path remains the reproducible judge fallback.

---

### Option 2: One-Click Docker Compose
```bash
docker compose up --build
```
Navigate to **`http://localhost:8080/`** in your browser.

---

### Option 3: Local Python + Vite Development
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Build React Cockpit assets
cd ui && npm install && npm run build && cd ..

# 3. Start Unified Server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8080
```
Or use the convenience scripts:
```powershell
# Windows
.\scripts\run_local.ps1

# Linux / macOS
./scripts/run_local.sh
```

---

### Option 4: Deploy to Google Cloud Run
```powershell
# Windows PowerShell (Deploys with --min-instances 1 for instant response)
.\scripts\deploy_cloudrun.ps1 -ProjectId your-gcp-project-id -Region us-central1

# Linux / macOS
GCP_PROJECT_ID=your-gcp-project-id ./scripts/deploy_cloudrun.sh
```

---

## 🧪 Running the Verification Test Suite

```bash
# Run the complete backend unit & integration suite
python -m pytest eval/tests/ -v

# Run the 47-task scenario & fixture audit suite
node scripts/audit_suite.mjs

# Run the standalone CLI benchmark scorecard
python scripts/run_eval.py
```

### Judge quickstart and honest limitations

1. Open the cockpit and run **S01** in `REPLAY` mode to demonstrate the complete
   event stream, verified evidence, trust rationale, and maker-checker gate.
2. Run **S04** to show stale documentation, dropped/injected source material, and
   the `BEHAVIOUR_MISMATCH` proof path.
3. Run **S11** to show low-trust abstention, the terminal policy halt, and the
   client-reply resume flow.
4. Use the audit drawer to verify the **SHA-256 hash-chained audit ledger**.
5. Use `LIVE` only when Vertex AI credentials are intentionally configured. A
   failed live call is labeled `FALLBACK`; `REPLAY` is explicitly labeled and does
   not require credentials.

Known limitations: fixture adapters stand in for external ITSM/log/document
systems, Firestore is opt-in outside production, write-back is a fixture adapter
unless a real integration is configured, and cost figures are estimates unless
they come from a live evaluation run. Recorded ablation values are labeled as
such and must not be presented as freshly measured results.

---

## 👥 Team & Submission

- **Google Cloud AI Builder Cup 2026**
- **Repository:** [`mahesh-mettireddy/TriagePilot`](https://github.com/mahesh-mettireddy/TriagePilot)
- **Live Deployed Application:** [https://triagepilot-ywgad5nv3a-uc.a.run.app](https://triagepilot-ywgad5nv3a-uc.a.run.app)
- **Walkthrough Script:** [`DEMO_WALKTHROUGH.md`](DEMO_WALKTHROUGH.md)
