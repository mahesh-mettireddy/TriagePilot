import React, { useState, useEffect } from 'react';
import { AuditChainEntry } from '../types';
import { getAuditChain, verifyAudit } from '../api';
import { 
  X, 
  ShieldCheck, 
  ShieldAlert, 
  RefreshCw, 
  Link, 
  Clock, 
  ChevronRight, 
  ChevronDown, 
  Hash, 
  CheckCircle2 
} from 'lucide-react';

interface AuditDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  investigationId?: string;
}

export const AuditDrawer: React.FC<AuditDrawerProps> = ({ isOpen, onClose, investigationId }) => {
  const [entries, setEntries] = useState<AuditChainEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyStatus, setVerifyStatus] = useState<{
    valid: boolean;
    entries_checked: number;
    message: string;
  } | null>(null);
  const [expandedSeq, setExpandedSeq] = useState<number | null>(null);

  const fetchEntries = async () => {
    setLoading(true);
    try {
      const data = await getAuditChain(investigationId);
      setEntries(data);
    } catch (err) {
      console.error('Failed to load audit chain', err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const res = await verifyAudit();
      setVerifyStatus(res);
    } catch (err: any) {
      setVerifyStatus({
        valid: false,
        entries_checked: entries.length,
        message: err.message || 'Verification failed',
      });
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchEntries();
      handleVerify();
    }
  }, [isOpen, investigationId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div 
        className="w-full max-w-2xl bg-slate-900 border-l border-slate-800 h-full flex flex-col shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 border-b border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-teal-950 text-teal-400 border border-teal-500/30">
              <Link className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-100 flex items-center gap-2">
                Cryptographic Audit Ledger
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-teal-400 border border-teal-500/20">
                  SHA-256 CHAIN
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Immutable, append-only hash chain verifying every triage step
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Verification Status Banner */}
        <div className="p-4 bg-slate-950/40 border-b border-slate-800/80 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            {verifyStatus?.valid ? (
              <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Chain Verified Valid ({verifyStatus.entries_checked} Blocks Checked)</span>
              </div>
            ) : verifyStatus ? (
              <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg bg-rose-950/60 text-rose-300 border border-rose-500/30">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                <span>Verification Failed: {verifyStatus.message}</span>
              </div>
            ) : (
              <div className="text-xs text-slate-400">Verifying chain integrity...</div>
            )}
          </div>

          <button
            onClick={handleVerify}
            disabled={verifying}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${verifying ? 'animate-spin text-teal-400' : ''}`} />
            Re-verify Chain
          </button>
        </div>

        {/* Ledger Entries List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading ? (
            <div className="text-center py-12 text-slate-500 text-xs">Loading ledger entries...</div>
          ) : entries.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">No audit entries recorded yet</div>
          ) : (
            entries.map((entry) => {
              const isExpanded = expandedSeq === entry.seq;
              return (
                <div
                  key={entry.seq}
                  className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 hover:border-slate-700 transition-colors"
                >
                  <div
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => setExpandedSeq(isExpanded ? null : entry.seq)}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-teal-400 border border-slate-700">
                        #{entry.seq}
                      </span>
                      <span className="text-xs font-semibold text-slate-200 uppercase tracking-wide">
                        {entry.step}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      <span className="flex items-center gap-1 text-[11px] font-mono">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {new Date(entry.ts).toLocaleTimeString()}
                      </span>
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </div>
                  </div>

                  {/* Hash info */}
                  <div className="mt-2 pt-2 border-t border-slate-850 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px] font-mono">
                    <div className="text-slate-500 truncate" title={entry.prev_hash}>
                      Prev: <span className="text-slate-400">{entry.prev_hash.slice(0, 16)}...</span>
                    </div>
                    <div className="text-slate-500 truncate" title={entry.hash}>
                      Hash: <span className="text-teal-400">{entry.hash.slice(0, 16)}...</span>
                    </div>
                  </div>

                  {/* Expanded Payload */}
                  {isExpanded && (
                    <div className="mt-3 pt-2 border-t border-slate-800 text-xs">
                      <div className="text-[10px] uppercase font-semibold text-slate-500 mb-1">
                        Payload Summary:
                      </div>
                      <pre className="bg-slate-900 p-2.5 rounded border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-48">
                        <code>{JSON.stringify(entry.payload_summary, null, 2)}</code>
                      </pre>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex justify-between items-center text-xs text-slate-500">
          <span>SHA-256 Merkle-linked audit records</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
          >
            Close Ledger
          </button>
        </div>
      </div>
    </div>
  );
};
