# ANTIGRAVITY EXECUTION PLAN — MEMBER 1 (WS-A: ENGINE, ADK AGENTS, VERIFIER, API, EVAL)

## STRICT WORKSPACE RULES FOR ANTIGRAVITY
1. Read `ARCHITECTURE_AND_SPEC.md` and `engine/schemas.py` first. Do NOT modify `engine/schemas.py` without team sync.
2. **EXCLUSIVE FOLDERS OWNED BY MEMBER 1:**
   - `/engine/` (`planner.py`, `masking.py`, `verifier.py`, `reconcile.py`, `trust.py`, `leakcheck.py`, `audit.py`, `policy.py`, `agents/`, `ports/`, `adapters/`)
   - `/api/` (`main.py`, `sse.py`, `ratelimit.py`)
   - `/eval/` (`runner.py`, `metrics.py`, `ablations.py`)
   - `requirements.txt`
3. **FORBIDDEN FOLDERS (Owned by Member 2 — DO NOT TOUCH):**
   - `/ui/`, `/data/`, `/profiles/`, `/scripts/`, `Dockerfile`.
   - *Note:* If `/data/bundles/S01` does not exist yet while testing locally, create an in-memory mock fallback inside `/engine/adapters/fixture_adapter.py` so `/api/investigations` works standalone immediately.

---

## STEP-BY-STEP BUILD SEQUENCE

### Phase 1: Dependencies & Guardrails (`requirements.txt`, `masking.py`, `leakcheck.py`, `audit.py`)
1. **`requirements.txt`:** Include `fastapi`, `uvicorn[standard]`, `pydantic>=2.0`, `google-genai`, `google-adk`, `pyyaml`, `gitpython`, `httpx`, `sse-starlette`, `pytest`, `google-cloud-firestore`, `google-cloud-logging`.
2. **`engine/masking.py`:**
   - Deterministic regex scrubber running BEFORE any model call.
   - Redact: Email -> `[EMAIL_REDACTED]`, Phone -> `[PHONE_REDACTED]`, Account# (10-16 digits) -> `[ACCT_REDACTED]`, PAN (`[A-Z]{5}[0-9]{4}[A-Z]`) -> `[PAN_REDACTED]`, IFSC (`[A-Z]{4}0[A-Z0-9]{6}`) -> `[IFSC_REDACTED]`, 12-digit government ID pattern -> `[Aadhaar Redacted]`.
   - Also implement `detect_prompt_injection(text: str) -> tuple[bool, str | None]` scanning for `"ignore previous instructions"`, `"system override"`, `"ignore all rules"`, etc.
3. **`engine/leakcheck.py`:**
   - Deterministic scan on `customer_reply_draft`: reject if it contains internal file paths (`app/`, `.py`), stack trace lines (`Traceback`), internal hostnames (`localhost`, `.internal`), or raw git SHAs.
4. **`engine/audit.py`:**
   - Maintain an append-only list of `AuditChainEntry` (persisted to Firestore if configured, with local JSON/memory fallback).
   - `entry_hash = hashlib.sha256((prev_hash + canonical_json).encode()).hexdigest()`.
   - Provide `verify_chain() -> dict` returning `{valid: bool, entries_checked: int, first_broken_seq: int | None}`.

### Phase 2: Universal Hexagonal Ports & Adapters (`engine/ports/`, `engine/adapters/`)
Define abstract base classes in `engine/ports/base.py` and concrete adapters in `engine/adapters/`:
1. **`HistoryPort`:** `similar_tickets(query)`, `known_errors(text)`, `recent_changes(window_start, window_end)`. Reads from `/data/fixtures/history.json` (with built-in fallback data if Member 2's file isn't merged yet).
2. **`KnowledgePort`:** `search_docs(query)`, `get_doc_section(page_id, section)`. Reads from `/data/fixtures/docs.json`.
3. **`LogPort`:** `query_logs(scenario_id, start_ts, end_ts, filters)`, `digest_signatures(scenario_id)`, `trace_lookup(scenario_id, trace_id)`. Reads `/data/bundles/{scenario_id}/logs.jsonl` or Google Cloud Logging when `source=cloud_logging`.
4. **`CodePort`:** Inspects `/data/clientrepo` (or `CLIENT_REPO_PATH` env var) using `gitpython` or file reads at pinned SHA: `search_code(query)`, `read_lines(path, start, end)`, `git_log(path, n)`, `git_blame(path, start, end)`, `git_diff(sha)`.
5. **`RecordPort`:** `get_transfer_record(scenario_id, transfer_id)` reading masked snapshot `/data/bundles/{scenario_id}/record_snapshot.json`. Zero SQL execution.
6. **`WritePort`:** Approval-gated `create_issue(jira_draft)` and `post_comment(ticket_id, reply)`. Supports `fixture` mode (writes to audit/memory) and optional live `jira_rest` mode via `JIRA_BASE_URL` and `JIRA_API_TOKEN`.

### Phase 3: Intelligent Dynamic Router & 5 ADK Specialist Sub-Agents (`engine/planner.py`, `engine/agents/`)
Use `google-genai` (`gemini-2.5-flash` for fast steps, `gemini-2.5-pro` for Hypothesis/Semantic Reconciliation) with `response_schema` enforced:
1. **`engine/planner.py` (`Intake & Dynamic Router`):**
   - Classifies `TicketDTO` into `TicketClass` and `Severity`.
   - Reads screenshot attachment via Gemini Vision if present (`source_type=visual`).
   - Checks `TicketDTO.human_context`:
     - If `CLIENT_REPLY`: appends client answers to entities and upgrades routing from `INSUFFICIENT_INFO` to the target technical class (e.g., `CODE_DEFECT`).
     - If `DEV_STEER`: prioritizes the file/module named in `human_context.message` and retains `pinned_card_ids`.
   - **Intelligent Agent Pruning (Crucial):**
     - `HOW_TO_USER_ERROR` -> Active: `["KnowledgeAgent"]` | Skipped: `LogsAgent`, `CodeAgent`, `RecordAgent`, `HistoryAgent`.
     - `KNOWN_ERROR` -> Active: `["HistoryAgent", "LogsAgent"]` | Skipped: `CodeAgent`, `RecordAgent`, `KnowledgeAgent`.
     - `INSUFFICIENT_INFO` -> Active: `["HistoryAgent", "LogsAgent"]` (digest only, budget=3) | Skipped: `CodeAgent`, `RecordAgent`, `KnowledgeAgent`.
     - `DATA_ISSUE` -> Active: `["RecordAgent", "LogsAgent", "CodeAgent", "KnowledgeAgent"]` | Skipped: `HistoryAgent`.
     - `CODE_DEFECT` / `CONFIG_ENV` -> Active: `["LogsAgent", "CodeAgent", "HistoryAgent", "KnowledgeAgent"]` (+ `RecordAgent` if a `TXN-` ID is in the ticket).
     - `SECURITY_SENSITIVE` -> Active: `[]` (Immediate escalate shortcut).
2. **`engine/agents/specialists.py` (The 5 Specialist Sub-Agents):**
   - Implement `HistoryAgent`, `KnowledgeAgent`, `LogsAgent`, `CodeAgent`, `RecordAgent`.
   - Execute ONLY the `active_agents` from `AgentRoutingPlan` concurrently (using ADK `ParallelAgent` or `asyncio.gather`).
   - Emit SSE event `agent_skipped` for each pruned agent so the UI highlights cost/time savings.
   - Each active agent executes its port tools and returns typed `EvidenceCard` objects.

### Phase 4: Deterministic Verifier, Hybrid Reconciler & Trust Math (`verifier.py`, `reconcile.py`, `trust.py`)
1. **`engine/verifier.py`:**
   - Pure Python (NO LLM). Validates each `EvidenceCard`:
     - `log`: `log_id` exists in bundle/logs; normalized `snippet` is a substring of message; `ts` matches within 1s.
     - `code`: file `path` exists; `line_start..line_end` valid; whitespace-normalized `snippet` is substring of those exact lines; generates `github_permalink`.
     - `doc`: `page_id` and `section` exist; normalized `snippet` matches.
     - `ticket` / `record`: `id` exists and field matches snippet.
     - `visual`: marked `verified` only if corroborated by at least one non-visual card.
   - Cards that fail verification get `verification.status = DROPPED` with an explicit `reason` (e.g., `"Line 42 in cutoff.py does not contain claimed snippet"`).
   - **Seeded Hallucination Demo Guarantee:** Ensure that if a specialist emits an unverified/speculative claim (or during test verification), the verifier catches and drops it so the UI counter `Verified: N | Dropped: M` is demonstrated clearly.
2. **`engine/reconcile.py` (Deterministic Half):**
   - `TIME_MISMATCH`: `|client_claimed_start_utc - first_error_log_utc| > 30 minutes`.
   - `STATE_MISMATCH`: Client claimed transfer status != `RecordPort` status.
   - `STALE_DOC_FLAG`: `doc.last_updated < culprit_commit.date`.
3. **`engine/agents/hypothesis_agent.py` (`gemini-2.5-pro` — Semantic Half + Root Cause):**
   - Input: ONLY `verified_cards` + deterministic contradictions.
   - Detects `BEHAVIOUR_MISMATCH` (comparing verified `doc` card vs verified `code` card) and `SCOPE_MISMATCH`.
   - Outputs `<= 4` `Hypothesis` objects citing verified `card_id`s only.
4. **`engine/trust.py` (Deterministic Formula):**
   - Implement exact formula from `ARCHITECTURE_AND_SPEC.md` Section 2.7 (`c_ver`, `c_div`, `c_spec`, `c_time`, `p_contra`, `p_unver`).
   - Assign band (`HIGH >= 0.70`, `MEDIUM 0.45-0.70`, `LOW < 0.45`) and `PolicyAction`.
5. **`engine/agents/report_agent.py` (`gemini-2.5-flash`):**
   - Produces `ReportOutput`, `questions_for_client` (if `ABSTAIN` or `MEDIUM`), `jira_draft`, `kb_gap`, and `customer_reply_draft` (passed through `leakcheck.py`).

### Phase 5: FastAPI Backend, SSE Streaming & Eval Runner (`api/`, `eval/`)
1. **`api/main.py` & `api/sse.py`:**
   - `POST /api/investigations` -> starts investigation (or loads cached replay if `mode=="replay"` or on API error fallback); returns `{id}`.
   - `GET /api/investigations/{id}/events` -> streams `SSEEvent` objects in real time.
   - `GET /api/investigations/{id}` -> returns full `ReportOutput`.
   - `POST /api/investigations/{id}/decision` -> records human `approved | edited | rejected`; if `approved`, invokes `WritePort`.
   - `GET /api/scenarios` -> lists the 8 Golden Scenarios.
   - `GET /api/profile` -> returns parsed `profiles/transfers.yaml`.
   - `GET /api/eval/results` & `POST /api/eval/run` -> returns/runs A/B/C ablation metrics (`single_prompt` vs `agents_no_verify` vs `full_triagepilot`).
   - `GET /api/audit/verify` -> verifies SHA-256 chain integrity.
   - `GET /healthz` -> returns `{"status": "ok"}`.
   - Serve built static files from `/ui/dist` if directory exists (for single-service Cloud Run deployment).