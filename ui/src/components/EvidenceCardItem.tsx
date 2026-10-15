import React from 'react';
import { EvidenceCard } from '../types';
import { CheckCircle2, XCircle, Search, FileCode, AlertTriangle, ArrowRight } from 'lucide-react';

interface EvidenceCardItemProps {
  card: EvidenceCard;
  onInspect: (card: EvidenceCard) => void;
}

export const EvidenceCardItem: React.FC<EvidenceCardItemProps> = ({ card, onInspect }) => {
  const isVerified = card.verification?.status === 'verified';
  const isDropped = card.verification?.status === 'dropped';

  const stanceBadges: Record<string, { label: string; class: string }> = {
    supports: { label: 'SUPPORTS', class: 'bg-teal-950/80 text-teal-300 border-teal-500/30' },
    contradicts: { label: 'CONTRADICTS', class: 'bg-rose-950/80 text-rose-300 border-rose-500/40' },
    context: { label: 'CONTEXT', class: 'bg-blue-950/80 text-blue-300 border-blue-500/30' },
  };

  const stance = stanceBadges[card.stance] || { label: card.stance, class: 'bg-slate-800 text-slate-300' };

  return (
    <div
      className={`rounded-lg border p-3.5 transition-all duration-200 hover:border-slate-600/80 flex flex-col justify-between ${
        isVerified
          ? 'bg-slate-900/90 border-emerald-500/30 shadow-sm shadow-emerald-500/5'
          : isDropped
          ? 'bg-slate-950/70 border-rose-900/40 opacity-80'
          : 'bg-slate-900 border-slate-800'
      }`}
    >
      <div>
        {/* Top bar: ID, Specialist, Stance, Status */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {card.card_id}
            </span>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-teal-300 border border-slate-700">
              {card.specialist}
            </span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${stance.class}`}>
              {stance.label}
            </span>
          </div>

          <div>
            {isVerified ? (
              <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-500/40">
                <CheckCircle2 className="w-3 h-3" /> VERIFIED
              </span>
            ) : isDropped ? (
              <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-950 text-rose-400 border border-rose-500/40">
                <XCircle className="w-3 h-3" /> DROPPED
              </span>
            ) : (
              <span className="text-[10px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">
                PENDING
              </span>
            )}
          </div>
        </div>

        {/* Claim text */}
        <p className="text-xs font-medium text-slate-200 mb-2 leading-relaxed">
          {card.claim}
        </p>

        {/* Snippet preview */}
        {card.snippet && (
          <div className="bg-slate-950 p-2 rounded border border-slate-800/80 mb-2">
            <pre className="text-[11px] font-mono text-slate-400 line-clamp-2 overflow-hidden">
              <code>{card.snippet}</code>
            </pre>
          </div>
        )}

        {/* Dropped reason callout */}
        {isDropped && card.verification?.reason && (
          <div className="flex items-start gap-1.5 text-[11px] text-rose-300 bg-rose-950/30 p-2 rounded border border-rose-800/40 mb-2">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
            <span className="line-clamp-2">{card.verification.reason}</span>
          </div>
        )}
      </div>

      {/* Footer: Pointer summary + Inspect button */}
      <div className="pt-2 mt-2 border-t border-slate-800/60 flex items-center justify-between gap-2 text-xs">
        <div className="text-[10px] font-mono text-slate-500 truncate" title={JSON.stringify(card.pointer)}>
          {card.pointer?.file || card.pointer?.commit || card.pointer?.runbook || card.source_type}
        </div>

        <button
          onClick={() => onInspect(card)}
          className="flex items-center gap-1 text-[11px] font-medium text-teal-400 hover:text-teal-300 transition-colors bg-teal-950/50 hover:bg-teal-900/50 px-2 py-1 rounded border border-teal-500/30 shrink-0"
        >
          <Search className="w-3 h-3" /> Inspect Proof
        </button>
      </div>
    </div>
  );
};
