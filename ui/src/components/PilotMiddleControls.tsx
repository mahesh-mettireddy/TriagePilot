import React, { useState } from 'react';
import { HumanDecision, ReportOutput } from '../types';
import { submitDecision } from '../api';
import { 
  Send, 
  Compass, 
  CheckCheck, 
  Edit3, 
  XOctagon, 
  ExternalLink, 
  ShieldCheck, 
  MessageSquare,
  Sparkles
} from 'lucide-react';

interface PilotMiddleControlsProps {
  report?: ReportOutput | null;
  investigationId?: string;
  onDecisionSubmitted?: (updatedReport: ReportOutput) => void;
  onSimulateReply?: (replyText: string) => void;
  onDevSteer?: (steerText: string) => void;
  isStreaming?: boolean;
}

export const PilotMiddleControls: React.FC<PilotMiddleControlsProps> = ({
  report,
  investigationId,
  onDecisionSubmitted,
  onSimulateReply,
  onDevSteer,
  isStreaming = false,
}) => {
  const [activeTab, setActiveTab] = useState<'decision' | 'steer' | 'reply'>('decision');
  const [clientReplyText, setClientReplyText] = useState(
    'Client confirms: The timeout occurs consistently on /api/transfers/batch after 30 seconds when batch size > 50.'
  );
  const [steerText, setSteerText] = useState(
    'Focus investigation on database lock contention in account balance update during concurrent transfers.'
  );
  const [approverName, setApproverName] = useState('Alex Rivera (Staff SRE)');
  const [editMode, setEditMode] = useState(false);
  const [editedSummary, setEditedSummary] = useState(report?.summary || '');
  const [editedReply, setEditedReply] = useState(report?.customer_reply_draft || '');
  const [rejectionReason, setRejectionReason] = useState('Requires deeper memory heap analysis before customer notification.');
  const [submitting, setSubmitting] = useState(false);

  // Sync edits when report arrives
  React.useEffect(() => {
    if (report) {
      setEditedSummary(report.summary || '');
      setEditedReply(report.customer_reply_draft || '');
    }
  }, [report]);

  const handleApprove = async () => {
    if (!report?.investigation_id && !investigationId) return;
    const invId = report?.investigation_id || investigationId!;
    setSubmitting(true);
    try {
      const decision: HumanDecision = {
        status: editMode ? 'edited' : 'approved',
        by: approverName,
        reason: editMode ? 'Human edited summary and client draft' : 'Verified by human reviewer',
        edits_diff: editMode ? `Summary updated: "${editedSummary.slice(0, 60)}..."` : undefined,
        write_back_ref: `JIRA-SIM-${Math.floor(10000 + Math.random() * 90000)}`,
      };
      const updated = await submitDecision(invId, decision);
      if (onDecisionSubmitted) onDecisionSubmitted(updated);
      setEditMode(false);
    } catch (err) {
      console.error('Failed to submit decision', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!report?.investigation_id && !investigationId) return;
    const invId = report?.investigation_id || investigationId!;
    setSubmitting(true);
    try {
      const decision: HumanDecision = {
        status: 'rejected',
        by: approverName,
        reason: rejectionReason,
      };
      const updated = await submitDecision(invId, decision);
      if (onDecisionSubmitted) onDecisionSubmitted(updated);
    } catch (err) {
      console.error('Failed to submit rejection', err);
    } finally {
      setSubmitting(false);
    }
  };

  const decisionState = report?.decision?.status || 'pending';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
      {/* Tab Navigation */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('decision')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'decision'
                ? 'bg-teal-950 text-teal-300 border border-teal-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <CheckCheck className="w-3.5 h-3.5" />
            Maker-Checker Gate
          </button>

          <button
            onClick={() => setActiveTab('steer')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'steer'
                ? 'bg-teal-950 text-teal-300 border border-teal-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            Developer Steer
          </button>

          <button
            onClick={() => setActiveTab('reply')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'reply'
                ? 'bg-teal-950 text-teal-300 border border-teal-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Simulate Client Reply
          </button>
        </div>

        {/* Current status pill */}
        <div>
          {decisionState === 'approved' || decisionState === 'edited' ? (
            <span className="flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30">
              <ShieldCheck className="w-3 h-3" />
              APPROVED ({report?.decision?.write_back_ref})
            </span>
          ) : decisionState === 'rejected' ? (
            <span className="flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-500/30">
              <XOctagon className="w-3 h-3" />
              REJECTED
            </span>
          ) : (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-500/30">
              AWAITING HUMAN SIGN-OFF
            </span>
          )}
        </div>
      </div>

      {/* Tab 1: Maker-Checker Gate */}
      {activeTab === 'decision' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Human-in-the-Loop Safeguard: Zero automated write-backs without reviewer sign-off.</span>
            <span className="font-mono text-slate-500">Signer: {approverName}</span>
          </div>

          {editMode ? (
            <div className="space-y-2 bg-slate-950 p-3 rounded-lg border border-slate-800">
              <div>
                <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                  Edit Investigation Summary:
                </label>
                <textarea
                  value={editedSummary}
                  onChange={(e) => setEditedSummary(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-sans"
                  rows={2}
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                  Edit Customer Reply Draft:
                </label>
                <textarea
                  value={editedReply}
                  onChange={(e) => setEditedReply(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-sans"
                  rows={3}
                />
              </div>
            </div>
          ) : null}

          {/* Action buttons */}
          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={handleApprove}
              disabled={submitting || isStreaming || !report}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors shadow-lg shadow-emerald-950/40 disabled:opacity-40"
            >
              <CheckCheck className="w-4 h-4" />
              {editMode ? 'Approve with Edits → Jira' : 'Approve & Push to Jira'}
            </button>

            <button
              onClick={() => setEditMode(!editMode)}
              disabled={submitting || isStreaming || !report}
              className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs transition-colors border border-slate-700 disabled:opacity-40 flex items-center gap-1"
            >
              <Edit3 className="w-3.5 h-3.5 text-teal-400" />
              {editMode ? 'Cancel Edit' : 'Edit Draft'}
            </button>

            <button
              onClick={handleReject}
              disabled={submitting || isStreaming || !report}
              className="px-3 py-2 rounded-lg bg-rose-950/70 hover:bg-rose-900 text-rose-300 font-medium text-xs transition-colors border border-rose-800/40 disabled:opacity-40 flex items-center gap-1"
            >
              <XOctagon className="w-3.5 h-3.5" />
              Reject / Abstain
            </button>
          </div>

          {report?.decision?.write_back_ref && (
            <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-xs flex items-center justify-between text-emerald-300">
              <span className="flex items-center gap-1.5 font-medium">
                <ExternalLink className="w-3.5 h-3.5" />
                Linked System of Record: {report.decision.write_back_ref}
              </span>
              <span className="text-[11px] text-emerald-400/80">Approved by {report.decision.by}</span>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Developer Steer */}
      {activeTab === 'steer' && (
        <div className="space-y-2">
          <p className="text-xs text-slate-400">
            Inject engineer domain context or steer hypotheses toward specific subsystems:
          </p>
          <textarea
            value={steerText}
            onChange={(e) => setSteerText(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-sans"
            rows={2}
          />
          <div className="flex justify-end">
            <button
              onClick={() => onDevSteer && onDevSteer(steerText)}
              disabled={isStreaming}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs transition-colors disabled:opacity-40"
            >
              <Compass className="w-3.5 h-3.5" />
              Re-run With Developer Steer
            </button>
          </div>
        </div>
      )}

      {/* Tab 3: Simulate Client Reply */}
      {activeTab === 'reply' && (
        <div className="space-y-2">
          <p className="text-xs text-slate-400">
            Simulate client feedback answering diagnostic questions (Scenario S11 two-turn triage):
          </p>
          <textarea
            value={clientReplyText}
            onChange={(e) => setClientReplyText(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-sans"
            rows={2}
          />
          <div className="flex justify-end">
            <button
              onClick={() => onSimulateReply && onSimulateReply(clientReplyText)}
              disabled={isStreaming}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs transition-colors disabled:opacity-40"
            >
              <Send className="w-3.5 h-3.5" />
              Submit Client Reply (Turn 2)
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
