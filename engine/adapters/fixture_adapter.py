"""
engine/adapters/fixture_adapter.py
------------------------------------
File-based concrete implementations of all 6 hexagonal ports.

Data is read from:
  /data/fixtures/history.json          -> HistoryPort
  /data/fixtures/docs.json             -> KnowledgePort
  /data/bundles/{scenario_id}/logs.jsonl    -> LogPort
  /data/bundles/{scenario_id}/record_snapshot.json -> RecordPort
  /data/clientrepo  (or CLIENT_REPO_PATH env) -> CodePort
  audit chain / memory                 -> WritePort (fixture mode)

FALLBACK GUARANTEE:
  If any of the above files do not yet exist (Member 2's data hasn't been
  merged), every method returns a realistic in-memory mock dataset so
  /api/investigations works STANDALONE immediately.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from engine.ports.base import (
    CodePort,
    HistoryPort,
    KnowledgePort,
    LogPort,
    RecordPort,
    WritePort,
)

# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]          # TriagePilot/
_DATA_DIR = _REPO_ROOT / "data"
_FIXTURES_DIR = _DATA_DIR / "fixtures"
_BUNDLES_DIR = _DATA_DIR / "bundles"
_CLIENT_REPO = Path(os.environ.get("CLIENT_REPO_PATH", str(_DATA_DIR / "clientrepo")))


def _load_json(path: Path, fallback: Any) -> Any:
    """Load JSON from *path*; return *fallback* if file missing or malformed."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def _load_jsonl(path: Path, fallback: list) -> list[dict]:
    """Load a JSON-Lines file; return *fallback* if file missing."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


# ---------------------------------------------------------------------------
# In-memory fallback datasets (used when Member 2's files aren't present)
# ---------------------------------------------------------------------------

_FALLBACK_HISTORY: dict[str, Any] = {
    "tickets": [
        {
            "id": "INC-8801",
            "title": "Same-day transfers rejected after 4 PM IST",
            "resolution": "Bug in cutoff.py comparing UTC instead of IST. Fixed in CHG-401.",
            "resolved_at": "2026-09-15T14:30:00Z",
            "ticket_class": "CODE_DEFECT",
        },
        {
            "id": "INC-8745",
            "title": "Fee calculation off by 0.01 on large transfers",
            "resolution": "Float rounding issue in calculator.py. Fixed with Decimal.",
            "resolved_at": "2026-09-01T10:00:00Z",
            "ticket_class": "DATA_ISSUE",
        },
    ],
    "known_errors": [
        {
            "ke_id": "KE-104",
            "title": "Bank-holiday NEFT settlement batch delay",
            "symptoms": "Transfers show 'pending' on bank holidays; no error logs.",
            "workaround": "Inform customer that settlement resumes next business day. No action needed.",
            "status": "OPEN",
        },
    ],
    "changes": [
        {
            "change_id": "CHG-401",
            "title": "Fix cutoff time comparison to use IST",
            "deployed_at": "2026-10-07T10:45:00Z",
            "modules_affected": ["app/transfers/cutoff.py"],
            "author": "dev-team-payments",
        },
        {
            "change_id": "CHG-405",
            "title": "Refactor SMS notification module",
            "deployed_at": "2026-10-10T08:00:00Z",
            "modules_affected": ["app/notifications/sms.py"],
            "author": "dev-team-comms",
        },
    ],
}

_FALLBACK_DOCS: dict[str, Any] = {
    "pages": [
        {
            "page_id": "DOC-SMS-01",
            "title": "SMS Notification Runbook",
            "summary": "Describes SMS delivery behaviour including retry logic.",
            "last_updated": "2026-09-01T00:00:00Z",
            "space": "OPS",
            "sections": {
                "retry_policy": (
                    "SMS notifications automatically retry 3 times with exponential backoff "
                    "on delivery failure. Retry intervals: 30s, 60s, 120s."
                ),
                "escalation": "If all retries fail, raise P2 incident to team-comms.",
            },
        },
        {
            "page_id": "DOC-BEN-02",
            "title": "How to Add an International Beneficiary",
            "summary": "Step-by-step guide for adding international beneficiaries.",
            "last_updated": "2026-10-01T00:00:00Z",
            "space": "KB",
            "sections": {
                "steps": (
                    "1. Go to Transfers > Beneficiaries > Add New. "
                    "2. Select 'International'. "
                    "3. Enter SWIFT/BIC code and IBAN. "
                    "4. Complete 2FA verification. "
                    "5. Beneficiary is active after 30-minute cooling period."
                ),
            },
        },
        {
            "page_id": "DOC-CUTOFF-01",
            "title": "Transfer Cutoff Time Policy",
            "summary": "Describes same-day transfer cutoff rules.",
            "last_updated": "2026-08-15T00:00:00Z",
            "space": "OPS",
            "sections": {
                "cutoff_rule": (
                    "Same-day NEFT/IMPS transfers must be initiated before 4:00 PM IST. "
                    "Transfers initiated after 4:00 PM IST are processed next business day."
                ),
            },
        },
    ]
}

_FALLBACK_LOGS: list[dict[str, Any]] = [
    {
        "log_id": "LOG-001",
        "ts": "2026-10-07T10:35:00Z",
        "service": "transfers",
        "level": "ERROR",
        "trace_id": "trace-abc123",
        "message": "TransferCutoffError: same_day transfer rejected — cutoff check failed for 2026-10-07T10:35:00Z",
    },
    {
        "log_id": "LOG-002",
        "ts": "2026-10-07T10:35:01Z",
        "service": "transfers",
        "level": "INFO",
        "trace_id": "trace-abc123",
        "message": "Transfer TXN-1009 status set to REJECTED",
    },
    {
        "log_id": "LOG-003",
        "ts": "2026-10-07T10:34:58Z",
        "service": "api-gateway",
        "level": "INFO",
        "trace_id": "trace-abc123",
        "message": "POST /api/transfers amount=50000 user=[ACCT_REDACTED]",
    },
]

_FALLBACK_RECORD: dict[str, Any] = {
    "transfer_id": "TXN-1009",
    "status": "REJECTED",
    "amount": 50000.00,
    "fee": 625.00,
    "created_at": "2026-10-07T10:35:00Z",
    "masked_account": "[ACCT_REDACTED]",
    "currency": "INR",
    "type": "SAME_DAY_NEFT",
}


# ---------------------------------------------------------------------------
# FixtureHistoryAdapter
# ---------------------------------------------------------------------------

class FixtureHistoryAdapter(HistoryPort):
    """Reads from /data/fixtures/history.json with in-memory fallback."""

    def __init__(self) -> None:
        raw = _load_json(_FIXTURES_DIR / "history.json", _FALLBACK_HISTORY)
        raw_tickets = raw.get("tickets") or raw.get("incidents") or _FALLBACK_HISTORY["tickets"]
        self._tickets: list[dict] = []
        for t in raw_tickets:
            item = dict(t)
            if "id" not in item:
                item["id"] = item.get("incident_id", item.get("ticket_id", "INC-UNKNOWN"))
            self._tickets.append(item)

        self._known_errors: list[dict] = raw.get("known_errors", _FALLBACK_HISTORY["known_errors"])

        raw_changes = raw.get("changes", _FALLBACK_HISTORY["changes"])
        self._changes: list[dict] = []
        for c in raw_changes:
            item = dict(c)
            if "modules_affected" not in item:
                item["modules_affected"] = item.get("files_changed", [])
            if "files_changed" not in item:
                item["files_changed"] = item.get("modules_affected", [])
            self._changes.append(item)

    def similar_tickets(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Simple keyword match — specialist agent's LLM handles semantic ranking."""
        query_lower = query.lower()
        scored = [
            (
                t,
                sum(
                    1 for word in query_lower.split()
                    if word in (t.get("title", "") + " " + t.get("resolution", "")).lower()
                ),
            )
            for t in self._tickets
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scored[:limit]]

    def known_errors(self, text: str) -> list[dict[str, Any]]:
        text_lower = text.lower()
        return [
            ke for ke in self._known_errors
            if any(word in ke.get("symptoms", "").lower() or ke.get("title", "").lower()
                   for word in text_lower.split())
        ] or self._known_errors  # return all if no match (let LLM filter)

    def recent_changes(
        self,
        window_start: str,
        window_end: str,
    ) -> list[dict[str, Any]]:
        """Return all changes (file-based data is pre-filtered by Member 2)."""
        return self._changes


# ---------------------------------------------------------------------------
# FixtureKnowledgeAdapter
# ---------------------------------------------------------------------------

class FixtureKnowledgeAdapter(KnowledgePort):
    """Reads from /data/fixtures/docs.json with in-memory fallback."""

    def __init__(self) -> None:
        raw = _load_json(_FIXTURES_DIR / "docs.json", _FALLBACK_DOCS)
        self._pages: list[dict] = raw.get("pages", _FALLBACK_DOCS["pages"])

    def search_docs(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_lower = query.lower()
        scored = [
            (p, sum(word in (p.get("title", "") + p.get("summary", "")).lower()
                    for word in query_lower.split()))
            for p in self._pages
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for page, _ in scored[:limit]:
            results.append({
                "page_id": page["page_id"],
                "title": page["title"],
                "summary": page["summary"],
                "last_updated": page["last_updated"],
                "space": page["space"],
            })
        return results

    def get_doc_section(self, page_id: str, section: str) -> Optional[dict[str, Any]]:
        for page in self._pages:
            if page["page_id"] == page_id:
                sections = page.get("sections", {})
                content = sections.get(section)
                if content:
                    return {
                        "page_id": page_id,
                        "section": section,
                        "content": content,
                        "last_updated": page["last_updated"],
                    }
                # A pointer to an unknown section is not proof of the first
                # section.  Returning a substitute silently verifies a
                # hallucinated citation, so fail closed here.
                return None
        return None


# ---------------------------------------------------------------------------
# FixtureLogAdapter
# ---------------------------------------------------------------------------

class FixtureLogAdapter(LogPort):
    """
    Reads from /data/bundles/{scenario_id}/logs.jsonl.
    Falls back to _FALLBACK_LOGS if file doesn't exist.
    """

    def _load(self, scenario_id: str) -> list[dict[str, Any]]:
        path = _BUNDLES_DIR / scenario_id / "logs.jsonl"
        return _load_jsonl(path, _FALLBACK_LOGS)

    def query_logs(
        self,
        scenario_id: str,
        start_ts: Optional[str] = None,
        end_ts: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        logs = self._load(scenario_id)

        # Time window filter
        if start_ts:
            logs = [l for l in logs if l.get("ts", "") >= start_ts]
        if end_ts:
            logs = [l for l in logs if l.get("ts", "") <= end_ts]

        # Field filters (e.g. {"level": "ERROR", "service": "transfers"})
        if filters:
            for key, value in filters.items():
                logs = [l for l in logs if str(l.get(key, "")).upper() == str(value).upper()]

        return logs[:limit]

    def digest_signatures(self, scenario_id: str) -> list[dict[str, Any]]:
        logs = self._load(scenario_id)
        # Group by error message prefix (first 60 chars of ERROR logs)
        signatures: dict[str, dict[str, Any]] = {}
        for log in logs:
            if log.get("level") in ("ERROR", "CRITICAL"):
                key = log.get("message", "")[:60]
                if key not in signatures:
                    signatures[key] = {
                        "signature": key,
                        "count": 0,
                        "first_seen": log.get("ts"),
                        "last_seen": log.get("ts"),
                        "sample_log_id": log.get("log_id"),
                    }
                signatures[key]["count"] += 1
                signatures[key]["last_seen"] = log.get("ts")
        return list(signatures.values())

    def trace_lookup(
        self,
        scenario_id: str,
        trace_id: str,
    ) -> list[dict[str, Any]]:
        logs = self._load(scenario_id)
        return [l for l in logs if l.get("trace_id") == trace_id]


# ---------------------------------------------------------------------------
# FixtureRecordAdapter
# ---------------------------------------------------------------------------

class FixtureRecordAdapter(RecordPort):
    """
    Reads from /data/bundles/{scenario_id}/record_snapshot.json.
    Falls back to _FALLBACK_RECORD if file doesn't exist.
    """

    def get_transfer_record(
        self,
        scenario_id: str,
        transfer_id: str,
    ) -> Optional[dict[str, Any]]:
        path = _BUNDLES_DIR / scenario_id / "record_snapshot.json"
        data = _load_json(path, None)

        if data is None:
            # Use fallback — filter by transfer_id if provided
            if _FALLBACK_RECORD.get("transfer_id") == transfer_id:
                return _FALLBACK_RECORD
            return None

        # data can be a list of records or a single record dict
        if isinstance(data, list):
            for record in data:
                if record.get("transfer_id") == transfer_id:
                    return record
            return None

        if isinstance(data, dict):
            if data.get("transfer_id") == transfer_id:
                return data
        return None


# ---------------------------------------------------------------------------
# FixtureCodeAdapter
# ---------------------------------------------------------------------------

class FixtureCodeAdapter(CodePort):
    """
    Read-only git inspection of the client demo repo at CLIENT_REPO_PATH
    (defaults to /data/clientrepo).

    Falls back to stub responses if the repo doesn't exist yet.
    """

    def __init__(self) -> None:
        self._repo_path = _CLIENT_REPO
        self._repo = self._try_open_repo()

    def _try_open_repo(self):
        """Attempt to open the git repo; return None if not available."""
        if not self._repo_path.exists():
            return None
        try:
            import git  # gitpython
            return git.Repo(str(self._repo_path))
        except Exception:
            return None

    def _read_file_at_sha(self, path: str, sha: Optional[str]) -> str:
        """Read file content at an explicit commit SHA."""
        if self._repo is None or not sha:
            raise FileNotFoundError("Pinned git repository or commit SHA is unavailable")
        try:
            commit = self._repo.commit(sha)
            blob = commit.tree / path
            return blob.data_stream.read().decode("utf-8", errors="replace")
        except Exception as exc:
            raise FileNotFoundError(f"Cannot read {path} at commit {sha}") from exc

    def search_code(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Grep-style search across all tracked files."""
        if not self._repo_path.exists():
            return self._stub_search(query)

        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        for root, dirs, files in os.walk(self._repo_path):
            # Skip .git directory
            dirs[:] = [d for d in dirs if d != ".git"]
            for fname in files:
                if not fname.endswith((".py", ".js", ".ts", ".yaml", ".json", ".md")):
                    continue
                fpath = Path(root) / fname
                try:
                    lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
                except OSError:
                    continue
                rel_path = str(fpath.relative_to(self._repo_path)).replace("\\", "/")
                for i, line in enumerate(lines, start=1):
                    if query_lower in line.lower():
                        sha = self._head_sha()
                        results.append({
                            "path": rel_path,
                            "line_number": i,
                            "snippet": line.strip()[:200],
                            "sha": sha,
                        })
                        if len(results) >= limit:
                            return results
        return results

    def _head_sha(self) -> str:
        if self._repo:
            try:
                return self._repo.head.commit.hexsha
            except Exception:
                pass
        return "0000000000000000000000000000000000000000"

    def read_lines(
        self,
        path: str,
        line_start: int,
        line_end: int,
        sha: Optional[str] = None,
    ) -> dict[str, Any]:
        if not sha or len(sha) != 40:
            raise ValueError("read_lines requires a full 40-character commit SHA")
        if line_start < 1 or line_end < line_start:
            raise ValueError("line range must satisfy 1 <= line_start <= line_end")
        content = self._read_file_at_sha(path, sha)
        all_lines = content.splitlines()
        if line_end > len(all_lines):
            raise ValueError(
                f"line range {line_start}-{line_end} exceeds file length {len(all_lines)}"
            )
        start = line_start - 1
        end = line_end
        excerpt = "\n".join(all_lines[start:end])
        resolved_sha = sha

        # Build GitHub permalink using GITHUB_REPO env var if set
        gh_repo = os.environ.get("GITHUB_REPO", "mahesh-mettireddy/TriagePilot")
        permalink = (
            f"https://github.com/{gh_repo}/blob/{resolved_sha}/{path}"
            f"#L{line_start}-L{line_end}"
        )
        return {
            "path": path,
            "sha": resolved_sha,
            "line_start": line_start,
            "line_end": line_end,
            "content": excerpt,
            "github_permalink": permalink,
        }

    def git_log(self, path: str, n: int = 10) -> list[dict[str, Any]]:
        if self._repo is None:
            return self._stub_git_log(path)
        try:
            commits = list(self._repo.iter_commits(paths=path, max_count=n))
            return [
                {
                    "sha": c.hexsha,
                    "author": c.author.name,
                    "date": c.committed_datetime.isoformat(),
                    "message": c.message.strip(),
                    "files_changed": list(c.stats.files.keys()),
                }
                for c in commits
            ]
        except Exception:
            return self._stub_git_log(path)

    def git_blame(
        self,
        path: str,
        line_start: int,
        line_end: int,
    ) -> list[dict[str, Any]]:
        if self._repo is None:
            return self._stub_blame(path, line_start, line_end)
        try:
            blame = self._repo.blame("HEAD", path)
            results = []
            current_line = 1
            for commit, lines in blame:
                for line_bytes in lines:
                    if line_start <= current_line <= line_end:
                        results.append({
                            "line_number": current_line,
                            "sha": commit.hexsha,
                            "author": commit.author.name,
                            "date": commit.committed_datetime.isoformat(),
                            "content": line_bytes.decode("utf-8", errors="replace").rstrip(),
                        })
                    current_line += 1
            return results
        except Exception:
            return self._stub_blame(path, line_start, line_end)

    def git_diff(self, sha: str) -> str:
        if self._repo is None:
            return f"# diff not available — repo not found at {self._repo_path}"
        try:
            commit = self._repo.commit(sha)
            if commit.parents:
                diffs = commit.parents[0].diff(commit, create_patch=True)
                return "\n".join(d.diff.decode("utf-8", errors="replace") for d in diffs)
            return "# initial commit — no parent diff available"
        except Exception as exc:
            return f"# diff error: {exc}"

    # ------------------------------------------------------------------
    # Stubs — returned when repo doesn't exist yet
    # ------------------------------------------------------------------

    def _stub_search(self, query: str) -> list[dict[str, Any]]:
        return [
            {
                "path": "app/transfers/cutoff.py",
                "line_number": 18,
                "snippet": f"# [STUB] search for '{query}' — clientrepo not yet available",
                "sha": "stub0000000000000000000000000000000000000",
            }
        ]

    def _stub_git_log(self, path: str) -> list[dict[str, Any]]:
        return [
            {
                "sha": "stub0000000000000000000000000000000000000",
                "author": "stub-author",
                "date": "2026-10-07T10:45:00+00:00",
                "message": f"[STUB] git log for {path} — clientrepo not yet available",
                "files_changed": [path],
            }
        ]

    def _stub_blame(
        self, path: str, line_start: int, line_end: int
    ) -> list[dict[str, Any]]:
        return [
            {
                "line_number": n,
                "sha": "stub0000000000000000000000000000000000000",
                "author": "stub-author",
                "date": "2026-10-07T10:45:00+00:00",
                "content": f"# [STUB] blame line {n} — clientrepo not yet available",
            }
            for n in range(line_start, line_end + 1)
        ]


# ---------------------------------------------------------------------------
# FixtureWriteAdapter
# ---------------------------------------------------------------------------

class FixtureWriteAdapter(WritePort):
    """
    Fixture write-back: logs to audit chain and returns a mock ref.
    No real Jira/external calls.
    """

    def create_issue(self, jira_draft: dict[str, Any]) -> dict[str, Any]:
        import engine.audit as audit
        inv_id = jira_draft.get("investigation_id", "unknown")
        audit.append(inv_id, "write_back_jira", {"action": "create_issue", "title": jira_draft.get("title")})
        mock_key = f"TRIAGE-{abs(hash(jira_draft.get('title', ''))) % 9000 + 1000}"
        return {
            "issue_key": mock_key,
            "url": f"https://jira.example.com/browse/{mock_key}",
            "status": "fixture_created",
        }

    def post_comment(self, ticket_id: str, comment: str) -> dict[str, Any]:
        import engine.audit as audit
        audit.append(ticket_id, "write_back_comment", {"ticket_id": ticket_id, "length": len(comment)})
        return {
            "comment_id": f"CMT-{abs(hash(comment)) % 9000 + 1000}",
            "status": "fixture_posted",
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_adapters() -> dict[str, Any]:
    """
    Return all concrete adapter instances as a dict.

    Usage::
        adapters = get_adapters()
        history = adapters["history"]
        logs = adapters["logs"]
    """
    return {
        "history": FixtureHistoryAdapter(),
        "knowledge": FixtureKnowledgeAdapter(),
        "logs": FixtureLogAdapter(),
        "code": FixtureCodeAdapter(),
        "record": FixtureRecordAdapter(),
        "write": FixtureWriteAdapter(),
    }
