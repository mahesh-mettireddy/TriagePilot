import {
  AuditChainEntry,
  HumanDecision,
  InvestigationCreateRequest,
  ReadinessStatus,
  ReportOutput,
  ScenarioMeta,
  SSEEvent,
} from './types';

const API_BASE = '/api';

export async function getReadiness(): Promise<ReadinessStatus> {
  const res = await fetch('/readyz');
  if (!res.ok) throw new Error('Failed to fetch readiness');
  return res.json();
}

export async function getScenarios(): Promise<ScenarioMeta[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error('Failed to load scenarios');
  return res.json();
}

export async function getProfile(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/profile`);
  if (!res.ok) throw new Error('Failed to load profile');
  return res.json();
}

export async function getEvalResults(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/eval/results`);
  if (!res.ok) throw new Error('Failed to load eval results');
  return res.json();
}

export async function runEvaluationSuite(
  executionMode: 'live_evaluation' | 'replay_evaluation' = 'live_evaluation'
): Promise<Record<string, any>> {
  const res = await fetch(
    `${API_BASE}/eval/run?execution_mode=${encodeURIComponent(executionMode)}`,
    { method: 'POST' }
  );
  if (!res.ok) throw new Error('Failed to run evaluation benchmark');
  return res.json();
}

export async function verifyAudit(): Promise<{ valid: boolean; entries_checked: number; message: string }> {
  const res = await fetch(`${API_BASE}/audit/verify`);
  if (!res.ok) throw new Error('Failed to verify audit chain');
  return res.json();
}

export async function getAuditChain(investigationId?: string): Promise<AuditChainEntry[]> {
  const url = investigationId
    ? `${API_BASE}/audit/chain?investigation_id=${encodeURIComponent(investigationId)}`
    : `${API_BASE}/audit/chain`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch audit chain');
  return res.json();
}

export async function startInvestigation(req: InvestigationCreateRequest): Promise<string> {
  const res = await fetch(`${API_BASE}/investigations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error('Failed to start investigation');
  const data = await res.json();
  return data.id;
}

export async function getInvestigationReport(id: string): Promise<ReportOutput> {
  const res = await fetch(`${API_BASE}/investigations/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error('Investigation not found or not ready');
  return res.json();
}

export async function submitDecision(id: string, decision: HumanDecision): Promise<ReportOutput> {
  const res = await fetch(`${API_BASE}/investigations/${encodeURIComponent(id)}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(decision),
  });
  if (!res.ok) throw new Error('Failed to submit decision');
  return res.json();
}

export async function getConnectorsStatus(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/connectors/status`);
  if (!res.ok) throw new Error('Failed to fetch connectors status');
  return res.json();
}

export async function syncLiveRepo(commitMessage?: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/live/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(commitMessage ? { commit_message: commitMessage } : {}),
  });
  if (!res.ok) throw new Error('Failed to sync live repository');
  return res.json();
}

export async function getLiveEditableFiles(): Promise<{
  files: Array<{ path: string; label: string; content: string }>;
  git_workspace: Record<string, any>;
}> {
  const res = await fetch(`${API_BASE}/live/files`);
  if (!res.ok) throw new Error('Failed to load live editable files');
  return res.json();
}

export async function commitLiveFileEdit(payload: {
  path: string;
  content: string;
  commit_message?: string;
}): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/live/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to commit live code edit');
  }
  return res.json();
}

export async function resetLiveRepo(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/live/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ restore_demo_app_files: true }),
  });
  if (!res.ok) throw new Error('Failed to reset live repository');
  return res.json();
}

export async function triggerLiveTransaction(payload: {
  amount?: number;
  transfer_type?: string;
  tier?: string;
  simulate_utc_hour?: number;
}): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/live/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to execute live transaction');
  return res.json();
}

export async function getA2AAgentCard(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/a2a/agent-card`);
  if (!res.ok) throw new Error('Failed to fetch A2A Agent Card');
  return res.json();
}

export async function sendA2ATask(text: string, scenarioId: string = 'LIVE'): Promise<Record<string, any>> {
  const res = await fetch('/a2a/tasks/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: `a2a-${Date.now()}`,
      method: 'tasks/send',
      params: {
        id: `task-${Date.now()}`,
        scenario_id: scenarioId,
        message: {
          role: 'user',
          parts: [{ type: 'text', text }],
        },
      },
    }),
  });
  if (!res.ok) throw new Error('Failed to send A2A task');
  return res.json();
}

export async function getLiveIssues(): Promise<Array<Record<string, any>>> {
  const res = await fetch(`${API_BASE}/live/issues`);
  if (!res.ok) throw new Error('Failed to fetch live issues');
  return res.json();
}

export function subscribeToEvents(
  investigationId: string,
  onEvent: (event: SSEEvent) => void,
  onComplete: () => void,
  onError?: (err: any) => void
): () => void {
  const source = new EventSource(`${API_BASE}/investigations/${encodeURIComponent(investigationId)}/events`);
  let lastSeq = 0;
  let finished = false;
  let completionTimer: number | undefined;

  const handleMessage = (e: MessageEvent) => {
    try {
      const parsed = JSON.parse(e.data) as SSEEvent;
      if (typeof parsed.seq === 'number' && parsed.seq <= lastSeq) return;
      if (typeof parsed.seq === 'number') lastSeq = parsed.seq;
      onEvent(parsed);
      if (['awaiting_approval', 'policy_halted', 'error'].includes(parsed.type)) {
        finished = true;
        completionTimer = window.setTimeout(() => {
          source.close();
          onComplete();
        }, 250);
      }
    } catch (err) {
      console.error('Error parsing SSE event', err);
    }
  };

  // The backend uses named SSE events.  onmessage only receives the default
  // `message` event, so register listeners for the typed event contract.
  const eventTypes = [
    'masking_done', 'plan_created', 'agent_skipped', 'tool_started',
    'tool_finished', 'card_added', 'verifier_result', 'contradiction_found',
    'hypothesis_update', 'trust_update', 'abstain', 'report_ready',
    'awaiting_approval', 'awaiting_human', 'decision', 'write_back_done',
    'replay_fallback', 'tool_budget_rejected', 'adk_orchestration',
    'policy_halted', 'writeback_blocked', 'conclusion_withdrawn', 'error',
  ];
  eventTypes.forEach((eventType) => source.addEventListener(eventType, handleMessage));
  source.onmessage = handleMessage;

  source.onerror = (err) => {
    if (finished) {
      source.close();
      onComplete();
      return;
    }
    // Leave the EventSource open so the browser reconnects using
    // Last-Event-ID.  A transient proxy/network error is not a completed
    // investigation and must not discard the timeline.
    if (onError) onError(err);
  };

  return () => {
    if (completionTimer !== undefined) window.clearTimeout(completionTimer);
    source.close();
  };
}
