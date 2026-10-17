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
  getConnectorsStatus,
  syncLiveRepo,
  getLiveEditableFiles,
  commitLiveFileEdit,
  resetLiveRepo,
  triggerLiveTransaction,
  sendA2ATask,
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
  Radio,
  Zap,
  Network,
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
  const [intakeMode, setIntakeMode] = useState<'queue' | 'live' | 'custom'>('queue');
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
  const [inspectorTab, setInspectorTab] = useState<'swarm' | 'trace' | 'models'>('swarm');
  const [showAllTenStages, setShowAllTenStages] = useState<boolean>(false);

  // Live Service Connector & In-Browser Code Studio state
  const [liveStatus, setLiveStatus] = useState<Record<string, any> | null>(null);
  const [liveFiles, setLiveFiles] = useState<Array<{ path: string; label: string; content: string }>>([]);
  const [selectedLiveFile, setSelectedLiveFile] = useState<string>('app/limits/daily_limit.py');
  const [liveCodeContent, setLiveCodeContent] = useState<string>('');
  const [liveCommitMsg, setLiveCommitMsg] = useState<string>('fix(limits): change >= to > in daily_limit.py boundary check');
  const [isCodeStudioOpen, setIsCodeStudioOpen] = useState<boolean>(true);
  const [isCommittingCode, setIsCommittingCode] = useState<boolean>(false);
  const [liveCommitResult, setLiveCommitResult] = useState<Record<string, any> | null>(null);
  const [liveCommitError, setLiveCommitError] = useState<string | null>(null);
  const [liveAmount, setLiveAmount] = useState<string>('100000');
  const [liveWindow, setLiveWindow] = useState<'10' | '16'>('10');
  const [liveTxResult, setLiveTxResult] = useState<Record<string, any> | null>(null);
  const [isTriggeringLive, setIsTriggeringLive] = useState(false);
  const [isSyncingRepo, setIsSyncingRepo] = useState(false);
  const [a2aStatusBadge, setA2aStatusBadge] = useState<string | null>(null);

  const refreshLiveStatus = async () => {
    try {
      const [st, filesResp] = await Promise.all([
        getConnectorsStatus().catch(() => null),
        getLiveEditableFiles().catch(() => null),
      ]);
      if (st) setLiveStatus(st);
      if (filesResp && filesResp.files) {
        setLiveFiles(filesResp.files);
        const current = filesResp.files.find((f) => f.path === selectedLiveFile) || filesResp.files[0];
        if (current && !liveCodeContent) {
          setLiveCodeContent(current.content);
        }
      }
    } catch {
      // Non-blocking
    }
  };

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
    refreshLiveStatus();
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

  const handleSwitchToLive = async () => {
    setIntakeMode('live');
    await refreshLiveStatus();
    if (!ticketText || selectedScenario?.ticket_text === ticketText) {
      setTicketText(
        'Customer transfer for INR 1,00,000.00 from account 918273645501 was rejected with DailyLimitExceededException after the latest commit. Please verify live telemetry, ledger snapshot, and recent repository commits.'
      );
    }
  };

  const handleSwitchToCustom = () => {
    setIntakeMode('custom');
    setTicketText(
      'Same-day corporate transfer TXN-1009 for INR 45,000 from account 123456789012 failed at 4:05 PM IST with CUTOFF_EXCEEDED.'
    );
  };

  const handleSelectLiveFile = (path: string) => {
    setSelectedLiveFile(path);
    setLiveCommitError(null);
    const found = liveFiles.find((f) => f.path === path);
    if (found) {
      setLiveCodeContent(found.content);
    }
    if (path.includes('daily_limit')) {
      setLiveCommitMsg('bug(limits): enforce >= boundary check on DAILY_TRANSFER_LIMIT');
      setLiveAmount('100000');
      setLiveWindow('10');
    } else if (path.includes('cutoff')) {
      setLiveCommitMsg('bug(cutoff): evaluate datetime.utcnow().hour >= 16 without IST conversion');
      setLiveAmount('45000');
      setLiveWindow('16');
    } else if (path.includes('calculator')) {
      setLiveCommitMsg('bug(fees): use binary float round(amount * rate, 2) on fee calculation');
      setLiveAmount('803.40');
      setLiveWindow('10');
    } else {
      setLiveCommitMsg(`feat(live): update ${path} in transfers-demo-app`);
    }
  };

  const handleCommitLiveCode = async () => {
    setIsCommittingCode(true);
    setLiveCommitError(null);
    try {
      const res = await commitLiveFileEdit({
        path: selectedLiveFile,
        content: liveCodeContent,
        commit_message: liveCommitMsg,
      });
      setLiveCommitResult(res);
      if (res?.live_transaction) {
        setLiveTxResult(res.live_transaction);
      }
      const shortSha = res?.git_workspace?.short_sha || 'HEAD';
      const diffLines = String(res?.diff || '')
        .split('\n')
        .filter((l) => (l.startsWith('+') && !l.startsWith('+++')) || (l.startsWith('-') && !l.startsWith('---')))
        .slice(0, 4)
        .join(' | ');
      setTicketText(
        res?.suggested_ticket ||
          `Live developer commit @${shortSha} in ${selectedLiveFile} ("${liveCommitMsg}"): ${diffLines || 'code modified'}. Please verify the live Git diff, runbook compliance, and runtime behavior.`
      );
      await refreshLiveStatus();
    } catch (err: any) {
      setLiveCommitError(err?.message || 'Failed to commit live code edit');
    } finally {
      setIsCommittingCode(false);
    }
  };

  const handleResetLiveWorkspace = async () => {
    setIsSyncingRepo(true);
    setLiveCommitError(null);
    try {
      await resetLiveRepo();
      setLiveCommitResult(null);
      const filesResp = await getLiveEditableFiles();
      setLiveFiles(filesResp.files || []);
      const cur = (filesResp.files || []).find((f) => f.path === selectedLiveFile) || filesResp.files?.[0];
      if (cur) setLiveCodeContent(cur.content);
      await refreshLiveStatus();
    } catch (err) {
      console.error('Failed to reset live repo', err);
    } finally {
      setIsSyncingRepo(false);
    }
  };

  const handleSyncLiveRepo = async () => {
    setIsSyncingRepo(true);
    try {
      await syncLiveRepo();
      await refreshLiveStatus();
    } catch (err) {
      console.error('Failed to sync live repo', err);
    } finally {
      setIsSyncingRepo(false);
    }
  };

  const handleTriggerLiveService = async (
    overrideAmount?: string,
    overrideWindow?: '10' | '16',
    autoInvestigate: boolean = false
  ) => {
    const amtStr = overrideAmount ?? liveAmount;
    const winStr = overrideWindow ?? liveWindow;
    if (overrideAmount !== undefined) setLiveAmount(overrideAmount);
    if (overrideWindow !== undefined) setLiveWindow(overrideWindow);

    setIsTriggeringLive(true);
    try {
      const res = await triggerLiveTransaction({
        amount: parseFloat(amtStr.replace(/,/g, '')) || 100000,
        transfer_type: 'same_day',
        tier: 'standard',
        simulate_utc_hour: parseInt(winStr, 10),
      });
      setLiveTxResult(res);
      const nextTicket = res.suggested_ticket || ticketText;
      if (res.suggested_ticket) {
        setTicketText(res.suggested_ticket);
      }
      await refreshLiveStatus();
      if (autoInvestigate && nextTicket) {
        await handleStartInvestigation(undefined, nextTicket, 'LIVE');
      }
    } catch (err) {
      console.error('Failed to execute live transaction', err);
    } finally {
      setIsTriggeringLive(false);
    }
  };

  // Pre-flight client-side PII & Injection detection preview
  const preflightScan = useMemo(() => {
    const accounts = ticketText.match(/\b\d{10,16}\b/g) || [];
    const txns = ticketText.match(/\b(?:TXN|BATCH|INC|TCK)-[A-Z0-9]+\b/gi) || [];
    const hasInj = /ignore\s+(?:all\s+)?previous\s+instructions|system\s+override|output\s+no_bug/i.test(ticketText);
    return {
      accountCount: accounts.length,
      txnRefs: Array.from(new Set(txns)),
      hasInjection: hasInj,
    };
  }, [ticketText]);

  const handleStartInvestigation = async (
    humanContext?: any,
    overrideTicketText?: string,
    overrideScenarioId?: string
  ) => {
    setIsInvestigating(true);
    setEvents([]);
    setReport(null);
    setEvidenceFilter('all');
    setSourceFilter('all');
    setA2aStatusBadge(null);

    const activeScenario =
      overrideScenarioId ||
      (intakeMode === 'live' ? 'LIVE' : intakeMode === 'custom' ? 'CUSTOM' : selectedScenarioId);
    const activeText = overrideTicketText ?? ticketText;

    try {
      const invId = await startInvestigation({
        scenario_id: activeScenario,
        text: activeText,
        attachments: intakeMode === 'queue' && !overrideScenarioId ? selectedScenario?.attachments : [],
        mode: 'live',
        human_context: humanContext,
      });

      setInvestigationId(invId);
      if (intakeMode === 'live' || activeScenario === 'LIVE') refreshLiveStatus();

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
            if (intakeMode === 'live' || activeScenario === 'LIVE') refreshLiveStatus();
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

  const handleDelegateViaA2A = async () => {
    setIsInvestigating(true);
    setEvents([]);
    setReport(null);
    setA2aStatusBadge('Delegating via A2A JSON-RPC 2.0...');
    const activeScenario =
      intakeMode === 'live' ? 'LIVE' : intakeMode === 'custom' ? 'CUSTOM' : selectedScenarioId;
    try {
      const a2aResp = await sendA2ATask(ticketText, activeScenario);
      const taskResult = a2aResp.result || a2aResp;
      const invId = taskResult.investigation_id || taskResult.sessionId;
      setA2aStatusBadge(`A2A Task ${taskResult.id} → ${taskResult.status?.state?.toUpperCase()}`);
      if (invId) {
        setInvestigationId(invId);
        const finalReport = await getInvestigationReport(invId);
        setReport(finalReport);
      }
      await refreshLiveStatus();
    } catch (err) {
      console.error('A2A delegation failed', err);
      setA2aStatusBadge('A2A Error');
    } finally {
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

  const handleEvidenceUpdate = (evidenceText: string) => {
    handleStartInvestigation({
      source: 'EVIDENCE_UPDATE',
      message: evidenceText,
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
        title: '🗣️ 1. What Customer Claimed',
        badge: timeMismatch ? 'TIME MISMATCH' : 'INGESTED',
        badgeColor: timeMismatch ? 'text-amber-300 bg-amber-950 border-amber-500/40' : 'text-sky-300 bg-sky-950 border-sky-500/30',
        detail: timeMismatch
          ? timeMismatch.note
          : `Ticket ${report.ticket_id} classified as ${report.ticket_class} (${report.severity}).`,
      },
      telemetry: {
        title: '📋 2. What Logs & Ledger Show',
        badge: logOrRecCard ? `${logOrRecCard.card_id} VERIFIED` : 'SKIPPED',
        badgeColor: logOrRecCard ? 'text-emerald-300 bg-emerald-950 border-emerald-500/40' : 'text-slate-400 bg-slate-900 border-slate-700',
        detail: logOrRecCard ? logOrRecCard.claim : 'Pruned by smart router (not needed for this ticket class).',
      },
      code: {
        title: '💻 3. What Git Code Actually Runs',
        badge: codeCard ? `${(codeCard.pointer?.file || codeCard.pointer?.path || 'CODE').split('/').pop()} VERIFIED` : 'SKIPPED',
        badgeColor: codeCard ? 'text-teal-300 bg-teal-950 border-teal-500/40' : 'text-slate-400 bg-slate-900 border-slate-700',
        detail: codeCard
          ? `${codeCard.claim} (${codeCard.pointer?.file || codeCard.pointer?.path}:${codeCard.pointer?.line_start}@${String(codeCard.pointer?.commit_sha || codeCard.pointer?.sha || '').slice(0, 7)})`
          : 'Pruned by smart router (fast-path or insufficient info).',
      },
      docs: {
        title: '📖 4. What Runbook & Docs Promise',
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

  // 5 High-Level Macro Phases for effortless comprehension
  const macroPhases = useMemo(() => {
    const s = pipelineStages;
    return [
      {
        num: '1',
        title: 'Privacy & Security Shield',
        sub: 'Scrubs PII & blocks prompt injection',
        done: s[0]?.done,
        active: isInvestigating && !s[0]?.done,
      },
      {
        num: '2',
        title: 'Smart Agent Router',
        sub: 'Selects needed specialists (max 12 calls)',
        done: s[1]?.done && s[2]?.done,
        active: isInvestigating && s[0]?.done && !s[2]?.done,
      },
      {
        num: '3',
        title: 'Python Proof Verifier',
        sub: 'Validates Git SHAs, line numbers & logs',
        done: s[3]?.done && s[4]?.done,
        active: isInvestigating && s[2]?.done && !s[4]?.done,
      },
      {
        num: '4',
        title: '4-Way Cross-Check & Trust',
        sub: 'Catches doc/code drift & scores trust',
        done: s[5]?.done && s[6]?.done && s[7]?.done,
        active: isInvestigating && s[4]?.done && !s[7]?.done,
      },
      {
        num: '5',
        title: 'Human Gate & SHA-256 Audit',
        sub: 'Seals ledger & awaits operator sign-off',
        done: s[8]?.done,
        active: isInvestigating && s[7]?.done && !s[8]?.done,
      },
    ];
  }, [pipelineStages, isInvestigating]);

  const severityBadgeClass = (sev?: string) => {
    if (sev === 'P1') return 'bg-rose-950/90 text-rose-300 border-rose-500/40';
    if (sev === 'P2') return 'bg-amber-950/90 text-amber-300 border-amber-500/40';
    if (sev === 'P3') return 'bg-sky-950/90 text-sky-300 border-sky-500/40';
    return 'bg-slate-800 text-slate-300 border-slate-700';
  };

  return (
    <div className="space-y-4">
      {/* Top 5-Phase Live Backend Progress Bar (with expandable 10-stage detail) */}
      <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl px-4 py-3 shadow-xl space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-teal-400" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-100">
              Live Backend Execution Pipeline
            </span>
            <span className="hidden md:inline text-[11px] text-slate-400">
              — Gemini 2.5 Proposes • Deterministic Python Verifies Every Citation
            </span>
          </div>

          <div className="flex items-center gap-2.5 text-[11px] font-mono">
            {isInvestigating && (
              <span className="flex items-center gap-1.5 text-teal-300 bg-teal-950/80 px-2.5 py-0.5 rounded border border-teal-500/30 font-bold">
                <RefreshCw className="w-3 h-3 animate-spin" />
                Investigating ({(elapsedMs / 1000).toFixed(1)}s)...
              </span>
            )}
            {report?.metrics && (
              <div className="hidden sm:flex items-center gap-2 text-slate-300 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
                <span>
                  Tool Calls: <strong className="text-teal-300">{report.metrics.tool_calls}/{report.metrics.tool_budget_limit || 12}</strong>
                </span>
                <span className="text-slate-700">•</span>
                <span>
                  Time: <strong className="text-slate-100">{(report.metrics.latency_ms / 1000).toFixed(1)}s</strong>
                </span>
              </div>
            )}
            <button
              onClick={() => setShowAllTenStages((prev) => !prev)}
              className="px-2 py-1 rounded bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800 text-[10px]"
            >
              {showAllTenStages ? 'Hide 10 Granular Stages' : 'View All 10 Stages'}
            </button>
          </div>
        </div>

        {/* 5 Intuitive Macro Phases */}
        <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
          {macroPhases.map((p) => (
            <div
              key={p.num}
              className={`px-3 py-2 rounded-lg border transition-all flex items-center gap-2.5 ${
                p.done
                  ? 'bg-teal-950/60 border-teal-500/40 text-slate-100'
                  : p.active
                  ? 'bg-amber-950/60 border-amber-400/50 text-amber-100 animate-pulse'
                  : 'bg-slate-950/50 border-slate-800/80 text-slate-500'
              }`}
            >
              <span
                className={`w-5 h-5 rounded-full text-[10px] font-black flex items-center justify-center shrink-0 ${
                  p.done
                    ? 'bg-teal-400 text-slate-950'
                    : p.active
                    ? 'bg-amber-400 text-slate-950'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {p.done ? '✓' : p.num}
              </span>
              <div className="min-w-0">
                <div className="text-[11px] font-bold truncate">{p.title}</div>
                <div className="text-[10px] text-slate-400 truncate">{p.sub}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Optional Expandable 10-Stage Technical Strip */}
        {showAllTenStages && (
          <div className="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-10 gap-1.5 pt-2 border-t border-slate-800/80">
            {pipelineStages.map((s, idx) => {
              const prevDone = idx === 0 || pipelineStages[idx - 1].done;
              const isCurrent = isInvestigating && !s.done && prevDone;
              return (
                <div
                  key={s.step}
                  className={`px-2 py-1 rounded border text-[10px] font-mono flex items-center gap-1 ${
                    s.done
                      ? 'bg-teal-950/80 border-teal-500/40 text-teal-200'
                      : isCurrent
                      ? 'bg-amber-950/60 border-amber-400/50 text-amber-200 animate-pulse'
                      : 'bg-slate-950/60 border-slate-800 text-slate-500'
                  }`}
                >
                  <span className="font-bold">{s.done ? '✓' : s.step}</span>
                  <span className="truncate">{s.label}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Main 3-Column Command Center Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* ===================================================================
            COLUMN 1: STEP 1 — SELECT OR TRIGGER INCIDENT (lg:col-span-3)
           =================================================================== */}
        <div className="lg:col-span-3 space-y-4 lg:sticky lg:top-20">
          <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl space-y-3">
            {/* Step 1 Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30 font-mono text-[10px] font-bold">
                  STEP 1
                </span>
                <span className="font-bold text-xs uppercase tracking-wider text-slate-100">
                  Select Incident
                </span>
              </div>
            </div>

            {/* Clean 3-Way Intake Mode Switcher */}
            <div className="grid grid-cols-3 gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-[11px] font-semibold">
              <button
                onClick={() => setIntakeMode('queue')}
                className={`py-1.5 rounded-md transition-colors ${
                  intakeMode === 'queue' ? 'bg-teal-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Queue ({scenarios.length})
              </button>
              <button
                onClick={handleSwitchToLive}
                className={`py-1.5 rounded-md flex items-center justify-center gap-1 transition-colors ${
                  intakeMode === 'live' ? 'bg-teal-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Radio className="w-3 h-3" /> Live App
              </button>
              <button
                onClick={handleSwitchToCustom}
                className={`py-1.5 rounded-md flex items-center justify-center gap-1 transition-colors ${
                  intakeMode === 'custom' ? 'bg-teal-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <PlusCircle className="w-3 h-3" /> Custom
              </button>
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
                      placeholder="Search incidents..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-teal-500"
                    />
                  </div>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    aria-label="Sort ticket queue"
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-[11px] font-mono text-slate-300 focus:outline-none focus:border-teal-500"
                  >
                    <option value="order">#1 → #8</option>
                    <option value="severity">P1 → P4</option>
                    <option value="class">By Type</option>
                  </select>
                </div>

                {/* Sorted Ticket Queue List */}
                <div className="space-y-1.5 max-h-[260px] overflow-y-auto pr-1">
                  {sortedScenarios.map((sc) => {
                    const isSelected = sc.id === selectedScenarioId && intakeMode === 'queue';
                    return (
                      <button
                        key={sc.id}
                        onClick={() => handleScenarioSelect(sc)}
                        className={`w-full text-left p-2.5 rounded-xl text-xs transition-all border ${
                          isSelected
                            ? 'bg-teal-950/75 text-slate-100 border-teal-500/60 shadow-md shadow-teal-950/50'
                            : 'bg-slate-950/60 text-slate-300 hover:bg-slate-800/50 border-slate-800/80'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-1.5 mb-1">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-900 text-teal-400 border border-slate-700">
                              #{sc.order || sc.id}
                            </span>
                            <span className={`font-mono text-[9px] font-bold px-1.5 py-0.5 rounded border ${severityBadgeClass(sc.severity)}`}>
                              {sc.severity || 'P2'}
                            </span>
                          </div>
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800 uppercase">
                            {sc.module || 'core'}
                          </span>
                        </div>

                        <div className="font-semibold text-xs text-slate-100 leading-snug mb-1">
                          {sc.title}
                        </div>

                        <div className="flex items-center justify-between gap-1 text-[10px] font-mono text-slate-400">
                          <span>{sc.ticket_class}</span>
                          {sc.attachments && sc.attachments.length > 0 && (
                            <span className="text-teal-300">📎 Screenshot OCR</span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </>
            ) : intakeMode === 'live' ? (
              <div className="p-3 rounded-xl bg-slate-950/90 border border-teal-500/40 space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-teal-300 uppercase text-[10px] flex items-center gap-1.5">
                    <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                    Live Code &amp; Git Sandbox
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setIsCodeStudioOpen((prev) => !prev)}
                      className="px-2 py-0.5 rounded bg-teal-950/90 hover:bg-teal-900 border border-teal-500/40 text-[10px] font-mono text-teal-200 flex items-center gap-1 font-semibold"
                    >
                      <FileCode className="w-2.5 h-2.5" />
                      {isCodeStudioOpen ? 'Hide Editor' : 'Edit & Commit Code'}
                    </button>
                    <button
                      onClick={handleResetLiveWorkspace}
                      disabled={isSyncingRepo}
                      className="px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-[10px] font-mono text-slate-300 flex items-center gap-1"
                      title="Reset live repo to original baseline"
                    >
                      <RefreshCw className={`w-2.5 h-2.5 ${isSyncingRepo ? 'animate-spin' : ''}`} />
                      Reset
                    </button>
                  </div>
                </div>

                {/* Live Git HEAD Status */}
                <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800 space-y-1 font-mono text-[10px]">
                  <div className="flex items-center justify-between text-slate-300">
                    <span className="text-slate-400">HEAD Commit:</span>
                    <span className="text-teal-300 font-bold flex items-center gap-1">
                      <GitCommit className="w-3 h-3" />
                      @{liveStatus?.git_workspace?.short_sha || '288c17a'}
                    </span>
                  </div>
                  <div className="text-slate-400 truncate">
                    {liveStatus?.git_workspace?.last_commit?.subject || ' transfers-demo-app live mirror'}
                  </div>
                  {liveStatus?.git_workspace?.has_live_changes && (
                    <div className="text-emerald-300 font-bold">
                      ⚡ Live Diff Active: {(liveStatus.git_workspace.modified_files || []).join(', ')}
                    </div>
                  )}
                </div>

                {/* In-Browser Live Code Editor & Git Commit */}
                {isCodeStudioOpen && (
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-teal-500/40 space-y-2">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase text-teal-300 block">
                        1. Select File to Edit (`transfers-demo-app`):
                      </label>
                      <select
                        value={selectedLiveFile}
                        onChange={(e) => handleSelectLiveFile(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-[11px] font-mono text-teal-200 focus:outline-none focus:border-teal-500"
                      >
                        {liveFiles.map((f) => (
                          <option key={f.path} value={f.path}>
                            {f.path} — {f.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[10px] font-mono">
                        <span className="text-slate-300 font-bold uppercase">2. Edit Python Source Code:</span>
                        <span className="text-slate-500">AST Validated</span>
                      </div>
                      <textarea
                        value={liveCodeContent}
                        onChange={(e) => setLiveCodeContent(e.target.value)}
                        rows={8}
                        spellCheck={false}
                        className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-[10px] font-mono text-emerald-200 leading-snug focus:outline-none focus:border-teal-500"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase text-slate-300 block">
                        3. Git Commit Message:
                      </label>
                      <input
                        type="text"
                        value={liveCommitMsg}
                        onChange={(e) => setLiveCommitMsg(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-[10px] font-mono text-slate-200"
                      />
                    </div>

                    {liveCommitError && (
                      <div className="p-1.5 rounded bg-rose-950/90 border border-rose-500/40 text-[10px] font-mono text-rose-300">
                        {liveCommitError}
                      </div>
                    )}

                    <button
                      onClick={handleCommitLiveCode}
                      disabled={isCommittingCode}
                      className="w-full py-1.5 px-2.5 rounded bg-teal-600 hover:bg-teal-500 text-white font-bold text-[11px] font-mono flex items-center justify-center gap-1.5 shadow"
                    >
                      <GitCommit className="w-3.5 h-3.5" />
                      {isCommittingCode ? 'Committing to Live Git...' : 'Commit Edit to Live Git Repo'}
                    </button>

                    {liveCommitResult?.git_workspace && (
                      <div className="p-2 rounded bg-emerald-950/70 border border-emerald-500/40 text-[10px] font-mono text-emerald-200 space-y-1">
                        <div>
                          ✓ Committed <strong className="text-white">@{liveCommitResult.git_workspace.short_sha}</strong> in{' '}
                          <span className="text-teal-300">{selectedLiveFile}</span>
                        </div>
                        <button
                          onClick={() => handleTriggerLiveService(liveAmount, liveWindow, true)}
                          disabled={isTriggeringLive || isInvestigating}
                          className="w-full mt-1 py-1 px-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[10px] flex items-center justify-center gap-1 shadow"
                        >
                          <Zap className="w-3 h-3" />
                          Execute Live Transfer &amp; Verify Commit Now →
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* 3 One-Click Live Bug Scenarios */}
                <div className="space-y-1.5">
                  <div className="text-[10px] font-bold uppercase text-slate-300">
                    Or Trigger a 1-Click Live Bug Scenario:
                  </div>
                  <div className="grid grid-cols-1 gap-1.5">
                    <button
                      onClick={() => handleTriggerLiveService('100000', '10', true)}
                      disabled={isTriggeringLive || isInvestigating}
                      className="text-left p-2 rounded-lg bg-slate-900 hover:bg-teal-950/70 border border-slate-800 hover:border-teal-500/50 transition-all flex items-center justify-between gap-2"
                    >
                      <div>
                        <div className="text-[11px] font-bold text-rose-300">
                          🔴 Bug 1: Daily Limit Boundary (`&gt;=`)
                        </div>
                        <div className="text-[10px] font-mono text-slate-400">
                          INR 1,00,000 → `daily_limit.py`
                        </div>
                      </div>
                      <span className="px-2 py-1 rounded bg-teal-600/20 text-teal-300 border border-teal-500/30 font-mono text-[9px] font-bold shrink-0">
                        Run Live →
                      </span>
                    </button>

                    <button
                      onClick={() => handleTriggerLiveService('45000', '16', true)}
                      disabled={isTriggeringLive || isInvestigating}
                      className="text-left p-2 rounded-lg bg-slate-900 hover:bg-teal-950/70 border border-slate-800 hover:border-teal-500/50 transition-all flex items-center justify-between gap-2"
                    >
                      <div>
                        <div className="text-[11px] font-bold text-amber-300">
                          🟠 Bug 2: Cutoff Timezone (`cutoff.py`)
                        </div>
                        <div className="text-[10px] font-mono text-slate-400">
                          INR 45,000 @ 16:15 → `CutoffWindowClosedException`
                        </div>
                      </div>
                      <span className="px-2 py-1 rounded bg-teal-600/20 text-teal-300 border border-teal-500/30 font-mono text-[9px] font-bold shrink-0">
                        Run Live →
                      </span>
                    </button>

                    <button
                      onClick={() => handleTriggerLiveService('803.40', '10', true)}
                      disabled={isTriggeringLive || isInvestigating}
                      className="text-left p-2 rounded-lg bg-slate-900 hover:bg-teal-950/70 border border-slate-800 hover:border-teal-500/50 transition-all flex items-center justify-between gap-2"
                    >
                      <div>
                        <div className="text-[11px] font-bold text-sky-300">
                          🔵 Bug 3: Binary Float Fee (`calculator.py`)
                        </div>
                        <div className="text-[10px] font-mono text-slate-400">
                          INR 803.40 → Charges 10.05 vs 10.04
                        </div>
                      </div>
                      <span className="px-2 py-1 rounded bg-teal-600/20 text-teal-300 border border-teal-500/30 font-mono text-[9px] font-bold shrink-0">
                        Run Live →
                      </span>
                    </button>
                  </div>
                </div>

                {/* Custom Amount / Window Trigger */}
                <div className="pt-1.5 border-t border-slate-800/80 space-y-1.5">
                  <div className="grid grid-cols-2 gap-1.5">
                    <div>
                      <label className="text-[9px] uppercase text-slate-400 block mb-0.5">Amount (INR)</label>
                      <input
                        type="text"
                        value={liveAmount}
                        onChange={(e) => setLiveAmount(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs font-mono text-slate-100"
                      />
                    </div>
                    <div>
                      <label className="text-[9px] uppercase text-slate-400 block mb-0.5">Time Window</label>
                      <select
                        value={liveWindow}
                        onChange={(e) => setLiveWindow(e.target.value as '10' | '16')}
                        className="w-full bg-slate-900 border border-slate-700 rounded px-1.5 py-1 text-xs font-mono text-slate-100"
                      >
                        <option value="10">10:15 (Open)</option>
                        <option value="16">16:15 (Cutoff)</option>
                      </select>
                    </div>
                  </div>

                  <button
                    onClick={() => handleTriggerLiveService(undefined, undefined, true)}
                    disabled={isTriggeringLive || isInvestigating}
                    className="w-full py-1.5 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-teal-300 border border-teal-500/30 font-bold text-[11px] font-mono flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Zap className="w-3.5 h-3.5" />
                    {isTriggeringLive ? 'Executing Live Transfer...' : 'Execute Custom Transfer & Analyze'}
                  </button>
                </div>

                {liveTxResult && (
                  <div className="p-2 rounded bg-slate-900/95 border border-slate-800 text-[10px] font-mono space-y-0.5">
                    <div className="flex items-center justify-between">
                      <span className="text-teal-300 font-bold">{liveTxResult.transfer_id}</span>
                      <span
                        className={
                          liveTxResult.status === 'COMPLETED'
                            ? 'text-emerald-400 font-bold'
                            : 'text-rose-400 font-bold'
                        }
                      >
                        {liveTxResult.status}
                      </span>
                    </div>
                    <div className="text-slate-300 truncate">
                      {liveTxResult.error_message
                        ? `${liveTxResult.error_type}: ${liveTxResult.error_message}`
                        : `Fee Charged: INR ${Number(liveTxResult.fee || 0).toFixed(2)}`}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-2.5 rounded-lg bg-slate-950/90 border border-teal-500/30 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-teal-300 uppercase text-[10px]">
                    Custom Support Ticket
                  </span>
                  <select
                    value={customModule}
                    onChange={(e) => setCustomModule(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded px-2 py-0.5 text-[10px] font-mono text-slate-200"
                  >
                    <option value="transfers">transfers</option>
                    <option value="fees">fees</option>
                    <option value="notifications">notifications</option>
                    <option value="limits">limits</option>
                    <option value="settlement">settlement</option>
                  </select>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Type or paste any customer complaint below to run live 4-way verification.
                </p>
              </div>
            )}

            {/* Customer Ticket Text Box */}
            <div className="pt-2 border-t border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-[10px] uppercase font-bold text-slate-300">
                  Customer Complaint Text:
                </label>
                {preflightScan.accountCount > 0 && (
                  <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3" />
                    {preflightScan.accountCount} PII Masked
                  </span>
                )}
              </div>
              <textarea
                value={ticketText}
                onChange={(e) => setTicketText(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 focus:outline-none focus:border-teal-500 font-sans min-h-[105px] leading-relaxed"
                placeholder="Paste customer incident ticket..."
              />
              {preflightScan.hasInjection && (
                <div className="px-2.5 py-1.5 rounded-lg bg-rose-950/80 border border-rose-500/40 text-[10px] font-mono text-rose-300 font-bold">
                  🛡️ Prompt Injection Detected — Will be quarantined before AI
                </div>
              )}
            </div>

            {/* Multimodal Attachment Thumbnail (e.g. S06 screenshot.png) */}
            {intakeMode === 'queue' && selectedScenario?.attachments && selectedScenario.attachments.length > 0 && (
              <div className="p-2 rounded-lg bg-slate-950 border border-teal-500/35 space-y-1.5">
                <div className="flex items-center justify-between text-[10px] font-mono">
                  <span className="text-teal-300 font-bold">📎 Attached Error Screenshot</span>
                  <span className="text-slate-400">Gemini Vision OCR</span>
                </div>
                <img
                  src={`/api/bundles/${selectedScenario.id}/attachments/${selectedScenario.attachments[0]}`}
                  alt="Attached customer error screenshot"
                  className="w-full rounded border border-slate-800 max-h-32 object-contain bg-slate-900"
                />
              </div>
            )}

            {/* Primary CTA Button */}
            <button
              onClick={() => handleStartInvestigation()}
              disabled={isInvestigating || !ticketText.trim()}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-bold text-xs transition-all shadow-lg shadow-teal-950/60 disabled:opacity-50"
            >
              {isInvestigating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Investigating Live ({(elapsedMs / 1000).toFixed(1)}s)...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  Analyze Incident ({intakeMode === 'live' ? 'LIVE' : intakeMode === 'custom' ? 'CUSTOM' : selectedScenario?.ticket_id || selectedScenarioId})
                </>
              )}
            </button>

            {/* Subtle Secondary A2A Delegation Action */}
            <div className="flex items-center justify-between pt-1">
              <span className="text-[10px] text-slate-500">External Agent Interop:</span>
              <button
                onClick={handleDelegateViaA2A}
                disabled={isInvestigating || !ticketText.trim()}
                className="text-[10px] font-mono text-teal-400 hover:text-teal-300 flex items-center gap-1 disabled:opacity-50"
                title="Delegate via Google A2A JSON-RPC 2.0 Protocol"
              >
                <Network className="w-3 h-3" />
                Run via A2A Protocol →
              </button>
            </div>

            {a2aStatusBadge && (
              <div className="p-2 rounded-lg bg-teal-950/60 border border-teal-500/40 text-[10px] font-mono text-teal-200 flex items-center justify-between">
                <span>🔗 {a2aStatusBadge}</span>
                <span className="text-emerald-400 font-bold">A2A-0.2</span>
              </div>
            )}
          </div>
        </div>

        {/* ===================================================================
            COLUMNS 2 & 3: GUIDED IDLE OVERVIEW OR LIVE INVESTIGATION RESULTS
           =================================================================== */}
        {!report && !isInvestigating ? (
          <div className="lg:col-span-9 space-y-4">
            <div className="bg-slate-900/90 border border-slate-800/90 rounded-2xl p-6 shadow-xl space-y-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-md bg-teal-950 text-teal-300 border border-teal-500/30 font-mono text-xs font-bold">
                      READY TO INVESTIGATE
                    </span>
                    <span className="text-xs font-mono text-slate-400">
                      Selected: {intakeMode === 'live' ? 'Live Payment Service' : `${selectedScenario?.ticket_id || selectedScenarioId} — ${selectedScenario?.title || ''}`}
                    </span>
                  </div>
                  <h2 className="text-xl font-bold text-slate-100">
                    See How TriagePilot™ Verifies Root Causes Without Hallucinating
                  </h2>
                  <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
                    {intakeMode === 'queue' && selectedScenario
                      ? selectedScenario.description
                      : 'Click "Analyze Incident" to cross-examine the customer claim against live logs, pinned Git source code, transaction records, and SOP runbooks.'}
                  </p>
                </div>

                <button
                  onClick={() => handleStartInvestigation()}
                  disabled={!ticketText.trim()}
                  className="shrink-0 flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-white font-bold text-xs shadow-lg shadow-teal-950/60 transition-all"
                >
                  <Play className="w-4 h-4 fill-white" />
                  Analyze Selected Incident Now →
                </button>
              </div>

              {/* Quick-Pick Signature Scenarios for 1-Click Exploration */}
              <div className="space-y-2.5">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Or Try a 1-Click Signature Scenario:
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {[
                    {
                      id: 'S01',
                      badge: 'P1 • Timezone Bug',
                      title: '4 PM Cutoff Rejection',
                      desc: 'Customer claims failure since Monday 9 AM; logs & Git prove Tuesday 4:02 PM IST.',
                    },
                    {
                      id: 'S06',
                      badge: 'P2 • Vision OCR',
                      title: 'Screenshot + Limit Bug',
                      desc: 'Extracts TXN-6001 from PNG screenshot & pins >= boundary bug in daily_limit.py.',
                    },
                    {
                      id: 'S04',
                      badge: 'P2 • Stale Runbook',
                      title: 'SMS Retry Drift + Injection',
                      desc: 'Blocks log prompt injection & proves runbook DOC-SMS-01 contradicts sms.py.',
                    },
                    {
                      id: 'S11',
                      badge: 'P2 • Principled Abstain',
                      title: 'Vague Ticket → 2-Turn Fix',
                      desc: 'Abstains when evidence is weak (0.22), asks 2 questions, and resolves on reply.',
                    },
                  ].map((demo) => {
                    const sc = scenarios.find((s) => s.id === demo.id);
                    const isActive = selectedScenarioId === demo.id && intakeMode === 'queue';
                    return (
                      <div
                        key={demo.id}
                        onClick={() => {
                          if (sc) handleScenarioSelect(sc);
                        }}
                        className={`cursor-pointer p-3.5 rounded-xl border transition-all flex flex-col justify-between space-y-2 ${
                          isActive
                            ? 'bg-teal-950/60 border-teal-500/60 shadow-md'
                            : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div className="space-y-1">
                          <span className="text-[10px] font-mono font-bold text-teal-400">
                            {demo.badge}
                          </span>
                          <div className="text-xs font-bold text-slate-100">{demo.title}</div>
                          <p className="text-[11px] text-slate-400 leading-relaxed">{demo.desc}</p>
                        </div>
                        <span className="text-[10px] font-mono text-teal-300 font-semibold pt-1">
                          {isActive ? '✓ Selected — Click Analyze above' : 'Select scenario →'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 4-Step Visual Explanation of What Happens Behind the Scenes */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-2 border-t border-slate-800/80 text-xs">
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                  <div className="font-mono text-[10px] text-teal-400 font-bold">01. SCRUB &amp; ROUTE</div>
                  <div className="font-bold text-slate-200">PII Masking &amp; Smart Pruning</div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Redacts account numbers &amp; prompt injections before activating only needed ADK specialists.
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                  <div className="font-mono text-[10px] text-teal-400 font-bold">02. 4-WAY CHECK</div>
                  <div className="font-bold text-slate-200">Client vs Logs vs Code vs Docs</div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Cross-examines all 4 sources simultaneously to catch false timestamps and stale runbooks.
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                  <div className="font-mono text-[10px] text-teal-400 font-bold">03. PYTHON VERIFIER</div>
                  <div className="font-bold text-slate-200">Zero Hallucinated Citations</div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Deterministic Python validates every 40-char Git commit SHA, line number, and log ID.
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
                  <div className="font-mono text-[10px] text-teal-400 font-bold">04. TRUST &amp; SIGN-OFF</div>
                  <div className="font-bold text-slate-200">Math Trust Gate &amp; Maker-Checker</div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Abstains if evidence is weak (&lt;0.45) and binds human approval to SHA-256 audit hashes.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* ===============================================================
                COLUMN 2: STEP 2 — HOW THE BACKEND INVESTIGATED (lg:col-span-5)
               =============================================================== */}
            <div className="lg:col-span-5 space-y-4">
              {/* Live Backend Activity Ticker during active investigation */}
              {isInvestigating && (
                <div className="rounded-xl border border-amber-500/40 bg-amber-950/30 p-3.5 text-xs space-y-1.5 shadow-lg">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-300 uppercase tracking-wider flex items-center gap-2">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-400" />
                      Backend Pipeline Executing Live
                    </span>
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-500/40 font-bold">
                      {events.length} SSE EVENTS
                    </span>
                  </div>
                  <p className="text-[11px] font-mono text-amber-100/90 truncate">
                    {(() => {
                      const last = events[events.length - 1];
                      if (!last) return 'Initializing PII scrubber & prompt injection shield...';
                      if (last.type === 'masking_done') return 'Stage 01 • PII scrubbed; classifying ticket with Vertex AI gemini-2.5-flash...';
                      if (last.type === 'plan_created' || last.type === 'adk_orchestration')
                        return `Stage 02–03 • Routing to ADK ParallelAgent swarm (${last.data?.active_agents?.length || 4} specialists)...`;
                      if (last.type === 'tool_started')
                        return `Stage 03–08 • ${last.data?.agent || 'Engine'} executing ${last.data?.tool || 'operation'}${last.data?.detail ? ` — ${last.data.detail}` : ''}...`;
                      if (last.type === 'verifier_result')
                        return `Stage 04 • Python Verifier validated ${last.data?.verified_count ?? 0} proof cards (${last.data?.dropped_count ?? 0} dropped)...`;
                      if (last.type === 'contradiction_found')
                        return `Stage 05 • 4-Way Reconciler flagged ${last.data?.kind || 'contradiction'}...`;
                      if (last.type === 'hypothesis_update')
                        return 'Stage 06–07 • Hypotheses ranked; computing deterministic Trust Score...';
                      if (last.type === 'trust_update')
                        return 'Stage 08 • Synthesizing LeakCheck-safe customer reply & Jira ticket...';
                      return `Active event: ${last.type}`;
                    })()}
                  </p>
                </div>
              )}

              {/* High-Visibility Prompt Injection Quarantined Banner */}
              {hasInjection && (
                <div className="rounded-xl border border-rose-500/50 bg-rose-950/40 p-3.5 text-xs space-y-1 shadow-lg">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-rose-300 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertCircle className="w-4 h-4 text-rose-400" />
                      Prompt Injection Attack Blocked
                    </span>
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-500/40 font-bold">
                      STAGE 01 QUARANTINED
                    </span>
                  </div>
                  <p className="text-[11px] text-rose-200/90 leading-relaxed">
                    {report?.routing_plan?.injection_note ||
                      'Adversarial instruction override was neutralized with [INJECTION_QUARANTINED] before reaching Gemini.'}
                  </p>
                </div>
              )}

              {/* What Actually Happened: 4-Way Reality Cross-Check */}
              {fourWaySummary && (
                <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30 font-mono text-[10px] font-bold">
                        STEP 2
                      </span>
                      <span className="font-bold text-xs uppercase tracking-wider text-slate-100">
                        4-Way Reality Cross-Check
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-400">
                      Client vs Logs vs Git vs Docs
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {Object.values(fourWaySummary).map((quad, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-slate-950/90 border border-slate-800/90 space-y-1"
                      >
                        <div className="flex items-center justify-between gap-1">
                          <span className="text-[11px] font-bold text-slate-200">{quad.title}</span>
                          <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${quad.badgeColor}`}>
                            {quad.badge}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-300 leading-snug line-clamp-2">
                          {quad.detail}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Unified Tabbed Backend Execution Inspector (Swarm | Live Trace | AI Calls) */}
              <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
                  <span className="font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                    <Cpu className="w-4 h-4 text-teal-400" />
                    Backend Execution Inspector
                  </span>

                  <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-[11px] font-semibold">
                    <button
                      onClick={() => setInspectorTab('swarm')}
                      className={`px-2.5 py-1 rounded transition-colors ${
                        inspectorTab === 'swarm' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      Agent Swarm ({report?.routing_plan?.active_agents?.length || 0}/5)
                    </button>
                    <button
                      onClick={() => setInspectorTab('trace')}
                      className={`px-2.5 py-1 rounded transition-colors flex items-center gap-1 ${
                        inspectorTab === 'trace' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {isInvestigating && <span className="w-1.5 h-1.5 rounded-full bg-amber-300 animate-ping" />}
                      Live Trace ({events.length})
                    </button>
                    <button
                      onClick={() => setInspectorTab('models')}
                      className={`px-2.5 py-1 rounded transition-colors ${
                        inspectorTab === 'models' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      AI Calls ({report?.execution?.calls?.length || 0})
                    </button>
                  </div>
                </div>

                {inspectorTab === 'swarm' && (
                  <RouterBar
                    routingPlan={report?.routing_plan}
                    activeAgents={report?.routing_plan?.active_agents}
                  />
                )}

                {inspectorTab === 'trace' && (
                  <TimelineStream
                    events={events}
                    contradictions={report?.contradictions}
                    isStreaming={isInvestigating}
                  />
                )}

                {inspectorTab === 'models' && (
                  <div className="space-y-2 text-xs">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-400">
                      <span>Mode: <strong className="text-emerald-300">{report?.execution?.mode?.toUpperCase() || 'LIVE'}</strong></span>
                      <span>Provider: <strong className="text-teal-300">{report?.execution?.provider || 'vertex_ai'}</strong></span>
                      <span>Tokens: <strong className="text-slate-200">{report?.metrics?.tokens ?? 0}</strong></span>
                      <span>Cost: <strong className="text-emerald-300">${(report?.metrics?.cost_usd ?? 0).toFixed(4)}</strong></span>
                    </div>
                    {report?.execution?.calls && report.execution.calls.length > 0 ? (
                      <div className="space-y-1.5">
                        {report.execution.calls.map((c: any, idx: number) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px]"
                          >
                            <span className="text-slate-200 font-semibold">{c.operation}</span>
                            <span className="text-teal-300">
                              {c.model} {c.tokens ? `• ${c.tokens} tok ` : ''}• {c.latency_ms ?? 0}ms
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-4 text-center text-slate-500 bg-slate-950 rounded-lg border border-slate-800">
                        Deterministic fast-path completed without additional model calls.
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Operator Action Controls (Maker-Checker / Engineer Steer / Client Follow-Up / Contradictory Evidence) */}
              <PilotMiddleControls
                report={report}
                investigationId={investigationId}
                selectedScenario={selectedScenario}
                onDecisionSubmitted={(updated) => setReport(updated)}
                onSimulateReply={handleSimulateReply}
                onDevSteer={handleDevSteer}
                onEvidenceUpdate={handleEvidenceUpdate}
                isStreaming={isInvestigating}
              />
            </div>

            {/* ===============================================================
                COLUMN 3: STEP 3 — VERIFIED VERDICT, DRAFTS & PROOF (lg:col-span-4)
               =============================================================== */}
            <div className="lg:col-span-4 space-y-4">
              {isInvestigating && !report && (
                <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono text-[10px] font-bold">
                      STEP 3 • VERIFYING
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">Awaiting Verifier &amp; Trust Gate</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Verifying Git commit SHAs, AST line numbers, log timestamps, and runbook sections before unlocking root-cause verdict and drafts...
                  </p>
                </div>
              )}

              {/* 0. Withdrawn / Superseded Prior Conclusion Banner (when contradictory evidence or re-investigation updates verdict) */}
              {report?.withdrawn_conclusion && (
                <div className="bg-rose-950/40 border border-rose-500/50 rounded-xl p-3.5 shadow-xl space-y-2 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-bold text-rose-300 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertCircle className="w-4 h-4 text-rose-400" />
                      Prior Conclusion Withdrawn (Rev #{report.withdrawn_conclusion.prior_report_revision} → Rev #{report.report_revision})
                    </span>
                    <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-rose-950 text-rose-200 border border-rose-500/40">
                      PRIOR APPROVAL INVALIDATED ({report.withdrawn_conclusion.invalidated_by})
                    </span>
                  </div>
                  <div className="p-2 rounded bg-slate-950/80 border border-rose-500/30 text-[11px] text-slate-400 line-through">
                    Superseded Statement: {report.withdrawn_conclusion.withdrawn_hypothesis}
                  </div>
                  <p className="text-[11px] text-rose-200 leading-relaxed">
                    <strong>Reason:</strong> {report.withdrawn_conclusion.withdrawal_reason}
                  </p>
                </div>
              )}

              {/* 1. Verified Root-Cause Verdict (Hero Outcome Card at Top!) */}
              {report && (
                <div className="bg-slate-900/90 border border-teal-500/40 rounded-xl p-4 shadow-xl space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono text-[10px] font-bold">
                        STEP 3
                      </span>
                      <span className="font-bold text-xs uppercase tracking-wider text-slate-100">
                        {report.probable_root_cause ? 'Verified Root Cause' : 'Triage Resolution'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                        Rev #{report.report_revision || 1}
                      </span>
                      <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800">
                        {report.owner_team}
                      </span>
                      {report.probable_root_cause?.evidence_level && (
                        <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40">
                          {report.probable_root_cause.evidence_level}
                        </span>
                      )}
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
                            <span className="text-slate-400">Culprit File:</span>
                            <span className="text-teal-300 font-semibold truncate">
                              {report.probable_root_cause.culprit_files.join(', ')}
                            </span>
                          </div>
                        )}
                        {report.probable_root_cause.culprit_commit && (
                          <div className="text-[11px] flex items-center justify-between gap-2">
                            <span className="text-slate-400">Verified Git SHA:</span>
                            <span className="text-emerald-300 font-semibold">
                              {report.probable_root_cause.culprit_commit}
                            </span>
                          </div>
                        )}
                        {report.probable_root_cause.supporting_card_ids?.length > 0 && (
                          <div className="text-[11px] flex items-center justify-between gap-2">
                            <span className="text-slate-400">Proof Cards:</span>
                            <span className="text-slate-200 font-semibold">
                              {report.probable_root_cause.supporting_card_ids.join(', ')}
                            </span>
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <p className="text-xs text-slate-200 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800">
                      {report.summary}
                    </p>
                  )}

                  {report.kb_gap && (
                    <div className="p-2.5 rounded-lg bg-amber-950/35 border border-amber-500/30 text-[11px] text-amber-200">
                      <strong className="uppercase text-[10px] text-amber-400 block mb-0.5">
                        Stale Runbook Detected ({report.kb_gap.page_id}):
                      </strong>
                      {report.kb_gap.issue}
                    </div>
                  )}
                </div>
              )}

              {/* 1b. Allowlisted Recommended Next Useful Check (Decision-First Operator Card) */}
              {report?.next_check && (
                <div className="bg-slate-900/90 border border-sky-500/40 rounded-xl p-4 shadow-xl space-y-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-sky-400" />
                      <span className="font-bold text-xs uppercase tracking-wider text-slate-100">
                        Next Useful Check
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-500/40">
                        {report.next_check.check_id}
                      </span>
                      <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800">
                        {report.next_check.target_system} • {report.next_check.effort_level.toUpperCase()} EFFORT
                      </span>
                    </div>
                  </div>

                  <div className="text-xs font-bold text-slate-100">
                    {report.next_check.title}
                  </div>

                  <div className="space-y-1 text-[11px] text-slate-300 leading-relaxed">
                    <div>
                      <strong className="text-sky-300">Purpose:</strong> {report.next_check.purpose}
                    </div>
                    {report.next_check.expected_outcomes?.length > 0 && (
                      <div>
                        <strong className="text-emerald-300">Expected Signal:</strong> {report.next_check.expected_outcomes.join(' | ')}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 2. Mathematical Trust Meter */}
              <TrustMeter trust={report?.trust} />

              {/* 3. Ready-to-Send Outputs (Customer Reply & Engineering Bug Draft) */}
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
                        Engineering Bug Ticket
                      </button>
                    </div>
                    <button
                      onClick={draftTab === 'reply' ? handleCopyCustomerDraft : handleCopyJira}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-mono flex items-center gap-1 transition-colors border border-slate-700"
                    >
                      {(draftTab === 'reply' ? copiedDraft : copiedJira) ? (
                        <Check className="w-3 h-3 text-emerald-400" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                      Copy
                    </button>
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
                          ✓ LeakCheck Passed
                        </span>
                      </div>
                      <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs text-slate-200 leading-relaxed font-sans max-h-40 overflow-y-auto whitespace-pre-wrap">
                        {report.customer_reply_draft}
                      </div>
                    </div>
                  ) : (
                    <div>
                      {report.jira_draft ? (
                        <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs text-slate-200 space-y-2 max-h-48 overflow-y-auto font-mono">
                          <div className="font-bold text-teal-300">{report.jira_draft.title}</div>
                          <div className="text-[11px] whitespace-pre-wrap text-slate-300 font-sans leading-relaxed">
                            {report.jira_draft.description}
                          </div>
                          {report.jira_draft.evidence_links?.length > 0 && (
                            <div className="pt-2 border-t border-slate-800 text-[10px] text-teal-400 space-y-0.5">
                              <div className="font-bold text-slate-400 uppercase">Verified Proof Permalinks:</div>
                              {report.jira_draft.evidence_links.map((lnk, i) => (
                                <div key={i} className="truncate">• {lnk}</div>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-xs text-slate-500 text-center">
                          No engineering bug ticket needed for this resolution type.
                        </div>
                      )}
                    </div>
                  )}

                  {report.questions_for_client?.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/80">
                      <span className="text-[10px] uppercase font-bold text-amber-400 block mb-1.5 flex items-center gap-1">
                        <HelpCircle className="w-3.5 h-3.5" /> Clarifying Questions for Customer:
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

              {/* 4. Verified Evidentiary Proof Cards (Single-Row Filter) */}
              <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-4 shadow-xl space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <span className="font-bold text-xs uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Verified Proof Citations
                  </span>
                  <div className="flex items-center gap-1.5 text-[10px] font-mono">
                    <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30 font-bold">
                      {report?.verified_cards?.length || 0} Verified
                    </span>
                    {(report?.dropped_cards?.length || 0) > 0 && (
                      <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-500/30 font-bold">
                        {report?.dropped_cards?.length} Dropped
                      </span>
                    )}
                  </div>
                </div>

                {report && (
                  <div className="flex flex-wrap items-center gap-1 text-[10px] font-mono">
                    {[
                      { id: 'all', src: 'all', label: `All (${(report.verified_cards?.length || 0) + (report.dropped_cards?.length || 0)})` },
                      { id: 'primary', src: 'all', label: `Root Cause (${primaryCardIds.size})` },
                      { id: 'all', src: 'code', label: 'Git Code' },
                      { id: 'all', src: 'log', label: 'Logs' },
                      { id: 'all', src: 'doc', label: 'Runbooks' },
                      { id: 'dropped', src: 'all', label: `Dropped (${report.dropped_cards?.length || 0})` },
                    ].map((tab, i) => {
                      const active = evidenceFilter === tab.id && sourceFilter === tab.src;
                      return (
                        <button
                          key={i}
                          onClick={() => {
                            setEvidenceFilter(tab.id as any);
                            setSourceFilter(tab.src);
                          }}
                          className={`px-2 py-1 rounded border transition-colors ${
                            active
                              ? 'bg-teal-600 text-white border-teal-500 font-bold'
                              : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                          }`}
                        >
                          {tab.label}
                        </button>
                      );
                    })}
                  </div>
                )}

                <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
                  {sortedAndFilteredCards.length === 0 ? (
                    <div className="text-center py-6 text-slate-500 text-xs">
                      No proof cards match this filter.
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
            </div>
          </>
        )}
      </div>

      {/* Proof Inspector Modal */}
      <ProofModal card={inspectedCard} onClose={() => setInspectedCard(null)} />
    </div>
  );
};
