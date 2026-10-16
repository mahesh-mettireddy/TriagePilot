import React, { useState, useEffect } from 'react';
import {
  getProfile,
  getConnectorsStatus,
  getA2AAgentCard,
  getLiveIssues,
  syncLiveRepo,
} from '../api';
import {
  Cpu,
  ShieldCheck,
  Database,
  CheckCircle2,
  Terminal,
  FileCode,
  Lock,
  Workflow,
  Plug,
  Network,
  RefreshCw,
  GitCommit,
} from 'lucide-react';

export const ArchitectureScreen: React.FC = () => {
  const [profile, setProfile] = useState<Record<string, any>>({});
  const [connectors, setConnectors] = useState<Record<string, any> | null>(null);
  const [agentCard, setAgentCard] = useState<Record<string, any> | null>(null);
  const [liveIssues, setLiveIssues] = useState<any[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState<'diagram' | 'connectors' | 'a2a' | 'profile'>('diagram');

  const loadAll = async () => {
    try {
      const [profData, connData, cardData, issuesData] = await Promise.all([
        getProfile().catch(() => ({})),
        getConnectorsStatus().catch(() => null),
        getA2AAgentCard().catch(() => null),
        getLiveIssues().catch(() => []),
      ]);
      setProfile(profData);
      if (connData) setConnectors(connData);
      if (cardData) setAgentCard(cardData);
      setLiveIssues(Array.isArray(issuesData) ? issuesData : (issuesData as any)?.issues || []);
    } catch (err) {
      console.error('Failed to load architecture telemetry', err);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await syncLiveRepo();
      await loadAll();
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-teal-950 text-teal-300 border border-teal-500/30">
              HEXAGONAL PORTS &amp; ADAPTERS
            </span>
            <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30">
              GOOGLE ADK + A2A PROTOCOL v0.2
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Zero-Hallucination Verifier • Mathematical Trust Gate • Cryptographic Ledger
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100">
            TriagePilot™ Architecture, Live Connectors &amp; Agent Interoperability
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            TriagePilot™ decouples the neuro-symbolic reasoning engine from live target repositories, telemetry streams, and ITSM write-back systems via 6 typed hexagonal ports in <code className="text-teal-300 font-mono">engine/ports/base.py</code>, orchestrated by Google ADK and exposed via the Google A2A Protocol.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-semibold shrink-0 flex-wrap gap-1">
          <button
            onClick={() => setActiveTab('diagram')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'diagram' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            10-Stage Pipeline
          </button>
          <button
            onClick={() => setActiveTab('connectors')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'connectors' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Live Connectors ({connectors?.ports?.length || 6})
          </button>
          <button
            onClick={() => setActiveTab('a2a')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'a2a' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Google ADK &amp; A2A Protocol
          </button>
          <button
            onClick={() => setActiveTab('profile')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'profile' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Active Profile (YAML)
          </button>
        </div>
      </div>

      {/* Tab 1: System Diagram */}
      {activeTab === 'diagram' && (
        <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-6 shadow-xl space-y-6">
          <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
            <Workflow className="w-4 h-4 text-teal-400" />
            End-to-End Neuro-Symbolic Triage Architecture
          </h3>

          {/* 4 Macro Pipeline Stage Blocks */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-teal-400 font-bold">STAGES 01–02</span>
                <Lock className="w-4 h-4 text-emerald-400" />
              </div>
              <h4 className="font-bold text-slate-100 text-xs">PII Scrubbing &amp; Dynamic Router</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Deterministic PII scrubber masks accounts, PAN, IFSC, phone, and email tokens and quarantines prompt injections before Gemini 2.5 Flash classifies the ticket and prunes unneeded agents.
              </p>
            </div>

            <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-teal-400 font-bold">STAGES 03–04</span>
                <Cpu className="w-4 h-4 text-teal-400" />
              </div>
              <h4 className="font-bold text-slate-100 text-xs">ADK 5-Agent Swarm &amp; Python Verifier</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Google ADK <code className="text-teal-300 font-mono">ParallelAgent</code> specialists query read ports concurrently under a strict 12-call tool budget. Pure-Python <code className="text-teal-300 font-mono">verifier.py</code> validates every commit SHA, line range, log ID, and doc section.
              </p>
            </div>

            <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-teal-400 font-bold">STAGES 05–07</span>
                <ShieldCheck className="w-4 h-4 text-amber-400" />
              </div>
              <h4 className="font-bold text-slate-100 text-xs">4-Way Reconciler &amp; Trust Math</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Flags <code className="text-amber-300 font-mono">TIME_MISMATCH</code>, <code className="text-amber-300 font-mono">STALE_DOC_FLAG</code>, and <code className="text-amber-300 font-mono">BEHAVIOUR_MISMATCH</code>. Computes deterministic Trust Score and abstains if Trust &lt; 0.45.
              </p>
            </div>

            <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-teal-400 font-bold">STAGES 08–10</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <h4 className="font-bold text-slate-100 text-xs">LeakCheck, SHA-256 &amp; Maker-Checker</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Sanitizes customer replies via <code className="text-teal-300 font-mono">leakcheck.py</code>, appends to the SHA-256 hash-chained audit ledger, and enforces revision-bound human approval before write-back.
              </p>
            </div>
          </div>

          {/* 6 Hexagonal Ports */}
          <div className="pt-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-teal-400 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5" /> 5 Read-Only Evidentiary Ports (engine/ports/base.py)
              </h4>
              <div className="space-y-2 text-xs">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <strong className="text-teal-300 font-mono">CodePort:</strong>{' '}
                  <span className="text-slate-300">
                    Read-only Git inspection at pinned 40-char commit SHA (<code className="font-mono">search_code</code>, <code className="font-mono">read_lines</code>, <code className="font-mono">git_blame</code>, <code className="font-mono">git_diff</code>, <code className="font-mono">git_log</code>).
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <strong className="text-teal-300 font-mono">LogPort:</strong>{' '}
                  <span className="text-slate-300">
                    Normalized application telemetry (<code className="font-mono">query_logs</code>, <code className="font-mono">digest_signatures</code>, <code className="font-mono">trace_lookup</code>).
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <strong className="text-teal-300 font-mono">KnowledgePort:</strong>{' '}
                  <span className="text-slate-300">
                    Runbooks and architecture docs with <code className="font-mono">last_updated</code> timestamps (<code className="font-mono">search_docs</code>, <code className="font-mono">get_doc_section</code>).
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <strong className="text-teal-300 font-mono">HistoryPort:</strong>{' '}
                  <span className="text-slate-300">
                    Historical incidents, Known Errors (<code className="font-mono">KE-*</code>), and live Git deployment change records (<code className="font-mono">CHG-*</code>).
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <strong className="text-teal-300 font-mono">RecordPort:</strong>{' '}
                  <span className="text-slate-300">
                    Parameterized, pre-masked transaction/ledger snapshots (<code className="font-mono">get_transfer_record</code> — zero raw SQL).
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-teal-400 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5" /> Maker-Checker WritePort &amp; Cryptographic Governance
              </h4>
              <div className="space-y-2 text-xs">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <strong className="text-emerald-300 font-mono">WritePort.create_issue():</strong>{' '}
                  <span className="text-slate-300">
                    Creates engineering bug tickets with verified code permalinks and repro steps only after human sign-off.
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <strong className="text-emerald-300 font-mono">WritePort.post_comment():</strong>{' '}
                  <span className="text-slate-300">
                    Posts <code className="font-mono">LeakCheck</code>-verified customer responses back to the support channel.
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <strong className="text-teal-300 font-mono">Revision &amp; Hash Binding (policy.py):</strong>{' '}
                  <span className="text-slate-300">
                    Every approval payload is verified against <code className="font-mono">report_revision</code>, <code className="font-mono">report_hash</code>, and <code className="font-mono">decision_id</code> idempotency keys.
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                  <strong className="text-teal-300 font-mono">SHA-256 Audit Chain (audit.py):</strong>{' '}
                  <span className="text-slate-300">
                    Every pipeline step appends <code className="font-mono">SHA256(prev_hash || canonical_json)</code> to Cloud Firestore.
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Live Enterprise Connectors */}
      {activeTab === 'connectors' && (
        <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-6 shadow-xl space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
            <div>
              <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                <Plug className="w-4 h-4 text-teal-400" />
                Live Hexagonal Port Telemetry &amp; Target Repository Bridge
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Real-time connection status across all 6 Hexagonal Ports (<code className="text-teal-300 font-mono">engine/adapters/live_adapter.py</code>).
              </p>
            </div>
            <button
              onClick={handleSync}
              disabled={isSyncing}
              className="px-3 py-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-teal-500/40 text-teal-300 font-mono text-xs flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
              Sync Live Workspace &amp; Refresh Ports
            </button>
          </div>

          {/* Live Git Mirror & Telemetry Summary */}
          {connectors && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-[10px] text-slate-400 uppercase">Target Git HEAD SHA</span>
                <div className="text-sm font-bold text-teal-300 flex items-center gap-1.5">
                  <GitCommit className="w-4 h-4 text-teal-400" />
                  {connectors.git_workspace?.short_sha}
                </div>
                <div className="text-[10px] text-slate-400 truncate">
                  {connectors.git_workspace?.head_message}
                </div>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-[10px] text-slate-400 uppercase">Live Telemetry Events</span>
                <div className="text-sm font-bold text-emerald-300">
                  {connectors.telemetry?.live_logs_count ?? 0} JSONL Logs
                </div>
                <div className="text-[10px] text-slate-400">data/live/logs.jsonl</div>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-[10px] text-slate-400 uppercase">Live Ledger Snapshots</span>
                <div className="text-sm font-bold text-teal-300">
                  {connectors.telemetry?.live_records_count ?? 0} Masked Records
                </div>
                <div className="text-[10px] text-slate-400">data/live/records.json</div>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                <span className="text-[10px] text-slate-400 uppercase">Approved Write-Backs</span>
                <div className="text-sm font-bold text-amber-300">
                  {connectors.telemetry?.live_issues_count ?? 0} Persisted Issues
                </div>
                <div className="text-[10px] text-slate-400">data/live/issues.json</div>
              </div>
            </div>
          )}

          {/* 6 Live Port Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            {(connectors?.ports || []).map((p: any, idx: number) => (
              <div key={idx} className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-teal-400 font-bold">{p.port}</span>
                  <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40 font-mono text-[10px] font-bold">
                    {p.status}
                  </span>
                </div>
                <div className="font-mono text-[11px] text-slate-200">{p.adapter}</div>
                <div className="font-mono text-[10px] text-teal-300/90 truncate">{p.target}</div>
                <p className="text-slate-400 text-[11px] leading-relaxed">{p.detail}</p>
              </div>
            ))}
          </div>

          {/* Live Approved Issues Ledger */}
          {liveIssues.length > 0 && (
            <div className="pt-3 border-t border-slate-800 space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-teal-300">
                Recent Maker-Checker Approved Issues (LiveWriteAdapter)
              </h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {liveIssues.slice(0, 5).map((iss, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs font-mono"
                  >
                    <div className="truncate pr-3">
                      <span className="text-teal-300 font-bold mr-2">{iss.issue_key}</span>
                      <span className="text-slate-200">{iss.title}</span>
                    </div>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30 shrink-0">
                      {iss.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Google ADK & A2A Protocol */}
      {activeTab === 'a2a' && (
        <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-6 shadow-xl space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
            <div>
              <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                <Network className="w-4 h-4 text-teal-400" />
                Google ADK Swarm Orchestration &amp; A2A Agent2Agent Protocol
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Standardized multi-agent discovery (<code className="text-teal-300 font-mono">GET /.well-known/agent.json</code>) and JSON-RPC 2.0 task delegation (<code className="text-teal-300 font-mono">POST /a2a</code>).
              </p>
            </div>
            <span className="font-mono text-xs px-2.5 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40 font-bold">
              ADK ParallelAgent + A2A v0.2.0 ACTIVE
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-teal-300">
                Google ADK Specialist Swarm Topology (`engine/adk_orchestration.py`)
              </h4>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
                <div className="flex items-center justify-between font-mono">
                  <span className="text-slate-400">Orchestrator Class:</span>
                  <span className="text-teal-300 font-bold">
                    {agentCard?.adk_orchestration?.root_agent || 'TriagePilotSpecialistSwarm'} (ParallelAgent)
                  </span>
                </div>
                <div className="flex items-center justify-between font-mono">
                  <span className="text-slate-400">Model Backing:</span>
                  <span className="text-emerald-300">
                    {agentCard?.adk_orchestration?.model || 'gemini-2.5-flash'}
                  </span>
                </div>
                <div className="flex items-center justify-between font-mono">
                  <span className="text-slate-400">Hard Tool Call Budget:</span>
                  <span className="text-amber-300 font-bold">12 calls / investigation</span>
                </div>
                <div className="pt-2 border-t border-slate-800 space-y-1.5">
                  {(agentCard?.adk_orchestration?.sub_agents || []).map((sa: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-2 rounded bg-slate-900 border border-slate-800 flex items-center justify-between font-mono text-[11px]"
                    >
                      <span className="text-teal-300 font-bold">{sa.name}</span>
                      <span className="text-slate-400">
                        {sa.port} • max {sa.max_calls} calls
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-teal-300">
                Live A2A Agent Card (`/.well-known/agent.json`)
              </h4>
              <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto leading-relaxed max-h-[340px]">
                <code>{JSON.stringify(agentCard || { status: 'loading' }, null, 2)}</code>
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Profile YAML */}
      {activeTab === 'profile' && (
        <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <FileCode className="w-4 h-4 text-teal-400" />
                Active Domain Profile Configuration
              </h3>
              <p className="text-xs text-slate-400">
                Declarative YAML configuration governing service ownership mappings, PII scrubbing rules, and tool budgets
              </p>
            </div>
            <span className="font-mono text-xs px-2.5 py-1 rounded bg-teal-950 text-teal-300 border border-teal-500/30">
              profiles/transfers.yaml
            </span>
          </div>

          <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto leading-relaxed max-h-[550px]">
            <code>{JSON.stringify(profile, null, 2)}</code>
          </pre>
        </div>
      )}
    </div>
  );
};
