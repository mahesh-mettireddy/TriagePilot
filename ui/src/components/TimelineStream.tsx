import React, { useRef, useEffect, useState, useMemo } from 'react';
import { SSEEvent, Contradiction } from '../types';
import {
  Activity,
  ShieldCheck,
  Zap,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Layers,
  Clock,
  Filter,
} from 'lucide-react';

interface TimelineStreamProps {
  events: SSEEvent[];
  contradictions?: Contradiction[];
  isStreaming?: boolean;
}

const MILESTONE_TYPES = new Set([
  'masking_done',
  'ticket_masked',
  'plan_created',
  'routing_decided',
  'verifier_result',
  'evidence_verified',
  'contradiction_found',
  'contradiction_detected',
  'hypothesis_update',
  'hypotheses_ranked',
  'trust_update',
  'trust_evaluated',
  'abstain',
  'report_ready',
  'policy_halted',
  'awaiting_approval',
  'decision',
  'write_back_done',
]);

export const TimelineStream: React.FC<TimelineStreamProps> = ({
  events,
  contradictions = [],
  isStreaming = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [filterMode, setFilterMode] = useState<'all' | 'milestones' | 'alerts'>('all');

  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => (a.seq || 0) - (b.seq || 0));
  }, [events]);

  const filteredEvents = useMemo(() => {
    if (filterMode === 'milestones') {
      return sortedEvents.filter((e) => MILESTONE_TYPES.has(e.type));
    }
    if (filterMode === 'alerts') {
      return sortedEvents.filter((e) =>
        [
          'contradiction_found',
          'contradiction_detected',
          'evidence_dropped',
          'tool_budget_rejected',
          'abstain',
          'policy_halted',
          'writeback_blocked',
          'error',
        ].includes(e.type) ||
        (e.type === 'masking_done' && e.data?.injection_detected) ||
        (e.type === 'verifier_result' && (e.data?.dropped_count ?? 0) > 0)
      );
    }
    return sortedEvents;
  }, [sortedEvents, filterMode]);

  useEffect(() => {
    if (containerRef.current && isStreaming) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [filteredEvents.length, isStreaming]);

  const getEventMeta = (type: string) => {
    switch (type) {
      case 'ticket_masked':
      case 'masking_done':
        return { stage: 'STAGE 01', label: 'PII Redaction & Injection Guard', color: 'text-sky-400', bg: 'bg-sky-950/40 border-sky-500/30', icon: ShieldCheck };
      case 'leak_check_passed':
        return { stage: 'STAGE 08', label: 'Anti-Leak Output Sanitizer', color: 'text-emerald-400', bg: 'bg-emerald-950/40 border-emerald-500/30', icon: ShieldCheck };
      case 'routing_decided':
      case 'plan_created':
        return { stage: 'STAGE 02', label: 'Dynamic Router & Agent Pruning', color: 'text-purple-400', bg: 'bg-purple-950/40 border-purple-500/30', icon: Zap };
      case 'adk_orchestration':
        return { stage: 'STAGE 03', label: 'Specialist Swarm Dispatched', color: 'text-cyan-400', bg: 'bg-cyan-950/40 border-cyan-500/30', icon: Activity };
      case 'agent_skipped':
        return { stage: 'STAGE 02', label: 'Specialist Agent Pruned', color: 'text-slate-400', bg: 'bg-slate-900/80 border-slate-800', icon: Zap };
      case 'specialist_spawned':
      case 'tool_started':
        return { stage: 'STAGE 03', label: 'Read-Port Adapter Invoked', color: 'text-cyan-400', bg: 'bg-slate-950/80 border-cyan-500/20', icon: Activity };
      case 'specialist_evidence':
      case 'card_added':
        return { stage: 'STAGE 03', label: 'Evidentiary Pointer Collected', color: 'text-indigo-400', bg: 'bg-indigo-950/35 border-indigo-500/25', icon: Search };
      case 'tool_finished':
        return { stage: 'STAGE 03', label: 'Specialist Adapter Completed', color: 'text-teal-400', bg: 'bg-teal-950/30 border-teal-500/20', icon: CheckCircle2 };
      case 'evidence_verified':
      case 'verifier_result':
        return { stage: 'STAGE 04', label: 'Deterministic AST & Log Verifier', color: 'text-emerald-400', bg: 'bg-emerald-950/45 border-emerald-500/35', icon: CheckCircle2 };
      case 'evidence_dropped':
      case 'tool_budget_rejected':
        return { stage: 'STAGE 04', label: 'Unverified Claim Dropped', color: 'text-rose-400', bg: 'bg-rose-950/45 border-rose-500/35', icon: XCircle };
      case 'contradiction_detected':
      case 'contradiction_found':
        return { stage: 'STAGE 05', label: '4-Way Reality Contradiction Flagged', color: 'text-amber-400', bg: 'bg-amber-950/45 border-amber-500/35', icon: AlertTriangle };
      case 'hypotheses_ranked':
      case 'hypothesis_update':
        return { stage: 'STAGE 06', label: 'Root-Cause Hypotheses Ranked', color: 'text-teal-300', bg: 'bg-teal-950/45 border-teal-500/35', icon: Layers };
      case 'trust_evaluated':
      case 'trust_update':
        return { stage: 'STAGE 07', label: 'Mathematical Trust Gate Computed', color: 'text-violet-400', bg: 'bg-violet-950/45 border-violet-500/35', icon: Activity };
      case 'abstain':
        return { stage: 'STAGE 07', label: 'Principled Abstention Triggered', color: 'text-amber-400', bg: 'bg-amber-950/50 border-amber-500/40', icon: AlertTriangle };
      case 'report_ready':
        return { stage: 'STAGE 09', label: 'SHA-256 Bound Triage Report Ready', color: 'text-emerald-400', bg: 'bg-emerald-950/50 border-emerald-500/40', icon: FileText };
      case 'policy_halted':
        return { stage: 'STAGE 10', label: 'Policy Gate Halted Write-Back', color: 'text-rose-400', bg: 'bg-rose-950/50 border-rose-500/40', icon: ShieldCheck };
      case 'writeback_blocked':
        return { stage: 'STAGE 10', label: 'Write-Back Blocked by Policy', color: 'text-rose-400', bg: 'bg-rose-950/50 border-rose-500/40', icon: XCircle };
      case 'awaiting_approval':
      case 'awaiting_human':
        return { stage: 'STAGE 10', label: 'Awaiting Maker-Checker Sign-Off', color: 'text-amber-300', bg: 'bg-amber-950/40 border-amber-500/30', icon: Clock };
      case 'decision':
        return { stage: 'STAGE 10', label: 'Operator Decision Recorded', color: 'text-teal-400', bg: 'bg-teal-950/45 border-teal-500/35', icon: ShieldCheck };
      case 'write_back_done':
        return { stage: 'STAGE 10', label: 'Idempotent System Write-Back Complete', color: 'text-emerald-400', bg: 'bg-emerald-950/50 border-emerald-500/40', icon: CheckCircle2 };
      default:
        return { stage: 'EVENT', label: type, color: 'text-slate-300', bg: 'bg-slate-900 border-slate-800', icon: Activity };
    }
  };

  const renderEventDetail = (e: SSEEvent) => {
    const d = e.data || {};
    if (e.type === 'masking_done' || e.type === 'ticket_masked') {
      const count = d.pii_redacted_count ?? 0;
      const types = Array.isArray(d.redacted_types) && d.redacted_types.length > 0 ? ` [${d.redacted_types.join(', ')}]` : '';
      const inj = d.injection_detected ? ` • ⚠️ Prompt Injection Quarantined` : ' • Clean payload verified';
      return `Scrubbed ${count} sensitive PII token(s)${types}${inj}`;
    }
    if (e.type === 'plan_created' || e.type === 'routing_decided') {
      const active = Array.isArray(d.active_agents) ? d.active_agents.join(', ') : '';
      const skippedCount = d.skipped_agents ? Object.keys(d.skipped_agents).length : 0;
      return `Classified as ${d.ticket_class} (${d.severity}) • Dispatched [${active}] • Pruned ${skippedCount} unneeded agent(s)`;
    }
    if (e.type === 'agent_skipped') {
      return `${d.agent}: ${d.reason || 'Pruned by dynamic router'}`;
    }
    if (e.type === 'tool_started') {
      return `${d.agent} → invoking port method ${d.tool}()`;
    }
    if (e.type === 'card_added') {
      return `${d.agent} → extracted evidence pointer ${d.card_id}`;
    }
    if (e.type === 'tool_finished') {
      return `${d.agent} → ${d.tool}() returned ${d.cards ?? 0} candidate card(s)`;
    }
    if (e.type === 'verifier_result') {
      return `Verified ${d.verified_count ?? 0} grounded pointer(s) against source AST/logs • Dropped ${d.dropped_count ?? 0} unverified claim(s)`;
    }
    if (e.type === 'contradiction_found' || e.type === 'contradiction_detected') {
      return `[${d.kind}] ${d.note || ''}`;
    }
    if (e.type === 'hypothesis_update' || e.type === 'hypotheses_ranked') {
      const top = Array.isArray(d.hypotheses) && d.hypotheses[0];
      return top
        ? `Primary Hypothesis (${Math.round((top.score || 0) * 100)}% confidence): ${top.statement}`
        : 'Fast-path resolution or principled abstention (no speculative code hypothesis required)';
    }
    if (e.type === 'trust_update' || e.type === 'trust_evaluated') {
      return `Trust Score = ${Number(d.score || 0).toFixed(2)} (${d.band} Band) → Enforced Policy: ${d.policy_action}`;
    }
    if (e.type === 'abstain') {
      return d.rationale || 'Abstaining until client provides clarifying diagnostic details';
    }
    if (e.type === 'policy_halted') {
      return `${d.policy_action}: ${d.reason || 'Automated write-back halted by policy gate'}`;
    }
    if (e.type === 'report_ready') {
      return `Investigation ${d.investigation_id} cryptographically bound (SHA-256: ${(d.report_hash || '').slice(0, 16)}...)`;
    }
    if (e.type === 'write_back_done') {
      return `Idempotent write-back committed: ${JSON.stringify(d)}`;
    }
    if (d.specialist && d.claim) {
      return `[${d.specialist}] "${d.claim}"`;
    }
    return d.message || d.reason || d.claim || (d.status ? `Status: ${d.status}` : `Event ${e.type}`);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 flex flex-col shadow-xl">
      {/* Header with Filter Pills */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-teal-400" />
          <h3 className="font-bold text-xs uppercase tracking-wider text-slate-200">
            Execution Trace Stream
          </h3>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-950 text-teal-300 border border-slate-800">
            {filteredEvents.length} / {sortedEvents.length}
          </span>
          {isStreaming && (
            <span className="flex items-center gap-1.5 text-[10px] text-teal-300 font-mono bg-teal-950/80 px-2 py-0.5 rounded border border-teal-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-ping inline-block" />
              STREAMING SSE
            </span>
          )}
        </div>

        {/* Stream Filter Controls */}
        <div className="flex items-center gap-1 bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-[10px] font-medium">
          <Filter className="w-3 h-3 text-slate-500 ml-1.5 mr-0.5" />
          <button
            onClick={() => setFilterMode('all')}
            className={`px-2 py-1 rounded transition-colors ${
              filterMode === 'all' ? 'bg-teal-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({sortedEvents.length})
          </button>
          <button
            onClick={() => setFilterMode('milestones')}
            className={`px-2 py-1 rounded transition-colors ${
              filterMode === 'milestones' ? 'bg-teal-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Key Stages
          </button>
          <button
            onClick={() => setFilterMode('alerts')}
            className={`px-2 py-1 rounded transition-colors ${
              filterMode === 'alerts' ? 'bg-amber-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Conflicts &amp; Drops
          </button>
        </div>
      </div>

      {/* Contradictions Alert Box (if any detected) */}
      {contradictions.length > 0 && (
        <div className="mb-3 p-3 rounded-xl bg-amber-950/35 border border-amber-500/40 shrink-0 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-amber-300">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Cross-Source Reality Contradictions Detected ({contradictions.length})</span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-500/30">
              4-WAY RECONCILER
            </span>
          </div>
          <div className="grid grid-cols-1 gap-2">
            {contradictions.map((c, i) => (
              <div key={i} className="text-xs bg-slate-950/80 p-2.5 rounded-lg border border-amber-500/25 text-slate-200 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-500/30">
                    {c.kind}
                  </span>
                  <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                    {c.card_a && <span>Ref: {c.card_a}{c.card_b ? ` vs ${c.card_b}` : ''}</span>}
                    <span className="text-teal-400">
                      {c.deterministic ? '• Deterministic Python Check' : '• Semantic Pro Check'}
                    </span>
                  </div>
                </div>
                <p className="text-[11px] leading-relaxed text-slate-300">{c.note}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Events Log (No Truncation, Sorted by Sequence) */}
      <div ref={containerRef} className="overflow-y-auto space-y-2 pr-1 max-h-[380px]">
        {filteredEvents.length === 0 ? (
          <div className="text-center py-10 text-slate-500 text-xs bg-slate-950/40 rounded-lg border border-slate-800/60">
            {sortedEvents.length === 0
              ? 'Launch an investigation from the Ticket Queue to stream real-time execution steps.'
              : 'No events match the active filter.'}
          </div>
        ) : (
          filteredEvents.map((e) => {
            const meta = getEventMeta(e.type);
            const Icon = meta.icon;

            return (
              <div
                key={`${e.seq}-${e.type}`}
                className={`p-2.5 rounded-lg border text-xs transition-all duration-150 ${meta.bg}`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-950/90 text-slate-400 border border-slate-800">
                      #{String(e.seq).padStart(2, '0')}
                    </span>
                    <span className="font-mono text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-950/70 text-teal-400 border border-teal-500/20">
                      {meta.stage}
                    </span>
                    <Icon className={`w-3.5 h-3.5 ${meta.color} shrink-0`} />
                    <span className={`font-semibold text-xs ${meta.color}`}>
                      {meta.label}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 shrink-0">
                    {e.ts ? new Date(e.ts).toLocaleTimeString() : `seq:${e.seq}`}
                  </span>
                </div>

                {/* Full Readable Event Detail (Never Truncated) */}
                <div className="text-[11px] text-slate-200 font-mono leading-relaxed pl-2 border-l-2 border-slate-700/70 ml-1 mt-1.5 break-words">
                  {renderEventDetail(e)}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
