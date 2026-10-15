# TriagePilot (ProofTriage) — Status & Next Steps

## 1. Product Goal & AI Builder Cup Judging Alignment

TriagePilot is a Google Cloud-hosted initial analyst and evidentiary bridge for enterprise support triage. It cross-examines client claims, operational logs, pinned source code, and runbooks so that every root-cause report is backed by deterministically verified evidence pointers.

> Guiding invariant: **Gemini proposes; verified evidence decides.**

- **Technical Implementation:** Centralized Vertex AI Gemini runtime (`gemini-2.5-flash` for intake classification, multimodal screenshot OCR via `types.Part.from_bytes`, and post-verification report synthesis; `gemini-2.5-pro` for verified-evidence hypothesis reconciliation), deterministic Python verifier (`engine/verifier.py`), and Firestore persistence.
- **Enterprise Safety:** Pre-LLM PII masking and prompt-injection quarantine, hard per-investigation tool budget (`max_tool_calls <= 12`), mathematical trust scoring with principled abstention, customer-reply leak checks, and revision-bound maker-checker approval.
- **Operational Transparency:** Explicit execution provenance (`vertex_ai`, `api_key`, `fallback`, `replay`) and a SHA-256 hash-chained audit ledger.

## 2. Verified Completed Capabilities

- **Test, Benchmark & Build Health:** 193 passing backend pytest tests, 8/8 Golden Scenarios passing in `python scripts/run_eval.py` (100% root-cause hit rate, 0% false conclusion rate, 100% prompt-injection defense), and clean React/Tailwind production build (`ui/dist`).
- **Vertex AI Runtime, Multimodal Vision & Provenance (`engine/ai_runtime.py`):** Configured via Application Default Credentials (`GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`) with bounded `ThinkingConfig` (`thinking_budget=0` on `gemini-2.5-flash` intake, multimodal vision extraction, and report synthesis; `thinking_budget=512` on `gemini-2.5-pro` hypothesis reconciliation), per-call outcome/latency tracking, and deterministic fallback on timeout or error.
- **Pre-LLM Safety (`engine/masking.py`):** Deterministic scrubbing of emails, phones, accounts, PAN, IFSC, Aadhaar-style IDs, and prompt-injection quarantine prior to model calls and in UI evidence snippets (`[INJECTION_QUARANTINED]`).
- **Dynamic Routing & Tool Budgets (`engine/planner.py`, `engine/tool_budget.py`):** Classifies tickets into 10 classes, prunes unneeded specialists, fast-exits `SECURITY_SENSITIVE`, and enforces a hard 12-call tool budget (`3` for `INSUFFICIENT_INFO`).
- **ADK-Compatible Tool Registration (`engine/adk_orchestration.py`, `engine/adk_tools.py`):** ADK-compatible tool registration is implemented with shared budget wrappers; native ADK Runner execution is pending.
- **Deterministic Verifier & Four-Way Reconciliation (`engine/verifier.py`, `engine/reconcile.py`):** Pure-Python verification of log IDs/timestamps (`<= 1s` tolerance), 40-char git commit SHAs/line ranges (restored from `data/clientrepo.bundle` in container builds), document sections, visual screenshot attachments (`GET /api/bundles/{scenario_id}/attachments/{filename}`), and transfer records; deterministic `TIME_MISMATCH`, `STATE_MISMATCH`, `CHANGE_MISMATCH`, and `STALE_DOC_FLAG` detection.
- **Trust Gate, Leak Check & Maker-Checker (`engine/trust.py`, `engine/leakcheck.py`, `engine/policy.py`):** Fixed-weight trust formula, abstention below `0.45`, post-synthesis customer-reply leak scanning, and approval bound to `report_revision`, `report_hash`, and `decision_id`.
- **Cloud Run & Firestore Deployment (`engine/persistence.py`, `engine/audit.py`):**
  - Deployed to Cloud Run (`https://triagepilot-ywgad5nv3a-uc.a.run.app`, revision `triagepilot-00011-92z`, project `triagepilot-dev`, region `us-central1`) from Artifact Registry with `min-instances=1` and `--no-cpu-throttling`.
  - Firestore-backed persistence is deployed and readiness-verified (`/readyz` reports `status: ok`, `ai_mode: vertex_ai`, `persistence: firestore`, `audit: _FirestoreStore`).
  - Live end-to-end Vertex AI smoke tests verified on `S01` (`INV-7204512b`, `13.6s`, `0.77 HIGH` trust), multimodal `S06` (`INV-7663bfab`, `14.7s`, `0.73 HIGH` trust), and custom free-text ticket intake (`INV-c8c52201`, `14.1s`, `0.76 HIGH` trust): all four Vertex AI operations (`ticket_classification`, `multimodal_vision_extraction`, `hypothesis_reconciliation`, `report_synthesis`) execute live with `fallback_reason: null`, and `GET /api/audit/verify` confirms an intact SHA-256 hash-chained audit ledger.

## 3. Explicit Limitations

- **ADK Execution:** ADK-compatible tool registration is active, but native ADK `Runner` execution and schema-validated ADK output-to-`EvidenceCard` conversion are pending; specialist execution remains deterministic asyncio/port-based.
- **Audit Ledger Concurrency:** The SHA-256 hash-chained audit ledger (`engine/audit.py`) is process-locked and persisted in Firestore, not a Merkle tree, and cross-instance append is not yet wrapped in a Firestore transaction.
- **Benchmark Provenance:** A/B/C ablation comparisons in `eval/ablations.py` serve recorded benchmark baselines unless a fresh evaluation run is triggered via `POST /api/eval/run` or the Evaluation tab button.

## 4. Prioritized Next-Step Checklist

1. [ ] Wire native Google ADK `Runner` execution and schema-validated conversion from ADK tool outputs into `EvidenceCard` objects.
2. [ ] Wrap Firestore audit ledger sequence allocation and hash chaining in a Firestore transaction for multi-instance concurrency safety.
3. [ ] Record final 3-minute submission pitch video and export 8-slide deck.

## 5. Google Cloud Deployment & Cost Controls

| Resource | Configuration | Cost Control Policy |
|---|---|---|
| **Cloud Run (`triagepilot`)** | 1 vCPU, 1 GiB RAM, `min-instances=1`, `max-instances=5`, `--no-cpu-throttling` | Warm single instance during judging; scale `min-instances=0` after judging |
| **Artifact Registry** | `us-central1-docker.pkg.dev/triagepilot-dev/triagepilot` | Replaces legacy `gcr.io`; retains current container images |
| **Vertex AI Gemini** | `gemini-2.5-flash` (intake) + `gemini-2.5-pro` (reconciliation) | Bounded input length (`12,000` chars), `25s` timeout, replay mode for routine demos |
| **Cloud Firestore** | Native mode in `us-central1` (`investigations`, `events`, `audit_chain`) | Bounded demo documents; single regional database |
| **Cloud Logging** | Structured single-line JSON (`engine/observability.py`) | PII/secret redaction before log emission |

## 6. Definition of Done

- `pytest -q`, `npm run build` (`ui`), `python -m compileall -q engine api`, and `git diff --check` pass cleanly.
- Cloud Run `/readyz` returns `status: ok` with `ai_mode: vertex_ai`, `persistence: firestore`, and `audit: _FirestoreStore`.
- Live investigation creation, SSE event streaming, Firestore report persistence, `GET /api/investigations/{id}`, and `/api/audit/verify` succeed against the deployed service.
- All documentation accurately distinguishes implemented/verified features from pending items without overstating ADK or cryptographic capabilities.
