import React, { useRef, useEffect } from 'react';
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
  Clock 
} from 'lucide-react';

interface TimelineStreamProps {
  events: SSEEvent[];
  contradictions?: Contradiction[];
  isStreaming?: boolean;
}

export const TimelineStream: React.FC<TimelineStreamProps> = ({
  events,
  contradictions = [],
  isStreaming = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events]);

  const getEventMeta = (type: string) => {
    switch (type) {
      case 'ticket_masked':
        return { label: 'PII Redacted & Masked', color: 'text-sky-400', bg: 'bg-sky-950/65 border-sky-500/30', icon: ShieldCheck };
      case 'leak_check_passed':
        return { label: 'Anti-Leak Sanitized', color: 'text-emerald-400', bg: 'bg-emerald-950/65 border-emerald-500/30', icon: ShieldCheck };
      case 'routing_decided':
        return { label: 'Dynamic Routing Decided', color: 'text-purple-400', bg: 'bg-purple-950/65 border-purple-500/30', icon: Zap };
      case 'specialist_spawned':
        return { label: 'Specialist Spawned', color: 'text-cyan-400', bg: 'bg-cyan-950/65 border-cyan-500/30', icon: Activity };
      case 'specialist_evidence':
        return { label: 'Evidence Collected', color: 'text-indigo-400', bg: 'bg-indigo-950/65 border-indigo-500/30', icon: Search };
      case 'evidence_verified':
        return { label: 'Evidence Verified', color: 'text-emerald-400', bg: 'bg-emerald-950/65 border-emerald-500/30', icon: CheckCircle2 };
      case 'evidence_dropped':
        return { label: 'Evidence Dropped', color: 'text-rose-400', bg: 'bg-rose-950/65 border-rose-500/30', icon: XCircle };
      case 'contradiction_detected':
        return { label: 'Contradiction Detected', color: 'text-amber-400', bg: 'bg-amber-950/65 border-amber-500/30', icon: AlertTriangle };
      case 'hypotheses_ranked':
        return { label: 'Hypotheses Ranked', color: 'text-teal-400', bg: 'bg-teal-950/65 border-teal-500/30', icon: Layers };
      case 'trust_evaluated':
        return { label: 'Trust Evaluated', color: 'text-violet-400', bg: 'bg-violet-950/65 border-violet-500/30', icon: Activity };
      case 'report_ready':
        return { label: 'Triage Report Ready', color: 'text-emerald-400', bg: 'bg-emerald-950/65 border-emerald-500/30', icon: FileText };
      case 'awaiting_approval':
        return { label: 'Awaiting Human Sign-Off', color: 'text-amber-400', bg: 'bg-amber-950/65 border-amber-500/30', icon: Clock };
      default:
        return { label: type, color: 'text-slate-300', bg: 'bg-slate-900 border-slate-800', icon: Activity };
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col h-full shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-teal-400" />
          <h3 className="font-semibold text-xs uppercase tracking-wider text-slate-200">
            Real-Time Pipeline Stream
          </h3>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
            {events.length} events
          </span>
        </div>

        {isStreaming && (
          <div className="flex items-center gap-1.5 text-xs text-teal-400 font-mono">
            <span className="w-2 h-2 rounded-full bg-teal-400 animate-ping inline-block" />
            LIVE SSE
          </div>
        )}
      </div>

      {/* Contradictions Alert Box (if any detected) */}
      {contradictions.length > 0 && (
        <div className="mb-3 p-3 rounded-lg bg-amber-950/40 border border-amber-500/40 shrink-0 space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-300">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>Deterministic Contradictions Reconciled ({contradictions.length})</span>
          </div>
          {contradictions.map((c, i) => (
            <div key={i} className="text-xs bg-slate-950/70 p-2 rounded border border-amber-500/20 text-slate-300 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-500/30">
                  {c.kind}
                </span>
                {c.deterministic && (
                  <span className="text-[10px] text-teal-400 font-mono">deterministic</span>
                )}
              </div>
              <p className="text-[11px] leading-relaxed text-slate-300">{c.note}</p>
            </div>
          ))}
        </div>
      )}

      {/* Events Log */}
      <div ref={containerRef} className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[220px] max-h-[500px]">
        {events.length === 0 ? (
          <div className="text-center py-16 text-slate-500 text-xs">
            Awaiting investigation events...
          </div>
        ) : (
          events.map((e, idx) => {
            const meta = getEventMeta(e.type);
            const Icon = meta.icon;

            return (
              <div
                key={idx}
                className={`p-2.5 rounded-lg border text-xs transition-all duration-150 ${meta.bg}`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <Icon className={`w-3.5 h-3.5 ${meta.color}`} />
                    <span className={`font-semibold text-xs ${meta.color}`}>
                      {meta.label}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">
                    {e.ts ? new Date(e.ts).toLocaleTimeString() : `seq:${e.seq}`}
                  </span>
                </div>

                {/* Event Data summary */}
                <div className="text-[11px] text-slate-300 font-mono leading-relaxed pl-5 truncate">
                  {e.data?.specialist && (
                    <span className="text-teal-300 font-semibold mr-2">[{e.data.specialist}]</span>
                  )}
                  {e.data?.claim && (
                    <span>&quot;{e.data.claim}&quot;</span>
                  )}
                  {e.data?.reason && (
                    <span className="text-rose-300">Drop reason: {e.data.reason}</span>
                  )}
                  {e.data?.active_agents && (
                    <span>Active: {e.data.active_agents.join(', ')}</span>
                  )}
                  {e.data?.message && (
                    <span>{e.data.message}</span>
                  )}
                  {e.data?.ticket_class && (
                    <span>Class: {e.data.ticket_class} | Sev: {e.data.severity}</span>
                  )}
                  {e.data?.status && !e.data?.claim && (
                    <span>Status: {e.data.status}</span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
