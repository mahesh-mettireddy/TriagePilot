import React, { useState, useEffect } from 'react';
import { 
  ScenarioMeta, 
  ReportOutput, 
  SSEEvent, 
  EvidenceCard, 
  HumanDecision 
} from '../types';
import { 
  getScenarios, 
  startInvestigation, 
  getInvestigationReport, 
  subscribeToEvents 
} from '../api';
import { RouterBar } from '../components/RouterBar';
import { TrustMeter } from '../components/TrustMeter';
import { EvidenceCardItem } from '../components/EvidenceCardItem';
import { ProofModal } from '../components/ProofModal';
import { PilotMiddleControls } from '../components/PilotMiddleControls';
import { TimelineStream } from '../components/TimelineStream';
import { 
  Play, 
  Sparkles, 
  RefreshCw, 
  Copy, 
  Check, 
  AlertCircle, 
  FileText, 
  Tag, 
  Terminal, 
  HelpCircle,
  GitCommit,
  CheckCircle2,
  FolderGit2
} from 'lucide-react';

export const CockpitScreen: React.FC = () => {
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('S01');
  const [ticketText, setTicketText] = useState<string>('');
  const [mode, setMode] = useState<'live' | 'replay'>('replay');
  const [loadingScenarios, setLoadingScenarios] = useState(false);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [investigationId, setInvestigationId] = useState<string>('');
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [report, setReport] = useState<ReportOutput | null>(null);
  const [inspectedCard, setInspectedCard] = useState<EvidenceCard | null>(null);
  const [copiedDraft, setCopiedDraft] = useState(false);
  const [copiedJira, setCopiedJira] = useState(false);

  // Load scenarios on mount
  useEffect(() => {
    async function load() {
      setLoadingScenarios(true);
      try {
        const scs = await getScenarios();
        setScenarios(scs);
        if (scs.length > 0) {
          setSelectedScenarioId(scs[0].id);
          setTicketText(scs[0].description || '');
        }
      } catch (err) {
        console.error('Failed to load scenarios', err);
      } finally {
        setLoadingScenarios(false);
      }
    }
    load();
  }, []);

  // Update text when scenario changes
  const handleScenarioSelect = (sc: ScenarioMeta) => {
    setSelectedScenarioId(sc.id);
    setTicketText(sc.description || '');
  };

  const handleStartInvestigation = async (humanContext?: any) => {
    setIsInvestigating(true);
    setEvents([]);
    setReport(null);

    try {
      const invId = await startInvestigation({
        scenario_id: selectedScenarioId,
        text: ticketText,
        mode: mode,
        human_context: humanContext,
      });

      setInvestigationId(invId);

      // Subscribe to SSE events
      subscribeToEvents(
        invId,
        (ev) => {
          setEvents((prev) => [...prev, ev]);
          if (ev.type === 'report_ready' && ev.data?.investigation_id) {
            setReport(ev.data as ReportOutput);
          }
        },
        async () => {
          setIsInvestigating(false);
          // Fetch final report
          try {
            const finalReport = await getInvestigationReport(invId);
            setReport(finalReport);
          } catch (e) {
            console.error('Error fetching final report', e);
          }
        },
        (err) => {
          console.error('SSE Error', err);
          setIsInvestigating(false);
        }
      );
    } catch (err) {
      console.error('Failed to launch investigation', err);
      setIsInvestigating(false);
    }
  };

  const handleSimulateReply = (replyText: string) => {
    handleStartInvestigation({
      source: 'CLIENT_REPLY',
      message: replyText,
      parent_investigation_id: investigationId || undefined,
    });
  };

  const handleDevSteer = (steerText: string) => {
    handleStartInvestigation({
      source: 'DEV_STEER',
      message: steerText,
      parent_investigation_id: investigationId || undefined,
    });
  };

  const handleCopyCustomerDraft = () => {
    if (!report?.customer_reply_draft) return;
    navigator.clipboard.writeText(report.customer_reply_draft);
    setCopiedDraft(true);
    setTimeout(() => setCopiedDraft(false), 2000);
  };

  const handleCopyJira = () => {
    if (!report?.jira_draft) return;
    const jiraText = `[${report.jira_draft.title}]\n\n${report.jira_draft.description}\n\nRepro Steps:\n${report.jira_draft.repro_steps?.join('\n')}\n\nEvidence:\n${report.jira_draft.evidence_links?.join('\n')}`;
    navigator.clipboard.writeText(jiraText);
    setCopiedJira(true);
    setTimeout(() => setCopiedJira(false), 2000);
  };

  const selectedScenario = scenarios.find((s) => s.id === selectedScenarioId);

  return (
    <div className="space-y-6">
      {/* 3-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* COLUMN 1: Ingestion & Scenarios (lg:col-span-3) */}
        <div className="lg:col-span-3 space-y-4">
          {/* Scenario Selector */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
            <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-800">
              <span className="font-semibold text-xs uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <FolderGit2 className="w-3.5 h-3.5 text-teal-400" /> Ground-Truth Scenarios
              </span>
              <span className="text-[10px] font-mono text-slate-500">
                {scenarios.length} bundles
              </span>
            </div>

            <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
              {scenarios.map((sc) => {
                const isSelected = sc.id === selectedScenarioId;
                return (
                  <button
                    key={sc.id}
                    onClick={() => handleScenarioSelect(sc)}
                    className={`w-full text-left p-2 rounded-lg text-xs transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-teal-950/80 text-teal-300 border border-teal-500/40 font-semibold'
                        : 'bg-slate-950/50 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-slate-850'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-teal-400">
                        {sc.id}
                      </span>
                      <span className="truncate">{sc.title}</span>
                    </div>
                    <span className="text-[9px] font-mono text-slate-500 shrink-0 uppercase">
                      {sc.ticket_class}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Ticket Ingestion Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-xs uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-teal-400" /> Ingestion & Masking
              </span>
              {/* Mode Toggle */}
              <div className="flex items-center bg-slate-950 rounded-lg p-0.5 border border-slate-800 text-[10px]">
                <button
                  onClick={() => setMode('replay')}
                  className={`px-2 py-0.5 rounded font-mono transition-colors ${
                    mode === 'replay' ? 'bg-teal-600 text-white font-bold' : 'text-slate-400'
                  }`}
                >
                  REPLAY
                </button>
                <button
                  onClick={() => setMode('live')}
                  className={`px-2 py-0.5 rounded font-mono transition-colors ${
                    mode === 'live' ? 'bg-teal-600 text-white font-bold' : 'text-slate-400'
                  }`}
                >
                  LIVE
                </button>
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                Raw Ticket / Customer Description:
              </label>
              <textarea
                value={ticketText}
                onChange={(e) => setTicketText(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500 font-sans min-h-[140px]"
                placeholder="Enter customer bug report or select a scenario above..."
              />
            </div>

            {/* Redaction notice */}
            <div className="p-2 rounded bg-slate-950/70 border border-slate-800/80 text-[11px] text-slate-400 flex items-start gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
              <span>
                Deterministic Presidio PII sanitizer masks tokens (e.g. [REDACTED_PHONE_NUMBER], [REDACTED_EMAIL_ADDRESS]) before model ingestion.
              </span>
            </div>

            {/* Launch Button */}
            <button
              onClick={() => handleStartInvestigation()}
              disabled={isInvestigating || !ticketText.trim()}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold text-xs transition-colors shadow-lg shadow-teal-950/50 disabled:opacity-50"
            >
              {isInvestigating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Investigating Autonomous Loop...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  Run TriagePilot ({selectedScenarioId})
                </>
              )}
            </button>
          </div>
        </div>

        {/* COLUMN 2: Routing, SSE Timeline, Pilot Controls (lg:col-span-5) */}
        <div className="lg:col-span-5 space-y-4">
          {report?.execution && (
            <div className={`rounded-xl border p-3 text-xs ${
              report.execution.mode === 'vertex_ai'
                ? 'bg-emerald-950/30 border-emerald-500/30'
                : report.execution.mode === 'replay'
                  ? 'bg-sky-950/30 border-sky-500/30'
                  : 'bg-amber-950/30 border-amber-500/30'
            }`}>
              <div className="flex items-center justify-between">
                <span className="font-semibold uppercase tracking-wider text-slate-200">
                  AI Execution Provenance
                </span>
                <span className="font-mono font-bold text-slate-200">
                  {report.execution.mode.toUpperCase()}
                </span>
              </div>
              <div className="mt-1 text-slate-400">
                Provider: <span className="text-slate-200">{report.execution.provider}</span>
                {' · '}
                Models: <span className="text-slate-200">
                  {report.execution.models.length ? report.execution.models.join(', ') : 'deterministic fallback'}
                </span>
              </div>
              {report.execution.fallback_reason && (
                <div className="mt-1 text-amber-300">
                  Fallback: {report.execution.fallback_reason}
                </div>
              )}
            </div>
          )}

          {/* Dynamic Router Bar */}
          <RouterBar
            routingPlan={report?.routing_plan}
            activeAgents={report?.routing_plan?.active_agents}
          />

          {/* SSE Real-time Timeline */}
          <TimelineStream
            events={events}
            contradictions={report?.contradictions}
            isStreaming={isInvestigating}
          />

          {/* Human-in-the-Loop Controls */}
          <PilotMiddleControls
            report={report}
            investigationId={investigationId}
            onDecisionSubmitted={(updated) => setReport(updated)}
            onSimulateReply={handleSimulateReply}
            onDevSteer={handleDevSteer}
            isStreaming={isInvestigating}
          />
        </div>

        {/* COLUMN 3: Evidence, Root Cause, Trust, Output Drafts (lg:col-span-4) */}
        <div className="lg:col-span-4 space-y-4">
          {/* Trust Meter */}
          <TrustMeter trust={report?.trust} />

          {/* Probable Root Cause Hypothesis */}
          {report?.probable_root_cause && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="font-semibold text-xs uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <GitCommit className="w-4 h-4 text-teal-400" /> Probable Root Cause
                </span>
                <span className="font-mono text-xs font-bold text-teal-400 bg-teal-950 px-2 py-0.5 rounded border border-teal-500/30">
                  Score: {(report.probable_root_cause.score * 100).toFixed(0)}%
                </span>
              </div>

              <p className="text-xs font-semibold text-slate-100 leading-relaxed bg-slate-950 p-2.5 rounded-lg border border-slate-850">
                {report.probable_root_cause.statement}
              </p>

              {/* Culprit Files & Commit */}
              <div className="space-y-1.5 text-xs font-mono">
                {report.probable_root_cause.culprit_files?.length > 0 && (
                  <div className="text-[11px] text-slate-400">
                    <span className="text-slate-500">Culprit Files:</span>{' '}
                    <span className="text-teal-300">
                      {report.probable_root_cause.culprit_files.join(', ')}
                    </span>
                  </div>
                )}
                {report.probable_root_cause.culprit_commit && (
                  <div className="text-[11px] text-slate-400">
                    <span className="text-slate-500">Blamed Commit:</span>{' '}
                    <span className="text-teal-300">
                      {report.probable_root_cause.culprit_commit}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Verified Evidence Cards */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <span className="font-semibold text-xs uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Evidentiary Cards
              </span>
              <div className="flex items-center gap-2 text-[10px] font-mono">
                <span className="text-emerald-400">
                  {report?.verified_cards?.length || 0} Verified
                </span>
                <span className="text-slate-600">|</span>
                <span className="text-rose-400">
                  {report?.dropped_cards?.length || 0} Dropped
                </span>
              </div>
            </div>

            <div className="space-y-2.5 max-h-[260px] overflow-y-auto pr-1">
              {!report ? (
                <div className="text-center py-8 text-slate-500 text-xs">
                  Run triage to collect verified evidence
                </div>
              ) : (
                <>
                  {report.verified_cards?.map((card) => (
                    <EvidenceCardItem
                      key={card.card_id}
                      card={card}
                      onInspect={(c) => setInspectedCard(c)}
                    />
                  ))}
                  {report.dropped_cards?.map((card) => (
                    <EvidenceCardItem
                      key={card.card_id}
                      card={card}
                      onInspect={(c) => setInspectedCard(c)}
                    />
                  ))}
                </>
              )}
            </div>
          </div>

          {/* Customer Reply & Jira Draft Tabs/Boxes */}
          {report && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="font-semibold text-xs uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-teal-400" /> Synthesized Drafts
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleCopyCustomerDraft}
                    className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono flex items-center gap-1 transition-colors"
                    title="Copy customer reply draft"
                  >
                    {copiedDraft ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    Reply
                  </button>
                  <button
                    onClick={handleCopyJira}
                    className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono flex items-center gap-1 transition-colors"
                    title="Copy Jira ticket draft"
                  >
                    {copiedJira ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    Jira
                  </button>
                </div>
              </div>

              {/* Customer reply draft */}
              {report.customer_reply_draft && (
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                    Customer Reply Draft:
                  </span>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-850 text-xs text-slate-300 leading-relaxed font-sans max-h-36 overflow-y-auto whitespace-pre-wrap">
                    {report.customer_reply_draft}
                  </div>
                </div>
              )}

              {/* Client diagnostic questions (if any) */}
              {report.questions_for_client?.length > 0 && (
                <div className="pt-2 border-t border-slate-800/80">
                  <span className="text-[10px] uppercase font-bold text-amber-400/90 block mb-1 flex items-center gap-1">
                    <HelpCircle className="w-3 h-3" /> Targeted Diagnostic Clarifications:
                  </span>
                  <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside">
                    {report.questions_for_client.map((q, idx) => (
                      <li key={idx} className="leading-snug">
                        {q.text}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Proof Modal */}
      <ProofModal card={inspectedCard} onClose={() => setInspectedCard(null)} />
    </div>
  );
};
