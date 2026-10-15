import React from 'react';
import { EvidenceCard } from '../types';
import { ExternalLink, X, CheckCircle, XCircle, FileCode, Tag, Clock } from 'lucide-react';

interface ProofModalProps {
  card: EvidenceCard | null;
  onClose: () => void;
}

export const ProofModal: React.FC<ProofModalProps> = ({ card, onClose }) => {
  if (!card) return null;

  const isVerified = card.verification?.status === 'verified';
  const isDropped = card.verification?.status === 'dropped';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fadeIn">
      <div 
        className="bg-slate-900 border border-slate-700/80 rounded-xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs px-2 py-1 rounded bg-slate-800 text-teal-400 border border-teal-500/30">
              {card.card_id}
            </span>
            <div className="flex items-center gap-2">
              {isVerified && (
                <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-500/40">
                  <CheckCircle className="w-3.5 h-3.5" /> VERIFIED EVIDENCE
                </span>
              )}
              {isDropped && (
                <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-rose-950/80 text-rose-300 border border-rose-500/40">
                  <XCircle className="w-3.5 h-3.5" /> DROPPED / UNVERIFIED
                </span>
              )}
              {!isVerified && !isDropped && (
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400">
                  PENDING VERIFICATION
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-sm">
          {/* Claim */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Extracted Claim
            </h4>
            <p className="text-slate-100 font-medium leading-relaxed bg-slate-800/50 p-3 rounded-lg border border-slate-800">
              {card.claim}
            </p>
          </div>

          {/* Verification Reason (if dropped or verified) */}
          {card.verification?.reason && (
            <div className={`p-3 rounded-lg border ${isVerified ? 'bg-emerald-950/30 border-emerald-800/50 text-emerald-200' : 'bg-rose-950/30 border-rose-800/50 text-rose-200'}`}>
              <span className="font-semibold text-xs uppercase tracking-wide block mb-1">
                {isVerified ? 'Verifier Assertion' : 'Drop Reason (Hallucination / Staleness Deflection)'}
              </span>
              <p className="text-xs leading-normal">{card.verification.reason}</p>
            </div>
          )}

          {/* Metadata badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] uppercase text-slate-500 block">Specialist</span>
              <span className="font-semibold text-slate-300">{card.specialist}</span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] uppercase text-slate-500 block">Source Type</span>
              <span className="font-mono text-slate-300 flex items-center gap-1">
                <Tag className="w-3 h-3 text-teal-400" />
                {card.source_type}
              </span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] uppercase text-slate-500 block">Stance</span>
              <span className={`font-semibold capitalize ${card.stance === 'supports' ? 'text-teal-400' : card.stance === 'contradicts' ? 'text-rose-400' : 'text-slate-400'}`}>
                {card.stance}
              </span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] uppercase text-slate-500 block">Observed At</span>
              <span className="text-xs text-slate-400 font-mono truncate block" title={card.observed_at}>
                {card.observed_at ? new Date(card.observed_at).toLocaleTimeString() : 'N/A'}
              </span>
            </div>
          </div>

          {/* Visual Screenshot Preview (for multimodal visual evidence cards) */}
          {(card.source_type === 'visual' || card.pointer?.image_url) && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-teal-400 block mb-1.5">
                Multimodal Visual Evidence Attachment (Gemini 2.5 Flash Vision OCR)
              </span>
              <div className="bg-slate-950 p-3 rounded-lg border border-teal-500/30 overflow-hidden">
                <img
                  src={card.pointer?.image_url || `/api/bundles/S06/attachments/${card.pointer?.filename || 'screenshot.png'}`}
                  alt="Customer attached error screenshot"
                  className="w-full max-h-64 object-contain rounded border border-slate-800"
                />
              </div>
            </div>
          )}

          {/* Code/Log Snippet */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <FileCode className="w-4 h-4 text-teal-400" /> Grounded Evidentiary Snippet
              </span>
              {card.github_permalink && (
                <a
                  href={card.github_permalink}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-teal-400 hover:text-teal-300 flex items-center gap-1 underline underline-offset-2"
                >
                  GitHub Permalink <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
            <pre className="p-3.5 bg-slate-950 rounded-lg text-xs font-mono text-slate-300 overflow-x-auto border border-slate-800/80 leading-relaxed max-h-56">
              <code>{card.snippet || '// No snippet text captured'}</code>
            </pre>
          </div>

          {/* Pointer Structure */}
          {card.pointer && Object.keys(card.pointer).length > 0 && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                Deterministic Evidentiary Pointer
              </span>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 text-xs font-mono text-slate-400">
                {Object.entries(card.pointer).map(([k, v]) => (
                  <div key={k} className="flex gap-2 py-0.5">
                    <span className="text-slate-500 min-w-24">{k}:</span>
                    <span className="text-teal-300 break-all">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 flex justify-end bg-slate-950/60">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
