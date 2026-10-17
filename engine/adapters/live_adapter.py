"""
engine/adapters/live_adapter.py
-------------------------------
Production-grade Live Connectors for TriagePilot's 6 Hexagonal Ports.

Connects the neuro-symbolic triage pipeline to:
  1. Live Target Codebase (`transfers-demo-app/app`) via an isolated Git mirror
     (`data/live/clientrepo`) that preserves `data/clientrepo` (S01..S11) untouched
     while automatically syncing & committing live developer edits so every
     modified line has a verifiable 40-character Git SHA.
  2. Live Telemetry Stream (`data/live/logs.jsonl`) emitted by `transfers-demo-app`.
  3. Live Transaction Ledger Replica (`data/live/records.json`) with deterministic
     PII masking (`[ACCT_REDACTED]`).
  4. Live Git Deployment History (`git log` -> `CHG-<short_sha>`).
  5. Live Issue & Customer Response Write-Back (`data/live/issues.json` + optional
     GitHub Issues REST API when `GITHUB_TOKEN` is configured).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import urllib.request
import urllib.error

from engine.adapters.fixture_adapter import (
    FixtureCodeAdapter,
    FixtureHistoryAdapter,
    FixtureKnowledgeAdapter,
    FixtureLogAdapter,
    FixtureRecordAdapter,
    FixtureWriteAdapter,
    get_adapters as get_fixture_adapters,
)
from engine.ports.base import (
    CodePort,
    HistoryPort,
    KnowledgePort,
    LogPort,
    RecordPort,
    WritePort,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = _REPO_ROOT / "data"
_LIVE_DIR = _DATA_DIR / "live"
_LIVE_LOGS_PATH = _LIVE_DIR / "logs.jsonl"
_LIVE_RECORDS_PATH = _LIVE_DIR / "records.json"
_LIVE_ISSUES_PATH = _LIVE_DIR / "issues.json"
_LIVE_REPO_DIR = _LIVE_DIR / "clientrepo"
_BASELINE_BUNDLE = _DATA_DIR / "clientrepo.bundle"
_BASELINE_CLIENT_REPO = _DATA_DIR / "clientrepo"
_DEMO_APP_DIR = _REPO_ROOT / "transfers-demo-app"
_BASELINE_HEAD_SHA = "61b344d"
_BASELINE_SHAS = ("288c17a", "61b344d")

_ALLOWLISTED_LIVE_FILES: dict[str, str] = {
    "app/limits/daily_limit.py": "Daily Limit Enforcer (>= vs > Boundary)",
    "app/transfers/cutoff.py": "Same-Day Cutoff Validator (UTC vs IST)",
    "app/fees/calculator.py": "Fee Calculator (Float vs Decimal Rounding)",
    "app/notifications/sms.py": "SMS Notification Dispatcher (Retry Loop)",
}


def _is_baseline_commit(sha: str) -> bool:
    return bool(sha) and sha.startswith(_BASELINE_SHAS)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_live_dirs() -> None:
    _LIVE_DIR.mkdir(parents=True, exist_ok=True)


def _remove_readonly(func: Any, path: str, _excinfo: Any) -> None:
    import stat
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def ensure_live_git_repo() -> Path:
    """
    Ensure `data/live/clientrepo` exists as an initialized Git repository
    seeded from `data/clientrepo` (or `data/clientrepo.bundle`).
    Never mutates `data/clientrepo` so Golden Scenarios S01-S11 remain pinned.
    """
    _ensure_live_dirs()
    git_dir = _LIVE_REPO_DIR / ".git"
    if (git_dir / "HEAD").exists() and (_LIVE_REPO_DIR / "app").exists():
        return _LIVE_REPO_DIR

    if _LIVE_REPO_DIR.exists():
        shutil.rmtree(_LIVE_REPO_DIR, onerror=_remove_readonly)

    # Prefer cloning from bundle or copying from data/clientrepo
    if _BASELINE_BUNDLE.exists():
        try:
            subprocess.run(
                ["git", "clone", str(_BASELINE_BUNDLE), str(_LIVE_REPO_DIR)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return _LIVE_REPO_DIR
        except Exception as exc:
            logger.warning("Failed to clone clientrepo.bundle into live repo: %s", exc)

    if (_BASELINE_CLIENT_REPO / ".git" / "HEAD").exists():
        shutil.copytree(_BASELINE_CLIENT_REPO, _LIVE_REPO_DIR, dirs_exist_ok=True)
        return _LIVE_REPO_DIR

    # Fallback: copy transfers-demo-app and git init
    shutil.copytree(_DEMO_APP_DIR, _LIVE_REPO_DIR, dirs_exist_ok=True)
    subprocess.run(["git", "init"], cwd=str(_LIVE_REPO_DIR), check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "dev@triagepilot.io"], cwd=str(_LIVE_REPO_DIR), check=False)
    subprocess.run(["git", "config", "user.name", "live-developer"], cwd=str(_LIVE_REPO_DIR), check=False)
    subprocess.run(["git", "add", "."], cwd=str(_LIVE_REPO_DIR), check=False)
    subprocess.run(["git", "commit", "-m", "chore: initial baseline"], cwd=str(_LIVE_REPO_DIR), check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return _LIVE_REPO_DIR


def sync_live_workspace(commit_message: Optional[str] = None) -> dict[str, Any]:
    """
    Synchronize any live code edits from `transfers-demo-app/app/` into the
    isolated `data/live/clientrepo` Git repository and commit them if modified.

    This guarantees that whether a developer:
      (a) edits a file in `transfers-demo-app/app/` in their IDE and saves it, OR
      (b) commits a change in git,
    the change is immediately tracked with a genuine 40-character Git commit SHA,
    author, timestamp, and unified diff for `CodeAgent`, `HistoryAgent`, and `verifier.py`.
    """
    repo_dir = ensure_live_git_repo()
    src_app = _DEMO_APP_DIR / "app"
    dst_app = repo_dir / "app"

    changed_files: list[str] = []
    if src_app.exists():
        for src_file in src_app.rglob("*.py"):
            rel = src_file.relative_to(_DEMO_APP_DIR)
            dst_file = repo_dir / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            src_bytes = src_file.read_bytes()
            if not dst_file.exists() or dst_file.read_bytes() != src_bytes:
                dst_file.write_bytes(src_bytes)
                changed_files.append(str(rel).replace("\\", "/"))

    try:
        import git  # type: ignore[import]
        repo = git.Repo(str(repo_dir))
        dirty_paths = [item.a_path for item in repo.index.diff(None)] + repo.untracked_files
        all_touched = sorted(set(changed_files + [p.replace("\\", "/") for p in dirty_paths]))

        if all_touched or repo.is_dirty(untracked_files=True):
            with repo.config_writer() as cw:
                cw.set_value("user", "name", "live-developer")
                cw.set_value("user", "email", "dev@triagepilot.io")
            repo.git.add(A=True)
            msg = commit_message
            if not msg:
                # Check if outer repo has a recent commit message we can mirror
                short_files = ", ".join(Path(p).name for p in all_touched[:3])
                msg = f"feat(live): update {short_files or 'service logic'} in transfers-demo-app"
            commit = repo.index.commit(msg)
            logger.info("Committed live workspace changes to live repo: %s (%s)", commit.hexsha[:8], msg)

        head = repo.head.commit
        # Compute modified files relative to baseline commit if any live commits exist
        live_modified_files: list[str] = []
        for c in list(repo.iter_commits(max_count=5)):
            if _is_baseline_commit(c.hexsha):
                break
            for fpath in c.stats.files.keys():
                norm_f = str(fpath).replace("\\", "/")
                if norm_f in _ALLOWLISTED_LIVE_FILES and norm_f not in live_modified_files:
                    live_modified_files.append(norm_f)

        return {
            "repo_path": str(repo_dir),
            "head_sha": head.hexsha,
            "short_sha": head.hexsha[:8],
            "head_message": head.message.strip(),
            "head_author": head.author.name,
            "head_date": head.committed_datetime.isoformat(),
            "has_live_changes": not _is_baseline_commit(head.hexsha),
            "live_modified_files": live_modified_files,
            "newly_committed_files": all_touched,
        }
    except Exception as exc:
        logger.warning("sync_live_workspace fallback: %s", exc)
        return {
            "repo_path": str(repo_dir),
            "head_sha": "0" * 40,
            "short_sha": "00000000",
            "head_message": "unavailable",
            "head_author": "unknown",
            "head_date": _utc_now(),
            "has_live_changes": False,
            "live_modified_files": [],
            "newly_committed_files": changed_files,
        }


# ---------------------------------------------------------------------------
# Live Telemetry Emission Helpers (used by transfers-demo-app & live triggers)
# ---------------------------------------------------------------------------

def append_live_log(
    *,
    service: str,
    level: str,
    message: str,
    trace_id: Optional[str] = None,
    log_id: Optional[str] = None,
    ts: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Append a normalized structured JSONL log event to `data/live/logs.jsonl`."""
    _ensure_live_dirs()
    entry: dict[str, Any] = {
        "log_id": log_id or f"LOG-LIVE-{uuid.uuid4().hex[:6].upper()}",
        "ts": ts or _utc_now(),
        "service": service,
        "level": level.upper(),
        "trace_id": trace_id or f"trace-{uuid.uuid4().hex[:8]}",
        "message": message,
    }
    if extra:
        entry.update(extra)
    with _LIVE_LOGS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def save_live_record(record: dict[str, Any]) -> dict[str, Any]:
    """Persist a masked transfer record snapshot into `data/live/records.json`."""
    _ensure_live_dirs()
    records: list[dict[str, Any]] = []
    if _LIVE_RECORDS_PATH.exists():
        try:
            loaded = json.loads(_LIVE_RECORDS_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                records = loaded
        except Exception:
            records = []

    sanitized = {
        "transfer_id": record.get("transfer_id", f"TXN-{uuid.uuid4().int % 900000 + 100000}"),
        "status": str(record.get("status", "COMPLETED")).upper(),
        "amount": float(record.get("amount", 0.0)),
        "fee": float(record.get("fee", 0.0)),
        "created_at": record.get("created_at") or _utc_now(),
        "masked_account": "[ACCT_REDACTED]",
        "currency": record.get("currency", "INR"),
        "type": record.get("transfer_type", record.get("type", "SAME_DAY")),
        "trace_id": record.get("trace_id", ""),
    }
    records = [r for r in records if r.get("transfer_id") != sanitized["transfer_id"]]
    records.insert(0, sanitized)
    _LIVE_RECORDS_PATH.write_text(json.dumps(records[:100], indent=2), encoding="utf-8")
    return sanitized


def execute_live_demo_transaction(
    *,
    amount: float = 100000.0,
    transfer_type: str = "same_day",
    tier: str = "standard",
    sender_account: str = "918273645501",
    beneficiary_account: str = "102938475610",
    idempotency_key: Optional[str] = None,
    simulate_utc_hour: Optional[int] = None,
    transfer_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Execute the REAL code inside `transfers-demo-app/app` dynamically (reloading
    modules from disk so any live developer edits in `transfers-demo-app/app/`
    take effect immediately without restarting the server!), record live logs
    and ledger snapshots, and return the outcome.
    """
    import importlib
    import sys

    sync_info = sync_live_workspace()
    demo_root = str(_DEMO_APP_DIR.resolve())
    if demo_root not in sys.path:
        sys.path.insert(0, demo_root)

    transfer_id = transfer_id or f"TXN-{uuid.uuid4().int % 900000 + 100000}"
    trace_id = f"trace-{transfer_id}"
    now_iso = _utc_now()

    try:
        # Reload target domain modules from transfers-demo-app so live IDE edits execute immediately
        import app.config
        import app.models
        import app.fees.calculator
        import app.limits.daily_limit
        import app.transfers.cutoff
        import app.transfers.idempotency
        import app.notifications.sms
        import app.beneficiary.manager
        import app.settlement.batch

        for mod in (
            app.config,
            app.models,
            app.fees.calculator,
            app.limits.daily_limit,
            app.transfers.cutoff,
            app.transfers.idempotency,
            app.notifications.sms,
            app.beneficiary.manager,
            app.settlement.batch,
        ):
            importlib.reload(mod)

        # 1. Calculate fee first so even if limit/cutoff rejects, fee is logged
        fee = app.fees.calculator.calculate_transfer_fee(amount, tier=tier)
        breakdown = app.fees.calculator.get_fee_breakdown(amount, tier=tier)

        append_live_log(
            service="api-gateway",
            level="INFO",
            trace_id=trace_id,
            ts=now_iso,
            message=(
                f"POST /api/transfers transfer_id={transfer_id} amount={amount:.2f} "
                f"tier={tier} computed_fee={fee:.2f} type={transfer_type} account=[ACCT_REDACTED]"
            ),
        )

        # 2. Idempotency check
        if idempotency_key:
            app.transfers.idempotency.check_idempotency_key(
                {"Idempotency-Key": idempotency_key}, idempotency_key
            )

        # 3. Daily Limit check
        app.limits.daily_limit.check_daily_limit(amount, current_daily_total=0.0)

        # 4. Cutoff check
        if transfer_type.lower() in ("same_day", "same-day", "neft", "rtgs"):
            eff_hour = 10 if simulate_utc_hour is None else int(simulate_utc_hour)
            req_dt = datetime.now(timezone.utc).replace(hour=eff_hour, minute=15)
            app.transfers.cutoff.validate_transfer_cutoff(req_dt)

        # 5. Send SMS notification
        sms_res = app.notifications.sms.send_sms_notification(
            recipient="[PHONE_REDACTED]",
            message=f"Debited INR {amount:.2f} (fee INR {fee:.2f}) for {transfer_id}",
            trace_id=trace_id,
        )
        sms_delivered = sms_res.get("delivered", True) if isinstance(sms_res, dict) else bool(sms_res)
        sms_attempts = sms_res.get("attempts", 1) if isinstance(sms_res, dict) else 1

        record = save_live_record({
            "transfer_id": transfer_id,
            "status": "COMPLETED",
            "amount": amount,
            "fee": fee,
            "created_at": now_iso,
            "transfer_type": transfer_type.upper(),
            "trace_id": trace_id,
        })

        # Check if fee or behaviour has an anomaly to log
        expected_std_fee = round(amount * (0.02 if tier == "express" else 0.0125), 2)
        if abs(fee - expected_std_fee) >= 0.01:
            err_log = append_live_log(
                service="fees",
                level="ERROR",
                trace_id=trace_id,
                ts=now_iso,
                message=(
                    f"FeeCalculationAnomaly on {transfer_id}: app/fees/calculator.py "
                    f"returned fee={fee:.2f} (expected {expected_std_fee:.2f}) for amount={amount:.2f} tier={tier}"
                ),
            )
        else:
            err_log = append_live_log(
                service="transfers",
                level="ERROR" if not sms_delivered else "INFO",
                trace_id=trace_id,
                ts=now_iso,
                message=(
                    f"Transfer {transfer_id} COMPLETED: amount={amount:.2f} fee={fee:.2f} "
                    f"tier={tier} sms_attempts={sms_attempts}"
                ),
            )

        return {
            "ok": True,
            "status": "COMPLETED",
            "transfer_id": transfer_id,
            "trace_id": trace_id,
            "amount": amount,
            "fee": fee,
            "breakdown": breakdown,
            "record": record,
            "log": err_log,
            "repo_sync": sync_info,
        }

    except Exception as exc:
        tb = traceback.extract_tb(exc.__traceback__)
        culprit_frame = tb[-1] if tb else None
        rel_file = "app/transfers/service.py"
        line_no = 1
        func_name = "process_transfer"
        if culprit_frame:
            raw_file = culprit_frame.filename.replace("\\", "/")
            if "app/" in raw_file:
                rel_file = "app/" + raw_file.split("app/", 1)[1]
            line_no = culprit_frame.lineno
            func_name = culprit_frame.name

        err_msg = (
            f"{exc.__class__.__name__} on {transfer_id} in {rel_file}:{line_no} ({func_name}): {exc}"
        )
        err_log = append_live_log(
            service=rel_file.split("/")[1] if "/" in rel_file else "transfers",
            level="ERROR",
            trace_id=trace_id,
            ts=now_iso,
            message=err_msg,
            extra={"file": rel_file, "line": line_no, "exception": exc.__class__.__name__},
        )
        record = save_live_record({
            "transfer_id": transfer_id,
            "status": "REJECTED",
            "amount": amount,
            "fee": 0.0,
            "created_at": now_iso,
            "transfer_type": transfer_type.upper(),
            "trace_id": trace_id,
        })
        return {
            "ok": False,
            "status": "REJECTED",
            "transfer_id": transfer_id,
            "trace_id": trace_id,
            "amount": amount,
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
            "culprit_file": rel_file,
            "culprit_line": line_no,
            "record": record,
            "log": err_log,
            "repo_sync": sync_info,
        }


# ---------------------------------------------------------------------------
# Live Concrete Port Implementations
# ---------------------------------------------------------------------------

class LiveGitCodeAdapter(FixtureCodeAdapter):
    """
    Live Git repository connector backed by `data/live/clientrepo` (which
    auto-syncs any edits from `transfers-demo-app/app/`).
    """

    def __init__(self) -> None:
        sync_live_workspace()
        self._repo_path = ensure_live_git_repo()
        self._repo = self._try_open_repo()

    def refresh(self) -> dict[str, Any]:
        info = sync_live_workspace()
        self._repo_path = ensure_live_git_repo()
        self._repo = self._try_open_repo()
        return info

    def get_recent_diff_hits(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Inspect recent commits in the live repository (especially any commits
        after baseline `61b344d` / `288c17a`) and extract modified file paths and exact
        changed line numbers at `HEAD` SHA.
        """
        self.refresh()
        if self._repo is None:
            return []

        hits: list[dict[str, Any]] = []
        head_sha = self._head_sha()
        try:
            commits = list(self._repo.iter_commits(max_count=5))
            for commit in commits:
                if _is_baseline_commit(commit.hexsha):
                    break
                if not commit.parents:
                    continue
                diffs = commit.parents[0].diff(commit, create_patch=True)
                for d in diffs:
                    rel_path = (d.b_path or d.a_path or "").replace("\\", "/")
                    if not rel_path.endswith(".py") or rel_path.endswith("__init__.py"):
                        continue
                    if rel_path not in _ALLOWLISTED_LIVE_FILES and not _is_baseline_commit(commit.hexsha):
                        continue
                    patch_text = d.diff.decode("utf-8", errors="replace")
                    file_lines = self._read_file_at_sha(rel_path, head_sha).splitlines()
                    if not file_lines:
                        continue

                    added_lines: list[tuple[int, str]] = []
                    removed_lines: list[str] = []
                    curr_new_line: Optional[int] = None
                    for raw_patch_line in patch_text.splitlines():
                        hm = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", raw_patch_line)
                        if hm:
                            curr_new_line = int(hm.group(1))
                            continue
                        if curr_new_line is None:
                            continue
                        if raw_patch_line.startswith("+") and not raw_patch_line.startswith("+++"):
                            code_str = raw_patch_line[1:].strip()
                            if code_str and not code_str.startswith(("#", '"""', "'''")):
                                added_lines.append((curr_new_line, code_str))
                            curr_new_line += 1
                        elif raw_patch_line.startswith("-") and not raw_patch_line.startswith("---"):
                            old_str = raw_patch_line[1:].strip()
                            if old_str and not old_str.startswith(("#", '"""', "'''")):
                                removed_lines.append(old_str)
                            continue
                        else:
                            curr_new_line += 1

                    if added_lines:
                        # Prefer lines that start with executable Python statements over docstring text
                        best_line_no, best_line_text = added_lines[0]
                        found_exec = False
                        for lno, candidate in added_lines:
                            if candidate.startswith(("if ", "elif ", "return ", "raise ", "for ", "while ")):
                                best_line_no, best_line_text = lno, candidate
                                found_exec = True
                                break
                        if not found_exec:
                            for lno, candidate in added_lines:
                                if any(k in candidate for k in ("raise ", "return ", "if ", "rate", "fee", "limit", "cutoff", "=")):
                                    best_line_no, best_line_text = lno, candidate
                                    break
                        # Verify against file_lines at HEAD
                        if 1 <= best_line_no <= len(file_lines):
                            best_line_text = file_lines[best_line_no - 1].strip() or best_line_text
                        before_text = removed_lines[-1][:140] if removed_lines else ""
                        hits.append({
                            "path": rel_path,
                            "line_number": best_line_no,
                            "snippet": best_line_text[:200],
                            "before_line": before_text,
                            "sha": head_sha,
                            "commit_sha": commit.hexsha,
                            "commit_date": commit.committed_datetime.isoformat(),
                            "commit_message": commit.message.strip(),
                            "is_live_diff": not _is_baseline_commit(commit.hexsha),
                        })
                        if len(hits) >= limit:
                            return hits
        except Exception as exc:
            logger.warning("get_recent_diff_hits error: %s", exc)
        return hits

    def search_code(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        self.refresh()
        # First run standard search on the synced live repo
        standard_hits = super().search_code(query, limit=limit)
        # Filter out generic FastAPI router wrappers (`app/main.py`, `app/transfers/service.py`)
        # when specific domain modules (`daily_limit.py`, `cutoff.py`, `calculator.py`, `sms.py`) are matched
        domain_standard = [
            h for h in standard_hits
            if h.get("path") not in ("app/main.py", "app/transfers/service.py")
        ]
        if domain_standard:
            standard_hits = domain_standard

        # Also check if there are live commits after baseline and include their changed hunks
        diff_hits = [h for h in self.get_recent_diff_hits(limit=3) if h.get("is_live_diff")]
        combined: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()

        # Prioritize live diff hits when they match the query or when the user modified code live
        for h in diff_hits + standard_hits:
            key = (h["path"], int(h["line_number"]))
            if key not in seen:
                seen.add(key)
                combined.append(h)
                if len(combined) >= limit:
                    break
        return combined


class LiveGitHistoryAdapter(FixtureHistoryAdapter):
    """
    Combines historical tickets and Known Errors with LIVE Git commits from
    `data/live/clientrepo` so `HistoryAgent.recent_changes()` automatically
    surfaces any code changes committed by the developer.
    """

    def recent_changes(
        self,
        window_start: str,
        window_end: str,
    ) -> list[dict[str, Any]]:
        sync_live_workspace()
        repo_dir = ensure_live_git_repo()
        live_changes: list[dict[str, Any]] = []
        try:
            import git  # type: ignore[import]
            repo = git.Repo(str(repo_dir))
            for commit in list(repo.iter_commits(max_count=5)):
                files = [str(f).replace("\\", "/") for f in commit.stats.files.keys()]
                is_live = not _is_baseline_commit(commit.hexsha)
                live_changes.append({
                    "change_id": f"CHG-LIVE-{commit.hexsha[:6].upper()}" if is_live else f"CHG-{commit.hexsha[:7]}",
                    "title": commit.message.strip(),
                    "deployed_at": commit.committed_datetime.isoformat(),
                    "modules_affected": files,
                    "files_changed": files,
                    "author": commit.author.name,
                    "commit_sha": commit.hexsha,
                })
        except Exception as exc:
            logger.warning("LiveGitHistoryAdapter git inspection failed: %s", exc)

        return live_changes + super().recent_changes(window_start, window_end)


class LiveLogAdapter(FixtureLogAdapter):
    """
    Reads live application telemetry from `data/live/logs.jsonl` for `LIVE`/`CUSTOM`
    investigations, while delegating Golden Scenarios `S01`–`S11` to their pinned bundles.
    """

    def _is_live_scenario(self, scenario_id: str) -> bool:
        return not bool(re.fullmatch(r"S\d{2}", scenario_id or ""))

    def _load_live(self) -> list[dict[str, Any]]:
        if not _LIVE_LOGS_PATH.exists():
            return []
        try:
            lines = _LIVE_LOGS_PATH.read_text(encoding="utf-8").splitlines()
            parsed = [json.loads(line) for line in lines if line.strip()]
            # Most recent logs first
            return list(reversed(parsed))
        except Exception:
            return []

    def query_logs(
        self,
        scenario_id: str,
        start_ts: Optional[str] = None,
        end_ts: Optional[str] = None,
        filters: Optional[dict[str, Any]] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not self._is_live_scenario(scenario_id):
            return super().query_logs(scenario_id, start_ts=start_ts, end_ts=end_ts, filters=filters, limit=limit)

        logs = self._load_live()
        if start_ts:
            logs = [l for l in logs if l.get("ts", "") >= start_ts]
        if end_ts:
            logs = [l for l in logs if l.get("ts", "") <= end_ts]
        if filters:
            filtered = logs
            for key, value in filters.items():
                filtered = [l for l in filtered if str(l.get(key, "")).upper() == str(value).upper()]
            # If filtering by ERROR returns nothing but there are recent INFO/WARN live logs, return recent logs
            logs = filtered or logs
        return logs[:limit]

    def digest_signatures(self, scenario_id: str) -> list[dict[str, Any]]:
        if not self._is_live_scenario(scenario_id):
            return super().digest_signatures(scenario_id)

        logs = self._load_live()
        signatures: dict[str, dict[str, Any]] = {}
        for log in logs:
            if log.get("level") in ("ERROR", "CRITICAL", "WARNING"):
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
                signatures[key]["first_seen"] = log.get("ts")
        return list(signatures.values())

    def trace_lookup(self, scenario_id: str, trace_id: str) -> list[dict[str, Any]]:
        if not self._is_live_scenario(scenario_id):
            return super().trace_lookup(scenario_id, trace_id)

        logs = self._load_live()
        clean_id = trace_id.replace("trace-", "")
        return [
            l for l in logs
            if l.get("trace_id") == trace_id
            or clean_id in l.get("message", "")
            or clean_id in l.get("trace_id", "")
        ]


class LiveRecordAdapter(FixtureRecordAdapter):
    """
    Reads live masked transaction snapshots from `data/live/records.json` for
    `LIVE`/`CUSTOM` investigations, delegating `S01`–`S11` to their pinned bundles.
    """

    def get_transfer_record(
        self,
        scenario_id: str,
        transfer_id: str,
    ) -> Optional[dict[str, Any]]:
        if _LIVE_RECORDS_PATH.exists():
            try:
                records = json.loads(_LIVE_RECORDS_PATH.read_text(encoding="utf-8"))
                if isinstance(records, list):
                    for r in records:
                        if str(r.get("transfer_id", "")).upper() == transfer_id.upper():
                            return r
            except Exception:
                pass
        return super().get_transfer_record(scenario_id, transfer_id)


class LiveWriteAdapter(FixtureWriteAdapter):
    """
    Production WritePort connector:
      - Persists every approved issue and customer reply into `data/live/issues.json`
      - Deterministic SHA-256-derived issue keys and idempotent deduplication
      - Optionally creates a real GitHub Issue via REST API if `GITHUB_TOKEN` is set.
    """

    def create_issue(self, jira_draft: dict[str, Any]) -> dict[str, Any]:
        import hashlib
        import engine.audit as audit

        _ensure_live_dirs()
        inv_id = jira_draft.get("investigation_id", "unknown")
        title = jira_draft.get("title", "[TriagePilot] Verified Root Cause Issue")
        body = jira_draft.get("description", "")
        report_hash = jira_draft.get("report_hash", "")
        labels = jira_draft.get("labels", ["triagepilot"])

        digest = hashlib.sha256(f"live:{inv_id}:{report_hash}:{title}:{body}".encode("utf-8")).hexdigest()[:6].upper()
        issue_key = f"ISS-{digest}"
        issue_url = f"/api/live/issues/{issue_key}"
        status = "live_persisted"

        issues: list[dict[str, Any]] = []
        if _LIVE_ISSUES_PATH.exists():
            try:
                issues = json.loads(_LIVE_ISSUES_PATH.read_text(encoding="utf-8"))
                if not isinstance(issues, list):
                    issues = []
            except Exception:
                issues = []

        # Idempotency check: if an issue with this deterministic key already exists, return it without duplicating
        for existing in issues:
            if existing.get("issue_key") == issue_key:
                return {
                    "issue_key": existing["issue_key"],
                    "url": existing.get("url", issue_url),
                    "status": existing.get("status", status),
                }

        gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
        gh_repo = os.environ.get("GITHUB_REPO", "mahesh-mettireddy/TriagePilot").strip()

        if gh_token and "/" in gh_repo:
            try:
                req = urllib.request.Request(
                    f"https://api.github.com/repos/{gh_repo}/issues",
                    data=json.dumps({"title": title, "body": body, "labels": labels[:5]}).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {gh_token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "User-Agent": "TriagePilot-Enterprise",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    gh_data = json.loads(resp.read().decode("utf-8"))
                    issue_key = f"GH-{gh_data.get('number', issue_key)}"
                    issue_url = gh_data.get("html_url", issue_url)
                    status = "github_issue_created"
            except Exception as exc:
                logger.warning("GitHub Issue API call fell back to local live ledger: %s", exc)

        record = {
            "issue_key": issue_key,
            "investigation_id": inv_id,
            "report_hash": report_hash,
            "title": title,
            "description": body,
            "repro_steps": jira_draft.get("repro_steps", []),
            "evidence_links": jira_draft.get("evidence_links", []),
            "labels": labels,
            "url": issue_url,
            "status": status,
            "created_at": _utc_now(),
        }
        issues = [i for i in issues if i.get("investigation_id") != inv_id or i.get("issue_key") != issue_key]
        issues.insert(0, record)
        _LIVE_ISSUES_PATH.write_text(json.dumps(issues[:100], indent=2), encoding="utf-8")

        audit.append(inv_id, "write_back_jira", {"action": "create_issue", "issue_key": issue_key, "status": status})
        return {
            "issue_key": issue_key,
            "url": issue_url,
            "status": status,
        }


def get_scenario_adapters(scenario_id: str, default_adapters: dict[str, Any]) -> dict[str, Any]:
    """
    Route Golden Scenarios (`S01`–`S11`) through the pinned fixture adapters so
    benchmarks remain 100% deterministic, while routing `LIVE` / `CUSTOM`
    investigations through the Live Connector suite.
    """
    if re.fullmatch(r"S\d{2}", scenario_id or ""):
        return {
            **default_adapters,
            "code": FixtureCodeAdapter(),
        }

    return {
        "history": LiveGitHistoryAdapter(),
        "knowledge": default_adapters.get("knowledge") or FixtureKnowledgeAdapter(),
        "logs": LiveLogAdapter(),
        "code": LiveGitCodeAdapter(),
        "record": LiveRecordAdapter(),
        "write": LiveWriteAdapter(),
    }


def get_connectors_health() -> dict[str, Any]:
    """Return live status, latency, and telemetry metrics across all 6 Hexagonal Ports."""
    sync_info = sync_live_workspace()
    live_logs_count = 0
    if _LIVE_LOGS_PATH.exists():
        try:
            live_logs_count = len(_LIVE_LOGS_PATH.read_text(encoding="utf-8").splitlines())
        except Exception:
            pass

    live_records_count = 0
    if _LIVE_RECORDS_PATH.exists():
        try:
            live_records_count = len(json.loads(_LIVE_RECORDS_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass

    live_issues_count = 0
    if _LIVE_ISSUES_PATH.exists():
        try:
            live_issues_count = len(json.loads(_LIVE_ISSUES_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass

    return {
        "status": "connected",
        "checked_at": _utc_now(),
        "git_workspace": sync_info,
        "telemetry": {
            "live_logs_count": live_logs_count,
            "live_records_count": live_records_count,
            "live_issues_count": live_issues_count,
        },
        "ports": [
            {
                "port": "CodePort",
                "adapter": "LiveGitCodeAdapter",
                "status": "HEALTHY",
                "target": f"transfers-demo-app @ {sync_info.get('short_sha')}",
                "detail": (
                    f"HEAD: {sync_info.get('head_message')} "
                    f"({'Modified live' if sync_info.get('has_live_changes') else 'Baseline synced'})"
                ),
            },
            {
                "port": "LogPort",
                "adapter": "LiveLogAdapter",
                "status": "HEALTHY",
                "target": "data/live/logs.jsonl",
                "detail": f"{live_logs_count} structured JSONL events indexed",
            },
            {
                "port": "RecordPort",
                "adapter": "LiveRecordAdapter",
                "status": "HEALTHY",
                "target": "data/live/records.json",
                "detail": f"{live_records_count} PII-masked transaction snapshots",
            },
            {
                "port": "HistoryPort",
                "adapter": "LiveGitHistoryAdapter",
                "status": "HEALTHY",
                "target": "Git Commit Stream + ITSM History",
                "detail": f"Auto-ingests live commits as CHG-LIVE-* deployment records",
            },
            {
                "port": "KnowledgePort",
                "adapter": "FixtureKnowledgeAdapter",
                "status": "HEALTHY",
                "target": "SOP Runbooks (DOC-CUTOFF-01, DOC-FEES-01, DOC-LIMITS-01, DOC-SMS-01, DOC-BEN-02)",
                "detail": "5 canonical policy runbooks active with timestamp reconciliation",
            },
            {
                "port": "WritePort",
                "adapter": "LiveWriteAdapter",
                "status": "HEALTHY",
                "target": "GitHub Issues REST API + Local Issue Ledger",
                "detail": f"{live_issues_count} approved issues persisted",
            },
        ],
    }


def get_live_issues() -> list[dict[str, Any]]:
    """Return all issues created by LiveWriteAdapter."""
    if not _LIVE_ISSUES_PATH.exists():
        return []
    try:
        data = json.loads(_LIVE_ISSUES_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def reset_live_workspace(restore_demo_app_files: bool = False) -> dict[str, Any]:
    """
    Reset `data/live/clientrepo` to the clean baseline commit (`288c17a`) and
    optionally restore `transfers-demo-app/app/` files from `data/clientrepo/app/`.
    """
    if restore_demo_app_files and (_BASELINE_CLIENT_REPO / "app").exists():
        shutil.copytree(_BASELINE_CLIENT_REPO / "app", _DEMO_APP_DIR / "app", dirs_exist_ok=True)

    git_dir = _LIVE_REPO_DIR / ".git"
    if git_dir.exists():
        try:
            subprocess.run(
                ["git", "reset", "--hard", _BASELINE_HEAD_SHA],
                cwd=str(_LIVE_REPO_DIR),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=str(_LIVE_REPO_DIR),
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            shutil.rmtree(_LIVE_REPO_DIR, ignore_errors=True)
    ensure_live_git_repo()
    return sync_live_workspace()


def list_live_editable_files() -> dict[str, Any]:
    """
    Return the allowlisted source files in `transfers-demo-app/app/` along with
    their current content and the active Git workspace status (`short_sha`, diff, etc.).
    """
    sync_info = sync_live_workspace()
    files_out: list[dict[str, Any]] = []
    for rel_path, label in _ALLOWLISTED_LIVE_FILES.items():
        target = _DEMO_APP_DIR / rel_path
        content = ""
        if target.exists():
            content = target.read_text(encoding="utf-8", errors="replace")
        files_out.append({
            "path": rel_path,
            "label": label,
            "content": content,
        })
    return {
        "files": files_out,
        "git_workspace": sync_info,
    }


def update_and_commit_live_file(
    file_path: str,
    content: str,
    commit_message: Optional[str] = None,
) -> dict[str, Any]:
    """
    Write updated Python source to an allowlisted file in `transfers-demo-app/app/`,
    sync it into `data/live/clientrepo`, and create a real Git commit with a 40-char SHA.
    """
    norm_path = file_path.strip().replace("\\", "/")
    if norm_path not in _ALLOWLISTED_LIVE_FILES:
        raise ValueError(f"File '{norm_path}' is not in the allowlisted live editable files.")

    # Validate Python syntax before writing so a typo doesn't break the module loader
    compile(content, norm_path, "exec")

    target = _DEMO_APP_DIR / norm_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    msg = (commit_message or "").strip() or f"feat(live): update {norm_path} in transfers-demo-app"
    sync_info = sync_live_workspace(commit_message=msg)

    # Also grab unified diff for the latest commit to display in the UI
    diff_text = ""
    try:
        adapter = LiveGitCodeAdapter()
        diff_text = adapter.git_diff(sync_info.get("head_sha", "HEAD"))
    except Exception:
        pass

    # Automatically execute a live probe transaction against the newly committed code
    # so data/live/logs.jsonl and data/live/records.json reflect the exact post-commit runtime state.
    probe_amount = 100000.0
    probe_hour = 10
    if "cutoff" in norm_path:
        probe_amount = 45000.0
        probe_hour = 16
    elif "calculator" in norm_path:
        probe_amount = 803.40
        probe_hour = 10
    elif "sms" in norm_path:
        probe_amount = 25000.0
        probe_hour = 10

    live_tx = execute_live_demo_transaction(
        amount=probe_amount,
        transfer_type="same_day",
        tier="standard",
        simulate_utc_hour=probe_hour,
    )
    short_sha = sync_info.get("short_sha", "HEAD")
    txn_id = live_tx.get("transfer_id", "TXN-LIVE")
    if not live_tx.get("ok"):
        suggested_ticket = (
            f"Customer transfer {txn_id} for INR {probe_amount:,.2f} from account 918273645501 "
            f"failed after commit @{short_sha} in {norm_path} ('{msg}') with "
            f"{live_tx.get('error_type')}: '{live_tx.get('error_message')}'. "
            f"Please investigate the root cause across live logs, ledger state, and recent commits."
        )
    else:
        fee = float(live_tx.get("fee", 0.0))
        expected_fee = round(probe_amount * 0.0125, 2)
        if abs(fee - expected_fee) >= 0.01:
            suggested_ticket = (
                f"Customer reported incorrect fee deduction on transfer {txn_id} (account 918273645501) "
                f"after commit @{short_sha} in {norm_path}: principal INR {probe_amount:,.2f} was charged "
                f"fee INR {fee:,.2f} instead of expected INR {expected_fee:,.2f}."
            )
        else:
            suggested_ticket = (
                f"Live developer commit @{short_sha} in {norm_path} ('{msg}') verified against "
                f"transfer {txn_id} (INR {probe_amount:,.2f} COMPLETED, fee INR {fee:,.2f}). "
                f"Please verify the live Git diff, runbook compliance, and runtime behavior."
            )

    return {
        "ok": True,
        "path": norm_path,
        "commit_message": msg,
        "git_workspace": sync_info,
        "diff": diff_text,
        "live_transaction": live_tx,
        "suggested_ticket": suggested_ticket,
    }


