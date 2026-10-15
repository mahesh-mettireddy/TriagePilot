import React from 'react';
import { EvidenceCard } from '../types';
import {
  CheckCircle2,
  XCircle,
  Search,
  FileCode,
  AlertTriangle,
  Terminal,
  BookOpen,
  Database,
  Image as ImageIcon,
  History,
  Sparkles,
} from 'lucide-react';

interface EvidenceCardItemProps {
  card: EvidenceCard;
  isPrimaryCitation?: boolean;
  onInspect: (card: EvidenceCard) => void;
}

export const EvidenceCardItem: React.FC<EvidenceCardItemProps> = ({
  card,
  isPrimaryCitation = false,
  onInspect,
}) => {
  const isVerified = card.verification?.status === 'verified';
  const isDropped = card.verification?.status === 'dropped';

  const stanceBadges: Record<string, { label: string; class: string }> = {
    supports: { label: 'SUPPORTS', class: 'bg-teal-950/90 text-teal-300 border-teal-500/35' },
    contradicts: { label: 'CONTRADICTS', class: 'bg-amber-950/90 text-amber-300 border-amber-500/40' },
    context: { label: 'CONTEXT', class: 'bg-sky-950/80 text-sky-300 border-sky-500/30' },
  };

  const sourceMeta: Record<string, { label: string; icon: React.ComponentType<{ className?: string }>; color: string }> = {
    code: { label: 'GIT AST / CODE', icon: FileCode, color: 'text-emerald-400' },
    log: { label: 'TELEMETRY LOG', icon: Terminal, color: 'text-sky-400' },
    doc: { label: 'RUNBOOK DOC', icon: BookOpen, color: 'text-purple-400' },
    record: { label: 'LEDGER RECORD', icon: Database, color: 'text-amber-400' },
    visual: { label: 'VISION OCR', icon: ImageIcon, color: 'text-teal-400' },
    ticket: { label: 'INCIDENT HISTORY', icon: History, color: 'text-indigo-400' },
  };

  const stance = stanceBadges[card.stance] || { label: card.stance, class: 'bg-slate-800 text-slate-300' };
  const src = sourceMeta[card.source_type] || { label: card.source_type.toUpperCase(), icon: FileCode, color: 'text-slate-400' };
  const SrcIcon = src.icon;

  const proofLabel =
    card.source_type === 'code' && card.pointer?.path
      ? `${card.pointer.path}:${card.pointer.line_start || '?'}@${String(card.pointer.sha || '').slice(0, 8)}`
      : card.source_type === 'log' && card.pointer?.log_id
        ? `${card.pointer.log_id} (${card.pointer.service || 'service'})`
        : card.source_type === 'doc' && card.pointer?.page_id
          ? `${card.pointer.page_id}#${card.pointer.section || 'doc'}`
          : card.source_type === 'record' && (card.pointer?.id || card.pointer?.transfer_id)
            ? `${card.pointer.id || card.pointer.transfer_id} [${card.pointer.field || 'record'}]`
            : card.source_type === 'visual' && card.pointer?.filename
              ? `${card.pointer.filename} (Vision OCR)`
              : card.pointer?.ke_id || card.pointer?.issue_id || card.pointer?.change_id || card.card_id;

  return (
    <div
      onClick={() => onInspect(card)}
      className={`group cursor-pointer rounded-xl border p-3.5 transition-all duration-200 flex flex-col justify-between ${
        isPrimaryCitation
          ? 'bg-slate-900 border-teal-400/60 shadow-md shadow-teal-500/10 ring-1 ring-teal-400/20'
          : isVerified
            ? 'bg-slate-900/90 border-slate-800 hover:border-teal-500/50'
            : isDropped
              ? 'bg-slate-950/75 border-rose-900/50 hover:border-rose-500/50 opacity-85'
              : 'bg-slate-900 border-slate-800'
      }`}
    >
      <div>
        {/* Top bar: ID, Source Type, Stance, Verification Status */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-950 text-slate-200 border border-slate-700">
              {card.card_id}
            </span>
            <span className="flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800">
              <SrcIcon className={`w-3 h-3 ${src.color}`} />
              {src.label}
            </span>
            <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${stance.class}`}>
              {stance.label}
            </span>
            {isPrimaryCitation && (
              <span className="flex items-center gap-1 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-400/40">
                <Sparkles className="w-2.5 h-2.5" /> ROOT-CAUSE PROOF
              </span>
            )}
          </div>

          <div className="shrink-0">
            {isVerified ? (
              <span className="flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-emerald-950/90 text-emerald-300 border border-emerald-500/40">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" /> VERIFIED
              </span>
            ) : isDropped ? (
              <span className="flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-rose-950/90 text-rose-300 border border-rose-500/40">
                <XCircle className="w-3 h-3 text-rose-400" /> DROPPED
              </span>
            ) : (
              <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded-md">
                PENDING
              </span>
            )}
          </div>
        </div>

        {/* Claim text */}
        <p className="text-xs font-medium text-slate-100 mb-2 leading-relaxed">
          {card.claim}
        </p>

        {/* Snippet preview */}
        {card.snippet && (
          <div className="bg-slate-950/95 p-2 rounded-lg border border-slate-800/90 mb-2">
            <pre className="text-[11px] font-mono text-slate-300 line-clamp-2 overflow-hidden whitespace-pre-wrap">
              <code>{card.snippet}</code>
            </pre>
          </div>
        )}

        {/* Dropped reason callout */}
        {isDropped && card.verification?.reason && (
          <div className="flex items-start gap-1.5 text-[11px] text-rose-200 bg-rose-950/40 p-2 rounded-lg border border-rose-500/30 mb-2">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
            <span>
              <strong>Verifier Rejected:</strong> {card.verification.reason}
            </span>
          </div>
        )}
      </div>

      {/* Footer: Pointer locator + Inspect button */}
      <div className="pt-2 mt-1 border-t border-slate-800/70 flex items-center justify-between gap-2 text-xs">
        <div className="text-[10px] font-mono text-teal-300/90 truncate" title={proofLabel}>
          {proofLabel}
        </div>

        <span className="flex items-center gap-1 text-[10px] font-mono font-semibold text-slate-300 group-hover:text-teal-300 transition-colors bg-slate-950 group-hover:bg-teal-950/60 px-2 py-1 rounded border border-slate-800 group-hover:border-teal-500/40 shrink-0">
          <Search className="w-3 h-3" /> Inspect Proof
        </span>
      </div>
    </div>
  );
};
