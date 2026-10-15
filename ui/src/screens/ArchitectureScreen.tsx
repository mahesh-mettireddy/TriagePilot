import React, { useState, useEffect } from 'react';
import { getProfile } from '../api';
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
} from 'lucide-react';

export const ArchitectureScreen: React.FC = () => {
  const [profile, setProfile] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<'diagram' | 'connectors' | 'profile'>('diagram');

  useEffect(() => {
    async function load() {
      try {
        const data = await getProfile();
        setProfile(data);
      } catch (err) {
        console.error('Failed to load profile', err);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-teal-950 text-teal-300 border border-teal-500/30">
              HEXAGONAL PORTS &amp; ADAPTERS
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Zero-Hallucination Verifier • Mathematical Trust Gate • Cryptographic Ledger
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100">
            TriagePilot™ Architecture &amp; Enterprise Connectors
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-3xl">
            TriagePilot™ decouples the neuro-symbolic reasoning engine from external repositories, telemetry, and ticketing systems via 6 typed hexagonal ports in <code className="text-teal-300 font-mono">engine/ports/base.py</code>.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-semibold shrink-0">
          <button
            onClick={() => setActiveTab('diagram')}
            className={`px-3.5 py-1.5 rounded-lg transition-colors ${
              activeTab === 'diagram' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            10-Stage Pipeline
          </button>
          <button
            onClick={() => setActiveTab('connectors')}
            className={`px-3.5 py-1.5 rounded-lg transition-colors ${
              activeTab === 'connectors' ? 'bg-teal-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Enterprise Connectors
          </button>
          <button
            onClick={() => setActiveTab('profile')}
            className={`px-3.5 py-1.5 rounded-lg transition-colors ${
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
              <h4 className="font-bold text-slate-100 text-xs">5-Agent Swarm &amp; Python Verifier</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Active specialists query read ports concurrently under a strict 12-call tool budget. Pure-Python <code className="text-teal-300 font-mono">verifier.py</code> validates every commit SHA, line range, log ID, and doc section.
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
                    Historical incidents, Known Errors (<code className="font-mono">KE-*</code>), and deployment change records (<code className="font-mono">CHG-*</code>).
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

      {/* Tab 2: Enterprise Connectors */}
      {activeTab === 'connectors' && (
        <div className="bg-slate-900/90 border border-slate-800/90 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                <Plug className="w-4 h-4 text-teal-400" />
                Plug-and-Play Enterprise Adapter Matrix
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Connect live production repositories, observability streams, and ticketing systems without changing a single line of the core verifier or trust engine.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="font-mono text-teal-400 font-bold">1. CodePort → GitHub / GitLab API</span>
              <p className="text-slate-300 leading-relaxed">
                Point <code className="text-teal-300 font-mono">CodePort</code> to GitHub GraphQL/REST APIs or a shallow bare Git mirror. <code className="text-teal-300 font-mono">verifier.py</code> validates every 40-char commit SHA and line range before citations are accepted.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="font-mono text-teal-400 font-bold">2. LogPort → Cloud Logging / Datadog</span>
              <p className="text-slate-300 leading-relaxed">
                Implement <code className="text-teal-300 font-mono">LogPort</code> over <code className="font-mono">google-cloud-logging</code>, Datadog, or OpenTelemetry traces. <code className="text-teal-300 font-mono">verifier.py</code> re-verifies <code className="font-mono">insertId</code> and UTC timestamps within ±1s tolerance.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="font-mono text-teal-400 font-bold">3. KnowledgePort → Confluence / Vertex Search</span>
              <p className="text-slate-300 leading-relaxed">
                Connect Confluence CQL or Vertex AI Search. <code className="text-teal-300 font-mono">reconcile.py</code> compares <code className="font-mono">doc.last_updated</code> against <code className="font-mono">commit.date</code> to flag <code className="text-amber-300 font-mono">STALE_DOC_FLAG</code> automatically.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="font-mono text-teal-400 font-bold">4. RecordPort → Read-Replica Snapshot API</span>
              <p className="text-slate-300 leading-relaxed">
                Execute parameterized read-only lookups against AlloyDB/Cloud SQL replicas and pass records through <code className="text-teal-300 font-mono">mask_for_model()</code> before specialist inspection.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="font-mono text-teal-400 font-bold">5. HistoryPort → Jira / ServiceNow / Cloud Deploy</span>
              <p className="text-slate-300 leading-relaxed">
                Query past resolved incidents, Known Error databases, and deployment windows to power 2-call fast-path resolution for known operational issues.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="font-mono text-teal-400 font-bold">6. MCP Server Bridge Support</span>
              <p className="text-slate-300 leading-relaxed">
                Wrap standard Model Context Protocol (MCP) tools (GitHub MCP, Cloud Observability MCP, Atlassian MCP) inside TriagePilot&apos;s <code className="text-teal-300 font-mono">ToolBudget</code> (max 12 calls) and deterministic verifier.
              </p>
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
