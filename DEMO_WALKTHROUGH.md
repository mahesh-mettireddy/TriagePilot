# TriagePilot™ — Interactive Walkthrough & Pitch Script

> - **Product:** TriagePilot™ — Autonomous Incident Analyst & Verifiable Evidentiary Bridge
> - **Live URL:** [https://triagepilot-ywgad5nv3a-uc.a.run.app](https://triagepilot-ywgad5nv3a-uc.a.run.app)
> - **Target Walkthrough Length:** 3:00 (180 seconds)

---

## 🎬 Act 1: The Problem & The Evidentiary Architecture (0:00 – 0:35)

**[Visual: Open the TriagePilot™ Command Center (`https://triagepilot-ywgad5nv3a-uc.a.run.app`). Point to the top telemetry bar showing `Vertex AI • Gemini 2.5`, `Firestore Native`, `ADK • A2A v0.2`, and `SHA-256 Ledger`, plus the 3-Stage Pipeline Progress Header (`1. Security & Routing` → `2. 5-Agent Swarm & Verification` → `3. Root Cause & Approval`).]**

**Voiceover:**
> *"In enterprise production support, when an incident strikes, engineering teams get trapped in the L1-to-L3 escalation waterfall. Support agents escalate vague customer complaints, operations teams dig through distributed logs and stale runbooks, and engineers get paged to inspect Git commit history from scratch.*
>
> *Standard LLM bots fail in production because they hallucinate file paths, trust outdated documentation over real code, and fall victim to prompt injections hidden in tickets or logs.*
>
> *We built **TriagePilot™** — an autonomous incident analyst governed by one rule: **Every conclusion ships with proof, or it doesn't ship.**"*

---

## ⚡ Act 2: Live Code Bug-Hunt & Google A2A Protocol Delegation (0:35 – 1:25)

**[Visual: In `Step 1 — Select or Trigger Incident`, switch to `Live Demo App`. Open `transfers-demo-app/app/fees/calculator.py` in the IDE, change `fee = round(amount * rate, 2)` to `fee = round(amount * (rate * 4.0), 2)`, save, and click `Sync Repo` in the Live Demo App & Git Bridge.]**

**Voiceover:**
> *"To prove TriagePilot™ is a real engine—not a canned replay—let's introduce a live bug into `transfers-demo-app/app/fees/calculator.py` right now, multiplying customer transfer fees by 4x.*
>
> *Look at the **Live Demo App & Git Telemetry Bridge**: it immediately detects **`LIVE CODE DIFF DETECTED`** with a brand-new 40-character Git commit SHA. When we click **Trigger Live Payment Request & Populate Ticket** and click **Investigate Incident (LIVE)**—or **Delegate via Google A2A Protocol**—our **Google ADK `ParallelAgent` swarm** inspects the live Git diff, live JSONL logs, runbook `DOC-LIMITS-01` / `DOC-FEES-01`, and masked ledger snapshot, while `verifier.py` cryptographically verifies the exact line we just edited."*

---

## 🔍 Act 3: 4-Way Cross-Examination, 3-Tier Evidence Truth & Next Useful Check (1:25 – 2:15)

**[Visual: Switch back to `Queue`, select `#1 · TCK-1001` (`S01: Same-day transfers rejected after 4 PM IST`) and `#5 · TCK-6006` (`S06: Transfer blocked at INR 1,00,000 + Vision OCR`), and click `Analyze Incident`.]**

**Voiceover:**
> *"On **Ticket #1 (`TCK-1001`)**, look at **Step 2 — 4-Way Reality Cross-Check**: the client claims transfers failed since Monday 9 AM, but TriagePilot™ flags a `TIME_MISMATCH`—proving from logs and Git history that the regression started Tuesday at 4:02 PM IST due to a UTC vs `Asia/Kolkata` timezone bug in `app/transfers/cutoff.py`, graded **`CAUSE_REPRODUCED`** (`GATE: REPRODUCED IN FIXTURE`), and recommends allowlisted check **`CHK-REPRO-CUTOFF`**.*
>
> *On **Ticket #5 (`TCK-6006`)**, TriagePilot™ passes the customer's attached UI error screenshot to **Gemini 2.5 Flash Vision OCR**, extracts `TXN-6001` and runbook `DOC-LIMITS-01`, downgrades the newer innocent `httpx` commit to **`SOURCE_VALIDATED`** so it cannot support a false conclusion, and pins the `>=` boundary bug in `app/limits/daily_limit.py`.*
>
> *And on **Ticket #4 (`TCK-4004`)**, Stage 1 quarantines an adversarial log prompt injection (`[INJECTION_QUARANTINED]`) while **Gemini 2.5 Pro** detects a `STALE_DOC_FLAG` and `BEHAVIOUR_MISMATCH` between runbook `DOC-SMS-01` and `app/notifications/sms.py`."*

---

## 🔒 Act 4: Principled Abstention, Contradictory Evidence Withdrawal & Runnable Ablation (2:15 – 3:00)

**[Visual: Select `#8 · TCK-1111` (`S11: Underspecified ticket -> Abstain -> Turn-2 Resume`), click `Ingest Client Clarification & Resume Triage`, then click the `Contradictory Evidence` tab to demonstrate `WithdrawnConclusion` (`Rev #1 → Rev #2`), approve write-back (`COMMITTED • ISS-xxxx`), and switch to `Evaluation & Benchmark`.]**

**Voiceover:**
> *"When a ticket is underspecified like **Ticket #8 (`TCK-1111`)**, our provenance-deduplicated trust formula scores `0.22 LOW` (`GATE: NEED EVIDENCE`), triggers **Principled Abstention**, locks write-back, and selects **`CHK-CLARIFY-CLIENT`**. Once the client replies, Turn-2 resolves the root cause.*
>
> *And if late-arriving contradictory telemetry arrives in the **Contradictory Evidence** tab (`EVIDENCE_UPDATE`), TriagePilot™ explicitly **withdraws its prior conclusion**, increments `report_revision`, invalidates any prior approval on the superseded report, and seals the withdrawal in our **Firestore SHA-256 Hash-Chained Audit Ledger**—outperforming our runnable Single-Agent Baseline (`50.0%` false conclusions → **`0.0%` false conclusions** and **`100%` root-cause accuracy across all 8 scenarios**)."*
