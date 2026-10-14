# TriagePilot — Autonomous Initial Analyst & Evidentiary Bridge

> *"Every conclusion ships with proof, or it doesn't ship."*

**Track:** Future of Work & Enterprise Productivity (Google Cloud AI Builder Cup 2026)

---

## 📌 Overview
TriagePilot is an Autonomous Initial Analyst that sits between raw client-reported issues and engineering teams, eliminating the blind L1 -> L2 -> L3 escalation waterfall.

- **4-Way Reality Cross-Examination:** Cross-checks client claims, log events, pinned source code, and runbooks/docs.
- **Intelligent 5-Agent Dynamic Routing:** Activates only relevant specialist sub-agents (`History`, `Knowledge`, `Logs`, `Code`, `Record`) to save latency and token budget.
- **Proof-Carrying Conclusions (`verifier.py`):** Deterministic non-LLM Python code validates all evidence pointers against real data sources. Unverified claims are immediately dropped.
- **Mathematical Trust & Principled Abstention (`trust.py`):** Transparent trust score `[0.00 - 1.00]` with automatic principled abstention when trust < 0.45.
- **Cryptographic Audit & PII Scrubbing:** Pre-LLM deterministic regex masking, customer-reply leak checks, and a SHA-256 hash-chained audit log.

---

## 📂 Repository Structure

```
triagepilot/
├── .gitignore                          # Standard Python / Node exclusions
├── README.md                           # Project overview
├── ARCHITECTURE_AND_SPEC.md            # System architecture, pipeline, and scenario spec
├── PLAN_MEMBER_1_BACKEND.md            # Execution plan for Member 1 (Engine, API, Eval)
├── PLAN_MEMBER_2_FRONTEND_FIXTURES.md  # Execution plan for Member 2 (UI, Fixtures, Bundles)
├── engine/                             # Core investigation engine & verification
│   ├── __init__.py
│   ├── schemas.py                      # Locked shared Pydantic contract
│   ├── agents/                         # ADK specialist & hypothesis agents
│   ├── ports/                          # Hexagonal port definitions
│   └── adapters/                       # Port adapter implementations
├── api/                                # FastAPI backend & SSE streaming
├── eval/                               # Benchmark runner & ablation metrics
├── ui/                                 # React + Vite + Tailwind UI Cockpit
├── data/                               # Fixtures, replays, and golden scenario bundles
│   ├── bundles/                        # S01–S11 scenario bundles
│   ├── fixtures/                       # Mock history, docs, and records
│   └── replays/                        # Pre-cached replay data
├── profiles/                           # System profiles (e.g., transfers.yaml)
└── scripts/                            # Build, bundle, and replay utilities
```

---

## 📑 Core Documentation
- [Architecture & Full Specification](ARCHITECTURE_AND_SPEC.md)
- [Member 1 Plan (Backend / Engine / API)](PLAN_MEMBER_1_BACKEND.md)
- [Member 2 Plan (Frontend / Fixtures / Bundles)](PLAN_MEMBER_2_FRONTEND_FIXTURES.md)
- [Shared Schema Contract](engine/schemas.py)
