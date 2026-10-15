import React, { useState, useEffect, useMemo } from 'react';
import {
  ScenarioMeta,
  ReportOutput,
  SSEEvent,
  EvidenceCard,
} from '../types';
import {
  getScenarios,
  startInvestigation,
  getInvestigationReport,
  subscribeToEvents,
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
  Terminal,
  HelpCircle,
  GitCommit,
  CheckCircle2,
  Inbox,
  Search,
  ArrowUpDown,
  PlusCircle,
  ShieldCheck,
  FileCode,
  Database,
  BookOpen,
  MessageSquareWarning,
  Cpu,
  Clock,
  Layers,
} from 'lucide-react';

const SEVERITY_RANK: Record<string, number> = { P1: 1, P2: 2, P3: 3, P4: 4 };
const SOURCE_RANK: Record<string, number> = {
  code: 1,
  visual: 2,
  log: 3,
  record: 4,
  doc: 5,
  ticket: 6,
};

export const CockpitScreen: React.FC = () => {
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([]);
  const [intakeMode, setIntakeMode] = useState<'queue' | 'custom'>('queue');
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('S01');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'order' | 'severity' | 'class'>('order');
  const [ticketText, setTicketText] = useState<string>('');
  const [customModule, setCustomModule] = useState<string>('transfers');
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [investigationId, setInvestigationId] = useState<string>('');
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [report, setReport] = useState<ReportOutput | null>(null);
  const [inspectedCard, setInspectedCard] = useState<EvidenceCard | null>(null);
  const [copiedDraft, setCopiedDraft] = useState(false);
  const [copiedJira, setCopiedJira] = useState(false);
  const [draftTab, setDraftTab] = useState<'reply' | 'jira'>('reply');
  const [evidenceFilter, setEvidenceFilter] = useState<'all' | 'primary' | 'supports' | 'contradicts' | 'dropped'>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');

  // Load scenarios on mount
  useEffect(() => {
    async function load() {
      try {
        const scs = await getScenarios();
        setScenarios(scs);
        if (scs.length > 0) {
          setSelectedScenarioId(scs[0].id);
          setTicketText(scs[0].ticket_text || scs[0].description || '');
        }
      } catch (err) {
        console.error('Failed to load scenarios', err);
      }
    }
    load();
  }, []);

  // Elapsed timer while investigating
  useEffect(() => {
    if (!isInvestigating) return;
    const t0 = Date.now();
    setElapsedMs(0);
    const id = window.setInterval(() => {
      setElapsedMs(Date.now() - t0);
    }, 100);
    return () => window.clearInterval(id);
  }, [isInvestigating]);

  // Sorted & filtered ticket queue
  const sortedScenarios = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const filtered = scenarios.filter((sc) => {
      if (!q) return true;
      return (
        sc.id.toLowerCase().includes(q) ||
        (sc.ticket_id || '').toLowerCase().includes(q) ||
        sc.title.toLowerCase().includes(q) ||
        sc.ticket_class.toLowerCase().includes(q) ||
        (sc.module || '').toLowerCase().includes(q) ||
        sc.description.toLowerCase().includes(q)
      );
    });

    return filtered.sort((a, b) => {
      if (sortBy === 'severity') {
        const ra = SEVERITY_RANK[a.severity || 'P3'] || 9;
        const rb = SEVERITY_RANK[b.severity || 'P3'] || 9;
        if (ra !== rb) return ra - rb;
      }
      if (sortBy === 'class') {
        const cmp = a.ticket_class.localeCompare(b.ticket_class);
        if (cmp !== 0) return cmp;
      }
      return (a.order || 99) - (b.order || 99);
    });
  }, [scenarios, searchQuery, sortBy]);

  const selectedScenario = scenarios.find((s) => s.id === selectedScenarioId);

  const handleScenarioSelect = (sc: ScenarioMeta) => {
    setIntakeMode('queue');
    setSelectedScenarioId(sc.id);
    setTicketText(sc.ticket_text || sc.description || '');
  };

  const handleSwitchToCustom = () => {
    setIntakeMode('custom');
    setTicketText(
      'Same-day corporate transfer TXN-1009 for INR 45,000 from account 123456789012 failed at 4:05 PM IST with CUTOFF_EXCEEDED.'
    );
  };

  // Pre-flight client-side PII & Injection detection preview
  const preflightScan = useMemo(() => {
    const accounts = ticketText.match(/\b\d{10,16}\b/g) || [];
    const txns = ticketText.match(/\b(?:TXN|BATCH|INC|TCK)-\d+\b/gi) || [];
    const hasInj = /ignore\s+(?:all\s+)?previous\s+instructions|system\s+override|output\s+no_bug/i.test(ticketText);
    return {
      accountCount: accounts.length,
      txnRefs: Array.from(new Set(txns)),
      hasInjection: hasInj,
    };
  }, [ticketText]);

  const handleStartInvestigation = async (humanContext?: any) => {
    setIsInvestigating(true);
    setEvents([]);
    setReport(null);
    setEvidenceFilter('all');
    setSourceFilter('all');

    try {
      const invId = await startInvestigation({
        scenario_id: intakeMode === 'custom' ? 'CUSTOM' : selectedScenarioId,
        text: ticketText,
        attachments: intakeMode === 'queue' ? selectedScenario?.attachments : [],
        mode: 'live',
        human_context: humanContext,
      });

      setInvestigationId(invId);

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

  const eventTypeSet = new Set(events.map((e) => e.type));
  const hasInjection = Boolean(
    report?.routing_plan?.injection_detected ||
      events.some((e) => e.data?.injection_detected) ||
      report?.verified_cards?.some((c) => c.stance === 'contradicts' && c.claim.toLowerCase().includes('injection'))
  );

  const pipelineStages = [
    { step: '01', label: 'PII Mask', done: eventTypeSet.has('masking_done') || Boolean(report) },
    { step: '02', label: 'Flash Router', done: eventTypeSet.has('plan_created') || Boolean(report) },
    { step: '03', label: '5-Agent Swarm', done: eventTypeSet.has('tool_finished') || eventTypeSet.has('card_added') || Boolean(report) },
    { step: '04', label: 'AST Verifier', done: eventTypeSet.has('verifier_result') || Boolean(report) },
    { step: '05', label: '4-Way Reconcile', done: eventTypeSet.has('contradiction_found') || eventTypeSet.has('verifier_result') || Boolean(report) },
    { step: '06', label: 'Pro Hypotheses', done: eventTypeSet.has('hypothesis_update') || Boolean(report) },
    { step: '07', label: 'Trust Gate', done: eventTypeSet.has('trust_update') || Boolean(report) },
    { step: '08', label: 'Leak-Safe Drafts', done: eventTypeSet.has('report_ready') || Boolean(report) },
    { step: '09', label: 'SHA-256 Ledger', done: eventTypeSet.has('report_ready') || Boolean(report) },
    { step: '10', label: 'Maker-Checker', done: report?.decision?.status === 'approved' || eventTypeSet.has('write_back_done') },
  ];

  // Primary root-cause supporting card IDs
  const primaryCardIds = useMemo(() => {
    return new Set(report?.probable_root_cause?.supporting_card_ids || []);
  }, [report?.probable_root_cause]);

  // Deterministically sorted & filtered Evidence Cards
  const sortedAndFilteredCards = useMemo(() => {
    if (!report) return [];
    const allCards: EvidenceCard[] = [
      ...(report.verified_cards || []),
      ...(report.dropped_cards || []),
    ];

    const sorted = [...allCards].sort((a, b) => {
      const aVer = a.verification?.status === 'verified' ? 0 : 1;
      const bVer = b.verification?.status === 'verified' ? 0 : 1;
      if (aVer !== bVer) return aVer - bVer;

      const aPrim = primaryCardIds.has(a.card_id) ? 0 : 1;
      const bPrim = primaryCardIds.has(b.card_id) ? 0 : 1;
      if (aPrim !== bPrim) return aPrim - bPrim;

      const stanceOrder: Record<string, number> = { supports: 1, contradicts: 2, context: 3 };
      const aSt = stanceOrder[a.stance] || 4;
      const bSt = stanceOrder[b.stance] || 4;
      if (aSt !== bSt) return aSt - bSt;

      const aSrc = SOURCE_RANK[a.source_type] || 9;
      const bSrc = SOURCE_RANK[b.source_type] || 9;
      if (aSrc !== bSrc) return aSrc - bSrc;

      return a.card_id.localeCompare(b.card_id);
    });

    return sorted.filter((c) => {
      if (evidenceFilter === 'primary' && !primaryCardIds.has(c.card_id)) return false;
      if (evidenceFilter === 'supports' && (c.verification?.status !== 'verified' || c.stance !== 'supports')) return false;
      if (evidenceFilter === 'contradicts' && c.stance !== 'contradicts') return false;
      if (evidenceFilter === 'dropped' && c.verification?.status !== 'dropped') return false;
      if (sourceFilter !== 'all' && c.source_type !== sourceFilter) return false;
      return true;
    });
  }, [report, primaryCardIds, evidenceFilter, sourceFilter]);

  // 4-Way Reality Cross-Examination summary cards
  const fourWaySummary = useMemo(() => {
    if (!report) return null;
    const v = report.verified_cards || [];
    const codeCard = v.find((c) => c.source_type === 'code' && c.stance === 'supports') || v.find((c) => c.source_type === 'code');
    const logOrRecCard =
      v.find((c) => (c.source_type === 'log' || c.source_type === 'record') && c.stance === 'supports') ||
      v.find((c) => c.source_type === 'log' || c.source_type === 'record');
    const docOrHistCard =
      v.find((c) => c.source_type === 'doc' || c.source_type === 'ticket' || c.source_type === 'visual');
    const timeMismatch = report.contradictions?.find((c) => c.kind === 'TIME_MISMATCH');
    const docMismatch = report.contradictions?.find((c) => c.kind === 'STALE_DOC_FLAG' || c.kind === 'BEHAVIOUR_MISMATCH');

    return {
      client: {
        title: '1. Client Claim',
        badge: timeMismatch ? 'TIME_MISMATCH' : 'INGESTED',
        badgeColor: timeMismatch ? 'text-amber-300 bg-amber-950 border-amber-500/40' : 'text-sky-300 bg-sky-950 border-sky-500/30',
        detail: timeMismatch
          ? timeMismatch.note
          : `Ticket ${report.ticket_id} classified as ${report.ticket_class} (${report.severity}).`,
      },
      telemetry: {
        title: '2. Logs & Ledger State',
        badge: logOrRecCard ? `${logOrRecCard.card_id} VERIFIED` : 'PRUNED',
        badgeColor: logOrRecCard ? 'text-emerald-300 bg-emerald-950 border-emerald-500/40' : 'text-slate-400 bg-slate-900 border-slate-700',
        detail: logOrRecCard ? logOrRecCard.claim : 'Skipped by dynamic router (not required for this ticket class).',
      },
      code: {
        title: '3. Pinned Git AST',
        badge: codeCard ? `${codeCard.pointer?.path?.split('/').pop() || 'CODE'} VERIFIED` : 'PRUNED',
        badgeColor: codeCard ? 'text-teal-300 bg-teal-950 border-teal-500/40' : 'text-slate-400 bg-slate-900 border-slate-700',
        detail: codeCard
          ? `${codeCard.claim} (${codeCard.pointer?.path}:${codeCard.pointer?.line_start}@${String(codeCard.pointer?.sha || '').slice(0, 7)})`
          : 'Skipped by dynamic router (fast-path or insufficient info).',
      },
      docs: {
        title: '4. Runbooks & History',
        badge: docMismatch ? docMismatch.kind : docOrHistCard ? `${docOrHistCard.card_id} VERIFIED` : 'CHECKED',
        badgeColor: docMismatch
          ? 'text-amber-300 bg-amber-950 border-amber-500/40'
          : 'text-purple-300 bg-purple-950 border-purple-500/30',
        detail: docMismatch
          ? docMismatch.note
          : docOrHistCard
            ? docOrHistCard.claim
            : 'No conflicting runbooks or stale documentation detected.',
      },
    };
  }, [report]);

  const severityBadgeClass = (sev?: string) => {
    if (sev === 'P1') return 'bg-rose-950/90 text-rose-300 border-rose-500/40';
    if (sev === 'P2') return 'bg-amber-950/90 text-amber-300 border-amber-500/40';
    if (sev === 'P3') return 'bg-sky-950/90 text-sky-300 border-sky-500/40';
    return 'bg-slate-800 text-slate-300 border-slate-700';
  };

  return (
    <div className="space-y-4">
      {/* Top 10-Stage Neuro-Symbolic Execution Strip */}
      <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl px-4 py-3 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-teal-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
              10-Stage Verifiable Triage Pipeline
            </span>
            <span className="hidden sm:inline text-[11px] text-slate-400 font-mono">
              — Gemini 2.5 Proposes • Deterministic Python Verifies
            </span>
          </div>

          <div className="flex items-center gap-3 text-[11px] font-mono">
            {isInvestigating && (
              <span className="flex items-center gap-1.5 text-teal-300 bg-teal-950/80 px-2.5 py-0.5 rounded border border-teal-500/30">
                <RefreshCw className="w-3 h-3 animate-spin" />
                Running: {(elapsedMs / 1000).toFixed(1)}s
              </span>
            )}
            {report?.metrics && (
              <div className="flex items-center gap-2.5 text-slate-300 bg-slate-950 px-3 py-1 rounded-lg border border-slate-800">
                <span>
                  Tools: <strong className="text-teal-300">{report.metrics.tool_calls}/{report.metrics.tool_budget_limit || 12}</strong>
                </span>
                <span className="text-slate-700">|</span>
                <span>
                  Latency: <strong className="text-slate-100">{(report.metrics.latency_ms / 1000).toFixed(2)}s</strong>
                </span>
                <span className="text-slate-700">|</span>
                <span>
                  SHA-256: <strong className="text-teal-400">{(report.report_hash || '').slice(0, 10)}</strong>
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-10 gap-1.5">
          {pipelineStages.map((s, idx) => {
            const prevDone = idx === 0 || pipelineStages[idx - 1].done;
            const isCurrent = isInvestigating && !s.done && prevDone;
            return (
              <div
                key={s.step}
                className={`px-2.5 py-1.5 rounded-lg border text-[10px] font-mono flex items-center gap-1.5 transition-all ${
                  s.done
                    ? 'bg-teal-950/75 border-teal-500/45 text-teal-200 font-semibold shadow-sm shadow-teal-950/50'
                    : isCurrent
                      ? 'bg-amber-950/60 border-amber-400/50 text-amber-200 font-semibold animate-pulse'
                      : 'bg-slate-950/60 border-slate-800/80 text-slate-500'
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full text-[9px] flex items-center justify-center shrink-0 ${
                    s.done
                      ? 'bg-teal-400 text-slate-950 font-black'
                      : isCurrent
                        ? 'bg-amber-400 text-slate-950 font-black'
                        : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {s.done ? '✓' : s.step}
                </span>
                <span className="truncate">{s.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main 3-Column Command Center Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* COLUMN 1: Ticket Ingestion Queue & Custom Composer (lg:col-span-3) */}
        <div className="lg:col-span-3 space-y-4">
          {/* Ticket Queue & Intake Mode Switcher */}
          <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <div className="flex items-center gap-1.5">
                <Inbox className="w-4 h-4 text-teal-400" />
                <span className="font-bold text-xs uppercase tracking-wider text-slate-200">
                  Incident Ingestion
                </span>
              </div>

              <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-[10px] font-semibold">
                <button
                  onClick={() => setIntakeMode('queue')}
                  className={`px-2 py-1 rounded transition-colors ${
                    intakeMode === 'queue' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Queue ({scenarios.length})
                </button>
                <button
                  onClick={handleSwitchToCustom}
                  className={`px-2 py-1 rounded flex items-center gap-1 transition-colors ${
                    intakeMode === 'custom' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <PlusCircle className="w-3 h-3" /> Custom
                </button>
              </div>
            </div>

            {intakeMode === 'queue' ? (
              <>
                {/* Search & Sort Controls */}
                <div className="flex items-center gap-1.5">
                  <div className="relative flex-1">
                    <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Filter tickets..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
                    />
                  </div>
                  <div className="relative">
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as any)}
                      aria-label="Sort ticket queue"
                      className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-[11px] font-mono text-slate-300 focus:outline-none focus:border-teal-500"
                    >
                      <option value="order">Sort: #1 → #8</option>
                      <option value="severity">Sort: P1 → P4</option>
                      <option value="class">Sort: Class</option>
                    </select>
                  </div>
                </div>

                {/* Sorted Ticket Queue List */}
                <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
                  {sortedScenarios.map((sc) => {
                    const isSelected = sc.id === selectedScenarioId && intakeMode === 'queue';
                    return (
                      <button
                        key={sc.id}
                        onClick={() => handleScenarioSelect(sc)}
                        className={`w-full text-left p-2.5 rounded-xl text-xs transition-all border ${
                          isSelected
                            ? 'bg-teal-950/75 text-slate-100 border-teal-500/50 shadow-md shadow-teal-950/50'
                            : 'bg-slate-950/60 text-slate-300 hover:bg-slate-800/50 border-slate-800/80'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-1.5 mb-1">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-900 text-teal-400 border border-slate-700">
                              #{sc.order || sc.id} · {sc.ticket_id || sc.id}
                            </span>
                            <span className={`font-mono text-[9px] font-bold px-1.5 py-0.5 rounded border ${severityBadgeClass(sc.severity)}`}>
                              {sc.severity || 'P2'}
                            </span>
                          </div>
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800 uppercase">
                            {sc.module || sc.product_hint || 'core'}
                          </span>
                        </div>

                        <div className="font-semibold text-xs text-slate-100 leading-snug mb-1">
                          {sc.title}
                        </div>

                        <div className="flex items-center justify-between gap-1 text-[10px] font-mono text-slate-400">
                          <span>{sc.ticket_class}</span>
                          {sc.attachments && sc.attachments.length > 0 && (
                            <span className="text-teal-300">📎 Vision OCR</span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="p-2.5 rounded-lg bg-slate-950/90 border border-teal-500/30 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-teal-300 uppercase text-[10px]">
                    Direct Custom Ticket Intake
                  </span>
                  <select
                    value={customModule}
                    onChange={(e) => setCustomModule(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded px-2 py-0.5 text-[10px] font-mono text-slate-200"
                  >
                    <option value="transfers">module: transfers</option>
                    <option value="fees">module: fees</option>
                    <option value="notifications">module: notifications</option>
                    <option value="limits">module: limits</option>
                    <option value="settlement">module: settlement</option>
                  </select>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Paste any customer support ticket, transaction ID, or stack symptom below to run live Vertex AI routing and deterministic verification.
                </p>
              </div>
            )}
          </div>

          {/* Active Ticket Payload & Pre-Flight Security Scanner */}
          <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-teal-400" />
                {intakeMode === 'custom' ? 'Custom Payload' : `Ticket ${selectedScenario?.ticket_id || selectedScenarioId}`}
              </span>
              {intakeMode === 'queue' && selectedScenario?.created_at && (
                <span className="text-[10px] font-mono text-slate-400">
                  {new Date(selectedScenario.created_at).toLocaleString([], {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              )}
            </div>

            {intakeMode === 'queue' && selectedScenario && (
              <div className="p-2.5 rounded-lg bg-slate-950/90 border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between gap-1 flex-wrap">
                  <span className="text-[10px] font-mono font-bold text-teal-400 uppercase">
                    Verification Scope
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {selectedScenario.tags?.map((t) => (
                      <span
                        key={t}
                        className="px-1.5 py-0.5 rounded bg-slate-900 text-[9px] font-mono text-slate-300 border border-slate-800"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  {selectedScenario.description}
                </p>
              </div>
            )}

            <div>
              <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                Raw Unmasked Customer Ticket Text:
              </label>
              <textarea
                value={ticketText}
                onChange={(e) => setTicketText(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 focus:outline-none focus:border-teal-500 font-sans min-h-[125px] leading-relaxed"
                placeholder="Paste customer incident ticket..."
              />
            </div>

            {/* Live Pre-Flight PII & Injection Detection Preview */}
            <div className="p-2.5 rounded-lg bg-slate-950/90 border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between text-[10px] font-mono">
                <span className="text-slate-400 uppercase font-bold flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Pre-LLM Gate Preview
                </span>
                <span className="text-emerald-400">STAGE 01 ACTIVE</span>
              </div>
              <div className="flex flex-wrap gap-1.5 text-[10px] font-mono">
                <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                  PII Accounts: <strong className="text-teal-300">{preflightScan.accountCount}</strong>
                </span>
                {preflightScan.txnRefs.length > 0 && (
                  <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                    Refs: <strong className="text-teal-300">{preflightScan.txnRefs.join(', ')}</strong>
                  </span>
                )}
                {preflightScan.hasInjection && (
                  <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-500/40 font-bold">
                    ⚠️ Prompt Injection Override Detected
                  </span>
                )}
              </div>
            </div>

            {/* Multimodal Attachment Thumbnail (e.g. S06 screenshot.png) */}
            {intakeMode === 'queue' && selectedScenario?.attachments && selectedScenario.attachments.length > 0 && (
              <div className="p-2.5 rounded-lg bg-slate-950 border border-teal-500/35 space-y-1.5">
                <div className="flex items-center justify-between text-[10px] font-mono">
                  <span className="text-teal-300 font-bold">
                    📎 Attached UI Screenshot
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-teal-950 text-teal-300 border border-teal-500/30">
                    Gemini 2.5 Flash Vision
                  </span>
                </div>
                <img
                  src={`/api/bundles/${selectedScenario.id}/attachments/${selectedScenario.attachments[0]}`}
                  alt="Attached customer error screenshot"
                  className="w-full rounded border border-slate-800 max-h-40 object-contain bg-slate-900"
                />
              </div>
            )}

            {/* Launch Button */}
            <button
              onClick={() => handleStartInvestigation()}
              disabled={isInvestigating || !ticketText.trim()}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-bold text-xs transition-all shadow-lg shadow-teal-950/60 disabled:opacity-50"
            >
              {isInvestigating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Executing Autonomous Pipeline ({(elapsedMs / 1000).toFixed(1)}s)...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  Run Autonomous Triage ({intakeMode === 'custom' ? 'CUSTOM' : selectedScenario?.ticket_id || selectedScenarioId})
                </>
              )}
            </button>
          </div>
        </div>

        {/* COLUMN 2: Provenance, 4-Way Matrix, Specialist Swarm, Stream & Maker-Checker (lg:col-span-5) */}
        <div className="lg:col-span-5 space-y-4">
          {/* AI Execution Provenance Bar */}
          {report?.execution && (
            <div className="rounded-xl border border-emerald-500/30 bg-slate-900/95 p-3.5 text-xs shadow-lg space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-teal-400" />
                  <span className="font-bold uppercase tracking-wider text-slate-100">
                    Runtime Execution Provenance
                  </span>
                </div>
                <div className="flex items-center gap-2 font-mono text-[10px]">
                  <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40 font-bold">
                    {report.execution.mode.toUpperCase()}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-slate-950 text-teal-300 border border-slate-800">
                    {report.execution.calls?.length || 0} Model Call(s)
                  </span>
                </div>
              </div>

              {report.execution.calls && report.execution.calls.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
                  {report.execution.calls.map((c: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg bg-slate-950/90 border border-slate-800/90 font-mono text-[10px]"
                    >
                      <span className="text-slate-300 truncate">{c.operation}</span>
                      <span className="text-teal-300 shrink-0">
                        {c.model?.replace('gemini-', '')} • {c.latency_ms ?? 0}ms
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* High-Visibility Prompt Injection Quarantined Banner */}
          {hasInjection && (
            <div className="rounded-xl border border-rose-500/50 bg-rose-950/40 p-3.5 text-xs space-y-1.5 shadow-lg shadow-rose-950/30">
              <div className="flex items-center justify-between">
                <span className="font-bold text-rose-300 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-rose-400" />
                  Adversarial Prompt Injection Quarantined
                </span>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-500/40 font-bold">
                  NEUTRALIZED STAGE 01
                </span>
              </div>
              <p className="text-[11px] text-rose-200/90 leading-relaxed">
                {report?.routing_plan?.injection_note ||
                  'Untrusted instruction override detected in ticket or log stream and replaced with [INJECTION_QUARANTINED] before model ingestion.'}
              </p>
            </div>
          )}

          {/* Dynamic Specialist Router Bar */}
          <RouterBar
            routingPlan={report?.routing_plan}
            activeAgents={report?.routing_plan?.active_agents}
          />

          {/* 4-Way Reality Cross-Examination Matrix */}
          {fourWaySummary && (
            <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl space-y-2.5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-teal-400" />
                  4-Way Reality Cross-Examination Matrix
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  Client vs Logs vs Git AST vs Runbooks
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {Object.values(fourWaySummary).map((quad, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-slate-950/90 border border-slate-800/90 space-y-1"
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-[11px] font-bold text-slate-200">{quad.title}</span>
                      <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${quad.badgeColor}`}>
                        {quad.badge}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-snug line-clamp-2">
                      {quad.detail}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Real-Time Pipeline Stream */}
          <TimelineStream
            events={events}
            contradictions={report?.contradictions}
            isStreaming={isInvestigating}
          />

          {/* Context-Aware Pilot-in-the-Middle Controls */}
          <PilotMiddleControls
            report={report}
            investigationId={investigationId}
            selectedScenario={selectedScenario}
            onDecisionSubmitted={(updated) => setReport(updated)}
            onSimulateReply={handleSimulateReply}
            onDevSteer={handleDevSteer}
            isStreaming={isInvestigating}
          />
        </div>

        {/* COLUMN 3: Trust Score, Root-Cause Verdict, Sortable Evidence Board & Output Drafts (lg:col-span-4) */}
        <div className="lg:col-span-4 space-y-4">
          {/* Mathematical Trust Meter */}
          <TrustMeter trust={report?.trust} />

          {/* Probable Root Cause Hypothesis & Executive Summary */}
          {report && (
            <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                  <GitCommit className="w-4 h-4 text-teal-400" />
                  {report.probable_root_cause ? 'Verified Root-Cause Verdict' : 'Triage Resolution Summary'}
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800">
                    {report.owner_team}
                  </span>
                  {report.probable_root_cause && (
                    <span className="font-mono text-xs font-bold text-teal-300 bg-teal-950 px-2 py-0.5 rounded border border-teal-500/30">
                      {(report.probable_root_cause.score * 100).toFixed(0)}% Match
                    </span>
                  )}
                </div>
              </div>

              {report.probable_root_cause ? (
                <>
                  <p className="text-xs font-semibold text-slate-100 leading-relaxed bg-slate-950 p-3 rounded-lg border border-teal-500/25">
                    {report.probable_root_cause.statement}
                  </p>
                  <div className="grid grid-cols-1 gap-1.5 text-xs font-mono bg-slate-950/70 p-2.5 rounded-lg border border-slate-800">
                    {report.probable_root_cause.culprit_files?.length > 0 && (
                      <div className="text-[11px] flex items-center justify-between gap-2">
                        <span className="text-slate-500">Culprit File:</span>
                        <span className="text-teal-300 font-semibold truncate">
                          {report.probable_root_cause.culprit_files.join(', ')}
                        </span>
                      </div>
                    )}
                    {report.probable_root_cause.culprit_commit && (
                      <div className="text-[11px] flex items-center justify-between gap-2">
                        <span className="text-slate-500">Pinned Commit:</span>
                        <span className="text-emerald-300 font-semibold">
                          {report.probable_root_cause.culprit_commit}
                        </span>
                      </div>
                    )}
                    {report.probable_root_cause.supporting_card_ids?.length > 0 && (
                      <div className="text-[11px] flex items-center justify-between gap-2">
                        <span className="text-slate-500">Cited Proof IDs:</span>
                        <span className="text-slate-200">
                          {report.probable_root_cause.supporting_card_ids.join(', ')}
                        </span>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <p className="text-xs text-slate-200 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800 whitespace-pre-wrap">
                  {report.summary}
                </p>
              )}

              {report.workaround && (
                <div className="p-2.5 rounded-lg bg-teal-950/40 border border-teal-500/30 text-[11px] text-teal-200">
                  <strong className="uppercase text-[10px] text-teal-400 block mb-0.5">
                    Immediate Verified Workaround:
                  </strong>
                  {report.workaround}
                </div>
              )}

              {report.kb_gap && (
                <div className="p-2.5 rounded-lg bg-amber-950/35 border border-amber-500/30 text-[11px] text-amber-200">
                  <strong className="uppercase text-[10px] text-amber-400 block mb-0.5">
                    Documentation Drift Flagged ({report.kb_gap.page_id}):
                  </strong>
                  {report.kb_gap.issue}
                </div>
              )}
            </div>
          )}

          {/* Sorted & Filterable Evidentiary Cards Board */}
          <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <span className="font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Verified Evidentiary Cards
              </span>
              <div className="flex items-center gap-2 text-[10px] font-mono">
                <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30 font-bold">
                  {report?.verified_cards?.length || 0} Verified
                </span>
                <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-500/30 font-bold">
                  {report?.dropped_cards?.length || 0} Dropped
                </span>
              </div>
            </div>

            {report && (
              <div className="space-y-2">
                {/* Status / Stance Filter Bar */}
                <div className="flex flex-wrap items-center gap-1 text-[10px] font-mono">
                  {[
                    { id: 'all', label: `All (${(report.verified_cards?.length || 0) + (report.dropped_cards?.length || 0)})` },
                    { id: 'primary', label: `Root-Cause (${primaryCardIds.size})` },
                    { id: 'supports', label: 'Supports' },
                    { id: 'contradicts', label: 'Contradicts' },
                    { id: 'dropped', label: `Dropped (${report.dropped_cards?.length || 0})` },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setEvidenceFilter(tab.id as any)}
                      className={`px-2 py-1 rounded border transition-colors ${
                        evidenceFilter === tab.id
                          ? 'bg-teal-600 text-white border-teal-500 font-bold'
                          : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Source Type Filter Bar */}
                <div className="flex flex-wrap items-center gap-1 text-[10px] font-mono">
                  {['all', 'code', 'log', 'doc', 'record', 'visual', 'ticket'].map((src) => (
                    <button
                      key={src}
                      onClick={() => setSourceFilter(src)}
                      className={`px-2 py-0.5 rounded border uppercase transition-colors ${
                        sourceFilter === src
                          ? 'bg-slate-800 text-teal-300 border-teal-500/40 font-bold'
                          : 'bg-slate-950/60 text-slate-500 border-slate-800/80 hover:text-slate-300'
                      }`}
                    >
                      {src === 'all' ? 'All Sources' : src}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {!report ? (
                <div className="text-center py-10 text-slate-500 text-xs bg-slate-950/40 rounded-lg border border-slate-800/60">
                  Run autonomous triage to collect and verify multi-source evidence pointers.
                </div>
              ) : sortedAndFilteredCards.length === 0 ? (
                <div className="text-center py-6 text-slate-500 text-xs">
                  No evidence cards match the selected filter.
                </div>
              ) : (
                sortedAndFilteredCards.map((card) => (
                  <EvidenceCardItem
                    key={card.card_id}
                    card={card}
                    isPrimaryCitation={primaryCardIds.has(card.card_id)}
                    onInspect={(c) => setInspectedCard(c)}
                  />
                ))
              )}
            </div>
          </div>

          {/* Customer-Safe Reply & Engineering Jira Bug Draft Viewer */}
          {report && (
            <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                  <button
                    onClick={() => setDraftTab('reply')}
                    className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                      draftTab === 'reply'
                        ? 'bg-teal-600 text-white'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Customer Reply
                  </button>
                  <button
                    onClick={() => setDraftTab('jira')}
                    className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                      draftTab === 'jira'
                        ? 'bg-teal-600 text-white'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Jira Bug Draft
                  </button>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={handleCopyCustomerDraft}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-mono flex items-center gap-1 transition-colors border border-slate-700"
                  >
                    {copiedDraft ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    Copy Reply
                  </button>
                  <button
                    onClick={handleCopyJira}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-mono flex items-center gap-1 transition-colors border border-slate-700"
                  >
                    {copiedJira ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    Copy Jira
                  </button>
                </div>
              </div>

              {draftTab === 'reply' ? (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] uppercase font-bold text-slate-400">
                      Sanitized Client Response:
                    </span>
                    <span
                      className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border ${
                        report.leak_check?.passed
                          ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/40'
                          : 'bg-rose-950/80 text-rose-300 border-rose-500/40'
                      }`}
                    >
                      LeakCheck: {report.leak_check?.passed ? 'PASSED (0 Internal Paths)' : 'FLAGGED'}
                    </span>
                  </div>
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs text-slate-200 leading-relaxed font-sans max-h-44 overflow-y-auto whitespace-pre-wrap">
                    {report.customer_reply_draft}
                  </div>
                </div>
              ) : (
                <div>
                  {report.jira_draft ? (
                    <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs text-slate-200 space-y-2 max-h-52 overflow-y-auto font-mono">
                      <div className="font-bold text-teal-300">{report.jira_draft.title}</div>
                      <div className="text-[11px] whitespace-pre-wrap text-slate-300 font-sans leading-relaxed">
                        {report.jira_draft.description}
                      </div>
                      {report.jira_draft.evidence_links?.length > 0 && (
                        <div className="pt-2 border-t border-slate-800 text-[10px] text-teal-400 space-y-0.5">
                          <div className="font-bold text-slate-400 uppercase">Verified Proof Locators:</div>
                          {report.jira_draft.evidence_links.map((lnk, i) => (
                            <div key={i} className="truncate">• {lnk}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-xs text-slate-500 text-center">
                      No code defect Jira ticket required (Known Error fast-path, How-To guide, or Abstention).
                    </div>
                  )}
                </div>
              )}

              {/* Targeted client diagnostic questions (if any) */}
              {report.questions_for_client?.length > 0 && (
                <div className="pt-2 border-t border-slate-800/80">
                  <span className="text-[10px] uppercase font-bold text-amber-400 block mb-1.5 flex items-center gap-1">
                    <HelpCircle className="w-3.5 h-3.5" /> Discriminating Questions for Client:
                  </span>
                  <ul className="space-y-1 text-xs text-slate-200 list-disc list-inside bg-amber-950/20 p-2.5 rounded-lg border border-amber-500/25">
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

      {/* Proof Inspector Modal */}
      <ProofModal card={inspectedCard} onClose={() => setInspectedCard(null)} />
    </div>
  );
};
