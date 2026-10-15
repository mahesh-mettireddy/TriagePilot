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

  source.onmessage = (e) => {
    try {
      const parsed = JSON.parse(e.data);
      onEvent(parsed);
      if (parsed.type === 'report_ready' || parsed.type === 'error') {
        // Allow a short buffer for awaiting_approval or other trailing events
        setTimeout(() => {
          source.close();
          onComplete();
        }, 500);
      }
    } catch (err) {
      console.error('Error parsing SSE event', err);
    }
  };

  source.onerror = (err) => {
    source.close();
    if (onError) onError(err);
    else onComplete();
  };

  return () => {
    source.close();
  };
}
