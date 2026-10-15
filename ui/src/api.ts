import {
  AuditChainEntry,
  HumanDecision,
  InvestigationCreateRequest,
  ReportOutput,
  ScenarioMeta,
  SSEEvent,
} from './types';

const API_BASE = '/api';

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
    'policy_halted', 'writeback_blocked', 'error',
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
