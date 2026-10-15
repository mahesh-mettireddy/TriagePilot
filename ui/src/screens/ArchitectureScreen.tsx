import React, { useState, useEffect } from 'react';
import { getProfile } from '../api';
import { 
  Layers, 
  Cpu, 
  ShieldCheck, 
  GitBranch, 
  Database, 
  BookOpen, 
  FileText, 
  CheckCircle2, 
  Terminal, 
  ArrowRight, 
  FileCode, 
  ExternalLink,
  Lock,
  Workflow
} from 'lucide-react';

export const ArchitectureScreen: React.FC = () => {
  const [profile, setProfile] = useState<Record<string, any>>({});
  const [activeTab, setActiveTab] = useState<'diagram' | 'profile' | 'onboarding'>('diagram');

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
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-teal-950 text-teal-400 border border-teal-500/30">
              HEXAGONAL ARCHITECTURE
            </span>
            <span className="text-xs text-slate-500 font-mono">
              Ports & Adapters • Strict Trust Gate • Zero Phantom Hallucinations
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100">
            System Architecture & Extensibility
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            TriagePilot decouples the AI reasoning engine from external observability systems via clean ports, enforcing deterministic verification before any claim reaches a triage brief.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-medium">
          <button
            onClick={() => setActiveTab('diagram')}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              activeTab === 'diagram' ? 'bg-teal-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            System Diagram
          </button>
          <button
            onClick={() => setActiveTab('profile')}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              activeTab === 'profile' ? 'bg-teal-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Product Profile (YAML)
          </button>
          <button
            onClick={() => setActiveTab('onboarding')}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              activeTab === 'onboarding' ? 'bg-teal-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            10-Min Onboarding
          </button>
        </div>
      </div>

      {/* Tab 1: System Diagram */}
      {activeTab === 'diagram' && (
        <div className="space-y-6">
          {/* Hexagonal Pipeline Layout */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
            <h3 className="font-semibold text-sm text-slate-200 flex items-center gap-2">
              <Workflow className="w-4 h-4 text-teal-400" />
              End-to-End 12-Step Triage Pipeline
            </h3>

            {/* Pipeline Stage Blocks */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Step 1: Ingestion */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-teal-400 font-bold">STAGE 01</span>
                  <Lock className="w-4 h-4 text-emerald-400" />
                </div>
                <h4 className="font-bold text-slate-200 text-xs">Ingest & Mask PII</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Presidio PII scrubber replaces PAN, Aadhaar, email, and phone with deterministic tokens. LeakCheck verifies zero leakage before model ingestion.
                </p>
              </div>

              {/* Step 2: Routing & Specialists */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-teal-400 font-bold">STAGE 02</span>
                  <Cpu className="w-4 h-4 text-teal-400" />
                </div>
                <h4 className="font-bold text-slate-200 text-xs">Route & Specialist Swarm</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Dynamic planner classifies ticket & prunes unnecessary agents (e.g. prunes Code/Logs for user how-tos). Active specialists query read ports concurrently.
                </p>
              </div>

              {/* Step 3: Verifier & Reconciler */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-teal-400 font-bold">STAGE 03</span>
                  <ShieldCheck className="w-4 h-4 text-amber-400" />
                </div>
                <h4 className="font-bold text-slate-200 text-xs">Verifier & Reconciler</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Deterministic Verifier checks AST/line anchors and drops hallucinated claims. Reconciler resolves TIME_MISMATCH and BEHAVIOUR_MISMATCH contradictions.
                </p>
              </div>

              {/* Step 4: Trust & Maker-Checker */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-teal-400 font-bold">STAGE 04</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
                <h4 className="font-bold text-slate-200 text-xs">Trust Math & Human Gate</h4>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Calculates formula-driven Trust Score (0.00-1.00). Maker-Checker gate requires human sign-off before any mutation pushes to Jira or the client.
                </p>
              </div>
            </div>

            {/* Ports & Adapters Architecture Details */}
            <div className="pt-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Left: Read Ports */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-teal-400 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5" /> Pluggable Read Ports
                </h4>
                <div className="space-y-2 text-xs">
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-850">
                    <strong className="text-slate-200">GitPort:</strong> Clones client repositories, extracts commit history, diffs, and AST line anchors.
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-850">
                    <strong className="text-slate-200">LogPort:</strong> Searches distributed logs, traces, exceptions, and boundary metrics.
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-850">
                    <strong className="text-slate-200">DocPort:</strong> Indexes runbooks, architecture specs, and detected stale doc flags.
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-850">
                    <strong className="text-slate-200">RecordPort:</strong> Queries transactional ledgers, database audit trails, and balances.
                  </div>
                </div>
              </div>

              {/* Right: Write Ports & Audit */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-teal-400 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5" /> Pluggable Write Ports & Audit Ledger
                </h4>
                <div className="space-y-2 text-xs">
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-850">
                    <strong className="text-slate-200">JiraPort:</strong> Formats and files verified Jira bug tickets with reproduction steps.
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-850">
                    <strong className="text-slate-200">KBGapPort:</strong> Flags documentation gaps or stale runbooks to engineering docs.
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-850">
                    <strong className="text-slate-200">AuditPort:</strong> Records every pipeline event into an immutable SHA-256 hash chain.
                  </div>
                  <div className="p-2.5 rounded bg-slate-950 border border-slate-850">
                    <strong className="text-slate-200">ClientReplyPort:</strong> Generates client-facing explanations and diagnostic inquiries.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Profile YAML */}
      {activeTab === 'profile' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="font-semibold text-sm text-slate-200 flex items-center gap-2">
                <FileCode className="w-4 h-4 text-teal-400" />
                Active Product Profile: profiles/transfers.yaml
              </h3>
              <p className="text-xs text-slate-400">
                Declarative profile defining service boundaries, error taxonomy, PII rules, and agent tool budgets
              </p>
            </div>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-teal-950 text-teal-300 border border-teal-500/30">
              profiles/transfers.yaml
            </span>
          </div>

          <pre className="bg-slate-950 p-4 rounded-lg border border-slate-850 text-xs font-mono text-slate-300 overflow-x-auto leading-relaxed max-h-[600px]">
            <code>{JSON.stringify(profile, null, 2)}</code>
          </pre>
        </div>
      )}

      {/* Tab 3: 10-Minute Onboarding */}
      {activeTab === 'onboarding' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
          <div>
            <h3 className="font-semibold text-base text-slate-200 mb-1">
              10-Minute Product Onboarding Guide
            </h3>
            <p className="text-xs text-slate-400">
              How to onboard a new microservice or product domain into TriagePilot in under 10 minutes.
            </p>
          </div>

          <div className="space-y-4 text-xs">
            {/* Step 1 */}
            <div className="p-4 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
              <span className="font-mono text-teal-400 font-bold">STEP 1: Create a Product Profile YAML</span>
              <p className="text-slate-300 leading-relaxed">
                Add a new YAML file to <code className="text-teal-300 bg-slate-900 px-1 py-0.5 rounded font-mono">profiles/my_service.yaml</code> defining:
              </p>
              <ul className="list-disc list-inside text-slate-400 space-y-1">
                <li><code className="text-slate-300 font-mono">product.name</code> and <code className="text-slate-300 font-mono">product.domain</code> (e.g. transfers, auth, payments)</li>
                <li><code className="text-slate-300 font-mono">taxonomy.classes</code> and <code className="text-slate-300 font-mono">taxonomy.severities</code></li>
                <li><code className="text-slate-300 font-mono">budgets.max_tool_calls</code> (default 12)</li>
              </ul>
            </div>

            {/* Step 2 */}
            <div className="p-4 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
              <span className="font-mono text-teal-400 font-bold">STEP 2: Connect Observability Read Adapters</span>
              <p className="text-slate-300 leading-relaxed">
                Implement the 5 read interfaces in <code className="text-teal-300 bg-slate-900 px-1 py-0.5 rounded font-mono">engine/ports/base.py</code>:
              </p>
              <ul className="list-disc list-inside text-slate-400 space-y-1">
                <li><code className="text-slate-300 font-mono">GitPort</code>: Point to your GitHub/GitLab repository URI or token.</li>
                <li><code className="text-slate-300 font-mono">LogPort</code>: Connect Datadog, Google Cloud Logging, or Elasticsearch.</li>
                <li><code className="text-slate-300 font-mono">DocPort</code>: Connect Confluence or Notion runbook exports.</li>
              </ul>
            </div>

            {/* Step 3 */}
            <div className="p-4 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
              <span className="font-mono text-teal-400 font-bold">STEP 3: Configure Human-in-the-Loop Webhook</span>
              <p className="text-slate-300 leading-relaxed">
                Connect the Maker-Checker approval endpoint <code className="text-teal-300 bg-slate-900 px-1 py-0.5 rounded font-mono">POST /api/investigations/{'{id}'}/decision</code> to your Slack/Teams SRE on-call channel or Jira bot.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
