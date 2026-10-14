"""
engine/ports/base.py
---------------------
Hexagonal port definitions — abstract base classes for all external data sources.

All concrete adapters (fixture, cloud_logging, live_jira, etc.) must implement
these interfaces.  The engine ONLY depends on these abstractions — never on a
concrete adapter directly.

Ports:
  HistoryPort  — past incidents, known errors, change/deploy records
  KnowledgePort — runbooks, architecture docs (with last_updated timestamps)
  LogPort      — normalised JSONL events, error-signature digests, trace lookup
  CodePort     — git repo inspection at pinned SHA (search, read, blame, diff, log)
  RecordPort   — masked transfer/record snapshots (zero raw SQL)
  WritePort    — approval-gated Jira issue creation + comment write-back
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


# ---------------------------------------------------------------------------
# HistoryPort
# ---------------------------------------------------------------------------

class HistoryPort(ABC):
    """Access to historical incidents, known errors, and change records."""

    @abstractmethod
    def similar_tickets(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Return past incident/support tickets semantically similar to *query*.

        Each dict must include at minimum:
          ``{id, title, resolution, resolved_at, ticket_class}``
        """

    @abstractmethod
    def known_errors(self, text: str) -> list[dict[str, Any]]:
        """
        Return Known Error records that match *text*.

        Each dict must include at minimum:
          ``{ke_id, title, symptoms, workaround, status}``
        """

    @abstractmethod
    def recent_changes(
        self,
        window_start: str,
        window_end: str,
    ) -> list[dict[str, Any]]:
        """
        Return change/deploy records in the given UTC ISO-8601 window.

        Each dict must include at minimum:
          ``{change_id, title, deployed_at, modules_affected, author}``
        """


# ---------------------------------------------------------------------------
# KnowledgePort
# ---------------------------------------------------------------------------

class KnowledgePort(ABC):
    """Access to runbooks, architecture docs, and how-to articles."""

    @abstractmethod
    def search_docs(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Return doc page summaries matching *query*.

        Each dict must include at minimum:
          ``{page_id, title, summary, last_updated, space}``
        """

    @abstractmethod
    def get_doc_section(self, page_id: str, section: str) -> Optional[dict[str, Any]]:
        """
        Return the full text of a specific *section* within *page_id*.

        Returns ``None`` if the page or section does not exist.
        Dict must include: ``{page_id, section, content, last_updated}``
        """


# ---------------------------------------------------------------------------
# LogPort
# ---------------------------------------------------------------------------

class LogPort(ABC):
    """Access to normalised application log events."""

    @abstractmethod
    def query_logs(
        self,
        scenario_id: str,
        start_ts: Optional[str] = None,
        end_ts: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Return JSONL log events for *scenario_id* within an optional time window.

        Each event dict must include at minimum:
          ``{log_id, ts, service, level, trace_id, message}``
        """

    @abstractmethod
    def digest_signatures(self, scenario_id: str) -> list[dict[str, Any]]:
        """
        Return error-signature digest records for *scenario_id*.

        Each dict: ``{signature, count, first_seen, last_seen, sample_log_id}``
        """

    @abstractmethod
    def trace_lookup(
        self,
        scenario_id: str,
        trace_id: str,
    ) -> list[dict[str, Any]]:
        """
        Return all log events belonging to *trace_id*.
        """


# ---------------------------------------------------------------------------
# CodePort
# ---------------------------------------------------------------------------

class CodePort(ABC):
    """
    Read-only inspection of a pinned git repository.

    The underlying repo is either:
      - ``/data/clientrepo`` (fixture mode, Member 2's demo app)
      - ``CLIENT_REPO_PATH`` env var (override)
    """

    @abstractmethod
    def search_code(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Full-text search across the repo.

        Each result: ``{path, line_number, snippet, sha}``
        """

    @abstractmethod
    def read_lines(
        self,
        path: str,
        line_start: int,
        line_end: int,
        sha: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Read *line_start*–*line_end* of *path* at *sha* (HEAD if None).

        Returns: ``{path, sha, line_start, line_end, content, github_permalink}``
        """

    @abstractmethod
    def git_log(self, path: str, n: int = 10) -> list[dict[str, Any]]:
        """
        Return the last *n* commits touching *path*.

        Each commit: ``{sha, author, date, message, files_changed}``
        """

    @abstractmethod
    def git_blame(
        self,
        path: str,
        line_start: int,
        line_end: int,
    ) -> list[dict[str, Any]]:
        """
        Return blame records for *line_start*–*line_end* in *path*.

        Each record: ``{line_number, sha, author, date, content}``
        """

    @abstractmethod
    def git_diff(self, sha: str) -> str:
        """Return the unified diff string for commit *sha*."""


# ---------------------------------------------------------------------------
# RecordPort
# ---------------------------------------------------------------------------

class RecordPort(ABC):
    """
    Access to masked transaction/record snapshots.

    ZERO raw SQL — only reads pre-masked JSON snapshot files.
    """

    @abstractmethod
    def get_transfer_record(
        self,
        scenario_id: str,
        transfer_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Return a masked transfer record snapshot for *transfer_id*.

        Returns ``None`` if the record does not exist.
        Dict must include at minimum:
          ``{transfer_id, status, amount, fee, created_at, masked_account}``
        """


# ---------------------------------------------------------------------------
# WritePort
# ---------------------------------------------------------------------------

class WritePort(ABC):
    """
    Approval-gated write operations.

    All methods must be called ONLY after explicit human approval.
    In fixture mode they log to the audit chain and return a mock ref.
    In live mode they call the real Jira REST API.
    """

    @abstractmethod
    def create_issue(self, jira_draft: dict[str, Any]) -> dict[str, Any]:
        """
        Create a Jira issue from *jira_draft*.

        Returns: ``{issue_key, url, status}``
        """

    @abstractmethod
    def post_comment(self, ticket_id: str, comment: str) -> dict[str, Any]:
        """
        Post *comment* to *ticket_id*.

        Returns: ``{comment_id, status}``
        """
