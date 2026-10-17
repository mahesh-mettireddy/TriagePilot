# TriagePilot™ — Interactive Walkthrough & 3-Minute Pitch Script

> - **Product:** TriagePilot™ — Autonomous Incident Analyst & Verifiable Evidentiary Bridge
> - **Live URL:** [https://triagepilot-ywgad5nv3a-uc.a.run.app](https://triagepilot-ywgad5nv3a-uc.a.run.app)
> - **Complete Codeflow & Readiness Playbook:** [`READINESS.md`](READINESS.md)
> - **Target Walkthrough Length:** 3:00 (180 seconds)

---

## 🎬 Minute 0:00 – 0:40 | Act 1: The Problem & The Evidentiary Rule

**[Visual: Open the TriagePilot™ Cockpit (`https://triagepilot-ywgad5nv3a-uc.a.run.app`). Point to the top telemetry badges (`Vertex AI • Gemini 2.5`, `Firestore Native`, `ADK • A2A v0.2`, `SHA-256 Audit Chain`) and the 3-column layout: Incident Queue & Live Trigger (Left), 4-Way Reality Cross-Check & Interactive HITL Loop (Middle), and Verified Root Cause, Next Useful Check & Evidentiary Trust Gate (Right).]**

**Voiceover:**
> *"In enterprise fintech and production support, when an incident strikes, teams get trapped in the L1-to-L3 escalation waterfall. Support agents escalate vague customer complaints, operations digs through distributed logs and outdated runbooks, and engineers get paged to inspect Git commit history from scratch.*
>
> *Standard LLM copilots fail in production because they hallucinate file paths, trust stale documentation over real code, and fall victim to prompt injections hidden in tickets or logs.*
>
> *We built **TriagePilot™** — an autonomous incident analyst governed by one strict rule: **Every conclusion ships with proof, or it doesn't ship.** Every claim is deterministically verified against real Git commit SHAs, line numbers, JSONL logs, runbooks, and masked ledger records before a human ever approves write-back."*

---

## ⚡ Minute 0:40 – 2:00 | Act 2: Live Case #1 — Client Bug Report $\rightarrow$ Triage Swarm $\rightarrow$ Dev HITL Loop $\rightarrow$ Live Code Fix Verified

**[Visual: Switch to `Live App` $\rightarrow$ click `S03: Daily Limit Boundary >= Bug` (`INR 100,000`) $\rightarrow$ click `Trigger & Auto-Triage in Cockpit`. Then in the Cockpit middle column (`Interactive HITL Loop`), select `Steer Swarm`, enter developer confirmation, and click `Re-Investigate with Context`. Finally, open `Live App` $\rightarrow$ `Live Code Studio` (`app/limits/daily_limit.py`), change `>=` to `>`, and click `Commit & Triage in Cockpit`.]**

**Voiceover:**
> *"Let's run a real end-to-end incident live—not a canned replay.*
>
> *1. **Turn 1 (Client Bug Report & Swarm Pinpoint):** A customer attempts a ₹1,00,000 transfer and fails with `DailyLimitExceededError`, even though their prior spend today is ₹0.00. TriagePilot's 5-specialist swarm cross-examines the client claim, live JSONL logs, masked ledger state, Runbook `DOC-LIMITS-01`, and Git AST—pinpointing `app/limits/daily_limit.py:29` (`if transfer_amount >= DAILY_TRANSFER_LIMIT:`), graded **`CAUSE_REPRODUCED`**, and selecting allowlisted check **`CHK-BOUNDARY-CONTROL-DIFF`**.*
>
> *2. **Turn 2 (Interactive Developer HITL Loop):** In the middle column under **Interactive HITL Loop**, the on-call engineer selects **`Steer Swarm`** and types in plain English: 'I checked daily_limit logic and confirmed line 29 uses >= instead of > against DAILY_TRANSFER_LIMIT. Please confirm runbook DOC-LIMITS-01 and prepare the fix recommendation.' Clicking **Re-Investigate** dynamically updates the **Probable Root Cause** with `[HITL ENGINEER CONFIRMATION]`, transitions **Next Useful Check** to **`CHK-STEER-DIRECTIVE-VERIFIED`**, logs the engineer steer in the **Evidence Trust Gate** (`0.76 HIGH / CONCLUDE`), and updates the customer reply and Jira draft.*
>
> *3. **Turn 3 (Live Code Studio Fix & Auto-Probe Verification):** Now we open the **Live Code Studio**, change `>=` to `>` in `app/limits/daily_limit.py`, and click **Commit & Triage in Cockpit**. TriagePilot commits a brand-new 40-character Git SHA, automatically executes a live ₹1,00,000 probe transfer (`COMPLETED`), and verifies **`[LIVE GIT FIX VERIFIED]`** with **`CHK-LIVE-FIX-VERIFIED`**!"*

---

## 🔒 Minute 2:00 – 3:00 | Act 3: Live Case #2 — Principled Abstention (`S11`), Conclusion Withdrawal & 100% Benchmark Proof

**[Visual: Select `S11` from the Queue (`"Transfers not working urgently"`), click `Run Triage`, then click `Client Reply` in the HITL Loop to resume triage, click `New Evidence` (`EVIDENCE_UPDATE`) to demonstrate `WithdrawnConclusion` (`Rev #1 → Rev #2`), and switch to `Eval Suite`.]**

**Voiceover:**
> *"What happens when a ticket is underspecified, like `S11` ('Transfers not working urgently')? Instead of guessing, our provenance-deduplicated trust formula scores `0.22 LOW` (`GATE: NEED_EVIDENCE`), triggers **Principled Abstention**, locks write-back, and selects **`CHK-CLARIFY-CLIENT`** with two targeted questions. Once the client replies (`TXN-1009 at 4:15 PM IST`), Turn 2 resolves the exact UTC-vs-IST cutoff bug in `app/transfers/cutoff.py` while flagging a 31-hour `TIME_MISMATCH`.*
>
> *And if late-arriving contradictory telemetry arrives via **`New Evidence`** (`EVIDENCE_UPDATE`), TriagePilot explicitly **withdraws Revision #1** (`WithdrawnConclusion`), increments to **Revision #2**, invalidates stale approvals, and seals every transition in our **Firestore SHA-256 Hash-Chained Audit Ledger**.*
>
> *Across 205 automated pytest tests and 8 golden evaluation scenarios—including Gemini Vision OCR on `S06` and adversarial prompt injections on `S03` and `S04`—TriagePilot achieves **100% root-cause accuracy and 0.0% false conclusions**, outperforming our runnable Single-Agent Baseline (`50.0%` false conclusions → `0.0%`)."*
