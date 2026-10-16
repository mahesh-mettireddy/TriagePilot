# TriagePilot™ — Interactive Walkthrough & Pitch Script

> - **Product:** TriagePilot™ — Autonomous Incident Analyst & Verifiable Evidentiary Bridge
> - **Live URL:** [https://triagepilot-ywgad5nv3a-uc.a.run.app](https://triagepilot-ywgad5nv3a-uc.a.run.app)
> - **Target Walkthrough Length:** 3:00 (180 seconds)

---

## 🎬 Act 1: The Problem & The Evidentiary Architecture (0:00 – 0:35)

**[Visual: Open the TriagePilot™ Command Center (`https://triagepilot-ywgad5nv3a-uc.a.run.app`). Point to the top telemetry bar showing `Vertex AI • Gemini 2.5`, `Firestore Native`, `ADK • A2A v0.2`, and `SHA-256 Ledger`, plus the 10-Stage Verifiable Pipeline Strip.]**

**Voiceover:**
> *"In enterprise production support, when an incident strikes, engineering teams get trapped in the L1-to-L3 escalation waterfall. Support agents escalate vague customer complaints, operations teams dig through distributed logs and stale runbooks, and engineers get paged to inspect Git commit history from scratch.*
>
> *Standard LLM bots fail in production because they hallucinate file paths, trust outdated documentation over real code, and fall victim to prompt injections hidden in tickets or logs.*
>
> *We built **TriagePilot™** — an autonomous incident analyst governed by one rule: **Every conclusion ships with proof, or it doesn't ship.**"*

---

## ⚡ Act 2: Live Code Bug-Hunt & Google A2A Protocol Delegation (0:35 – 1:25)

**[Visual: In Column 1, switch Incident Ingestion to `Live Service`. Open `transfers-demo-app/app/fees/calculator.py` in the IDE, change `fee = round(amount * rate, 2)` to `fee = round(amount * (rate * 4.0), 2)`, save, and click `Sync Repo` in the Live Service & Git Telemetry Bridge.]**

**Voiceover:**
> *"To prove TriagePilot™ is a real engine—not a canned replay—let's introduce a live bug into `transfers-demo-app/app/fees/calculator.py` right now, multiplying customer transfer fees by 4x.*
>
> *Look at the **Live Service & Git Telemetry Bridge**: it immediately detects **`LIVE CODE DIFF DETECTED`** with a brand-new 40-character Git commit SHA. When we click **Trigger Live Payment Request & Populate Ticket** (or manually type a customer complaint) and click **Run Autonomous Triage (LIVE)**—or **Delegate via Google A2A Protocol**—our **Google ADK `ParallelAgent` swarm** inspects the live Git diff, live JSONL logs, and masked ledger snapshot, and `verifier.py` cryptographically verifies the exact line we just edited."*

---

## 🔍 Act 3: 4-Way Cross-Examination, Multimodal Vision OCR & Prompt Injection Guard (1:25 – 2:20)

**[Visual: Switch back to `Queue (8)`, select `#1 · TCK-1001` (`S01: Same-day transfers rejected after 4 PM IST`) and `#5 · TCK-6006` (`S06: Transfer blocked at INR 1,00,000 + Vision OCR`), and click `Run Autonomous Triage`.]**

**Voiceover:**
> *"On **Ticket #1 (`TCK-1001`)**, look at the **4-Way Reality Cross-Examination Matrix**: the client claims transfers failed since Monday 9 AM, but TriagePilot™ flags a `TIME_MISMATCH`—proving from logs and Git history that the regression started Tuesday at 4:02 PM IST due to a UTC vs `Asia/Kolkata` timezone bug in `app/transfers/cutoff.py`.*
>
> *On **Ticket #5 (`TCK-6006`)**, TriagePilot™ passes the customer's attached UI error screenshot to **Gemini 2.5 Flash Vision OCR**, extracts `TXN-6001` and `DOC-LIMITS-01`, and proves a `>=` boundary bug in `app/limits/daily_limit.py`.*
>
> *And on **Ticket #4 (`TCK-4004`)**, Stage 01 quarantines an adversarial log prompt injection (`[INJECTION_QUARANTINED]`) while **Gemini 2.5 Pro** detects a `STALE_DOC_FLAG` and `BEHAVIOUR_MISMATCH` between runbook `DOC-SMS-01` and `app/notifications/sms.py`."*

---

## 🔒 Act 4: Principled Abstention, Maker-Checker Sign-Off & SHA-256 Ledger (2:20 – 3:00)

**[Visual: Click `#8 · TCK-1111` (`S11: Underspecified ticket -> Abstain -> Turn-2 Resume`), show `Ingest Client Clarification & Resume Triage`, then switch to `Architecture & Integration` -> `Google ADK & A2A Protocol` and `SHA-256 Ledger`.]**

**Voiceover:**
> *"When a ticket is underspecified like **Ticket #8 (`TCK-1111`)**, our mathematical trust formula scores `0.22 LOW`, triggers **Principled Abstention**, locks write-back, and asks 2 discriminating questions. Once the client replies, Turn-2 resumes automatically to `HIGH` trust.*
>
> *Every conclusion is gated by **Maker-Checker** approval bound to `report_revision` and `report_hash`, persisted via `LiveWriteAdapter`, and sealed in our **Firestore SHA-256 Hash-Chained Audit Ledger**—achieving **100% citation validity and 0.0% false conclusions across 197 automated tests**."*
