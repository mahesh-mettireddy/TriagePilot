import React, { useState, useEffect } from 'react';
import { HumanDecision, ReportOutput, ScenarioMeta } from '../types';
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
  AlertTriangle,
} from 'lucide-react';

interface PilotMiddleControlsProps {
  report?: ReportOutput | null;
  investigationId?: string;
  selectedScenario?: ScenarioMeta;
  onDecisionSubmitted?: (updatedReport: ReportOutput) => void;
  onSimulateReply?: (replyText: string) => void;
  onDevSteer?: (steerText: string) => void;
  isStreaming?: boolean;
}

export const PilotMiddleControls: React.FC<PilotMiddleControlsProps> = ({
  report,
  investigationId,
  selectedScenario,
  onDecisionSubmitted,
  onSimulateReply,
  onDevSteer,
  isStreaming = false,
}) => {
  const [activeTab, setActiveTab] = useState<'decision' | 'steer' | 'reply'>('decision');
  const [clientReplyText, setClientReplyText] = useState(
    'Happened at 4:15 PM IST on same-day transfer TXN-1009. Rejected with CUTOFF_EXCEEDED.'
  );
  const [steerText, setSteerText] = useState(
    'Inspect app/transfers/cutoff.py around is_before_cutoff() and verify UTC vs Asia/Kolkata (IST) timezone comparison.'
  );
  const [approverName] = useState('Alex Rivera (Principal SRE)');
  const [editMode, setEditMode] = useState(false);
  const [editedSummary, setEditedSummary] = useState(report?.summary || '');
  const [editedReply, setEditedReply] = useState(report?.customer_reply_draft || '');
  const [rejectionReason] = useState('Requires deeper heap & trace inspection before customer notification.');
  const [submitting, setSubmitting] = useState(false);

  // Sync context-aware steer & client reply whenever selected ticket changes
  useEffect(() => {
    if (selectedScenario?.default_steer) {
      setSteerText(selectedScenario.default_steer);
    }
    if (selectedScenario?.default_client_reply) {
      setClientReplyText(selectedScenario.default_client_reply);
    }
  }, [selectedScenario?.id, selectedScenario?.default_steer, selectedScenario?.default_client_reply]);

  // Auto-focus Client Reply tab when policy is ABSTAIN (e.g., S11 Turn-1)
  useEffect(() => {
    if (report) {
      setEditedSummary(report.summary || '');
      setEditedReply(report.customer_reply_draft || '');
      if (report.trust?.policy_action === 'ABSTAIN') {
        setActiveTab('reply');
      } else {
        setActiveTab('decision');
      }
    }
  }, [report]);

  const handleApprove = async () => {
    if (!report?.investigation_id && !investigationId) return;
    const invId = report?.investigation_id || investigationId!;
    setSubmitting(true);
    try {
      const decision: HumanDecision = {
        status: 'approved',
        by: approverName,
        reason: editMode ? 'Operator edited summary and customer draft' : 'Verified by Principal SRE reviewer',
        edits_diff: editMode ? `Summary updated: "${editedSummary.slice(0, 60)}..."` : undefined,
        report_revision: report?.report_revision,
        report_hash: report?.report_hash,
        decision_id:
          typeof crypto !== 'undefined' && crypto.randomUUID
            ? crypto.randomUUID()
            : `decision-${Date.now()}-${Math.random().toString(16).slice(2)}`,
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
        report_revision: report?.report_revision,
        report_hash: report?.report_hash,
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
  const isAbstained = report?.trust?.policy_action === 'ABSTAIN';

  return (
    <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl">
      {/* Header & Tab Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5 mb-3">
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setActiveTab('decision')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'decision'
                ? 'bg-teal-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <CheckCheck className="w-3.5 h-3.5" />
            Maker-Checker Gate
          </button>

          <button
            onClick={() => setActiveTab('steer')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'steer'
                ? 'bg-teal-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            Engineer Steer
          </button>

          <button
            onClick={() => setActiveTab('reply')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              activeTab === 'reply'
                ? 'bg-amber-600 text-white shadow'
                : isAbstained
                  ? 'text-amber-300 bg-amber-950/60 border border-amber-500/40 animate-pulse'
                  : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Client Follow-Up {isAbstained ? '(Action Needed)' : ''}
          </button>
        </div>

        {/* Current status pill */}
        <div>
          {decisionState === 'approved' || decisionState === 'edited' ? (
            <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-md bg-emerald-950 text-emerald-300 border border-emerald-500/40">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              COMMITTED ({report?.decision?.write_back_ref})
            </span>
          ) : decisionState === 'rejected' ? (
            <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-md bg-rose-950 text-rose-300 border border-rose-500/40">
              <XOctagon className="w-3.5 h-3.5" />
              REJECTED BY OPERATOR
            </span>
          ) : isAbstained ? (
            <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-md bg-amber-950 text-amber-300 border border-amber-500/40">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              ABSTAINED • AWAITING CLIENT CLARIFICATION
            </span>
          ) : report ? (
            <span className="text-[11px] font-mono font-semibold px-2.5 py-1 rounded-md bg-teal-950/80 text-teal-300 border border-teal-500/30">
              READY FOR SIGN-OFF
            </span>
          ) : (
            <span className="text-[11px] font-mono text-slate-500 px-2 py-0.5 rounded bg-slate-950 border border-slate-800">
              STANDBY
            </span>
          )}
        </div>
      </div>

      {/* Tab 1: Maker-Checker Gate */}
      {activeTab === 'decision' && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
            <span>
              Cryptographic Maker-Checker Gate: Approval binds to <code className="text-teal-300 font-mono">report_revision</code> &amp; <code className="text-teal-300 font-mono">report_hash</code>.
            </span>
            <span className="font-mono text-[11px] text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
              Reviewer: {approverName}
            </span>
          </div>

          {report && !report.write_back_allowed && (
            <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-500/30 text-xs text-amber-200 flex items-center justify-between gap-2">
              <span>
                Automated write-back is locked by policy (<strong className="font-mono">{report.trust?.policy_action}</strong>). Provide client clarification in the <strong>Client Follow-Up</strong> tab to resume investigation.
              </span>
              <button
                onClick={() => setActiveTab('reply')}
                className="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white font-semibold text-[11px] shrink-0"
              >
                Provide Clarification →
              </button>
            </div>
          )}

          {editMode ? (
            <div className="space-y-2.5 bg-slate-950 p-3 rounded-lg border border-slate-800">
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
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <button
              onClick={handleApprove}
              disabled={submitting || isStreaming || !report || report.write_back_allowed === false}
              className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors shadow-lg shadow-emerald-950/40 disabled:opacity-40"
            >
              <CheckCheck className="w-4 h-4" />
              {editMode ? 'Approve with Edits & Commit Write-Back' : 'Approve & Commit Write-Back (Jira + Reply)'}
            </button>

            <button
              onClick={() => setEditMode(!editMode)}
              disabled={submitting || isStreaming || !report}
              className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs transition-colors border border-slate-700 disabled:opacity-40 flex items-center gap-1.5"
            >
              <Edit3 className="w-3.5 h-3.5 text-teal-400" />
              {editMode ? 'Cancel Edit' : 'Edit Drafts'}
            </button>

            <button
              onClick={handleReject}
              disabled={submitting || isStreaming || !report}
              className="px-3 py-2 rounded-lg bg-rose-950/70 hover:bg-rose-900 text-rose-300 font-medium text-xs transition-colors border border-rose-800/40 disabled:opacity-40 flex items-center gap-1.5"
            >
              <XOctagon className="w-3.5 h-3.5" />
              Reject
            </button>
          </div>

          {report?.decision?.write_back_ref && (
            <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-xs flex items-center justify-between text-emerald-300">
              <span className="flex items-center gap-1.5 font-mono font-semibold">
                <ExternalLink className="w-3.5 h-3.5" />
                Committed Write-Back Reference: {report.decision.write_back_ref}
              </span>
              <span className="text-[11px] text-emerald-400/90">Signed by {report.decision.by}</span>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Developer Steer */}
      {activeTab === 'steer' && (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-300">
              Steer specialist agents toward a specific file, commit, or hypothesis:
            </p>
            <span className="text-[10px] font-mono text-teal-400">HUMAN_CONTEXT: DEV_STEER</span>
          </div>
          <textarea
            value={steerText}
            onChange={(e) => setSteerText(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-sans"
            rows={2}
          />
          <div className="flex justify-end">
            <button
              onClick={() => onDevSteer && onDevSteer(steerText)}
              disabled={isStreaming || !steerText.trim()}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs transition-colors shadow-md disabled:opacity-40"
            >
              <Compass className="w-3.5 h-3.5" />
              Re-Run Pipeline With Engineer Steer
            </button>
          </div>
        </div>
      )}

      {/* Tab 3: Client Follow-Up Reply */}
      {activeTab === 'reply' && (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-300">
              Ingest client response answering diagnostic clarification questions (Turn-2 Resume):
            </p>
            <span className="text-[10px] font-mono text-amber-400">HUMAN_CONTEXT: CLIENT_REPLY</span>
          </div>
          <textarea
            value={clientReplyText}
            onChange={(e) => setClientReplyText(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-amber-500 font-sans"
            rows={2}
          />
          <div className="flex justify-end">
            <button
              onClick={() => onSimulateReply && onSimulateReply(clientReplyText)}
              disabled={isStreaming || !clientReplyText.trim()}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs transition-colors shadow-md disabled:opacity-40"
            >
              <Send className="w-3.5 h-3.5" />
              Ingest Client Clarification &amp; Resume Triage
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
