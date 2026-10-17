import React, { useState, useEffect } from 'react';
import { CockpitScreen } from './screens/CockpitScreen';
import { EvalScreen } from './screens/EvalScreen';
import { ArchitectureScreen } from './screens/ArchitectureScreen';
import { AuditDrawer } from './components/AuditDrawer';
import { getReadiness, verifyAudit } from './api';
import { ReadinessStatus } from './types';
import {
  Compass,
  BarChart3,
  Workflow,
  ShieldCheck,
  Activity,
  Database,
  Cpu,
  Lock,
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<'cockpit' | 'eval' | 'architecture'>('cockpit');
  const [isAuditDrawerOpen, setIsAuditDrawerOpen] = useState(false);
  const [readiness, setReadiness] = useState<ReadinessStatus | null>(null);
  const [auditCount, setAuditCount] = useState<number | null>(null);

  useEffect(() => {
    async function fetchSystemStatus() {
      try {
        const [r, a] = await Promise.all([
          getReadiness().catch(() => null),
          verifyAudit().catch(() => null),
        ]);
        if (r) setReadiness(r);
        if (a && typeof a.entries_checked === 'number') setAuditCount(a.entries_checked);
      } catch {
        // Non-blocking status poll
      }
    }
    fetchSystemStatus();
  }, [isAuditDrawerOpen]);

  const aiLabel =
    readiness?.ai_mode === 'vertex_ai'
      ? 'Vertex AI • Gemini 2.5'
      : readiness?.ai_mode === 'api_key'
        ? 'Gemini API • 2.5'
        : 'Deterministic Engine';

  const storeLabel =
    readiness?.persistence === 'firestore' ? 'Firestore Native' : 'Verified Store';

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-slate-950">
      {/* Top Enterprise Command Bar */}
      <header className="sticky top-0 z-40 bg-[#070b14]/95 backdrop-blur-xl border-b border-slate-800/80 shadow-lg shadow-black/40">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Logo & Brand (Project Trademark Only) */}
          <div className="flex items-center gap-3.5">
            <div className="p-2 rounded-xl bg-gradient-to-br from-teal-400 via-teal-500 to-emerald-600 text-slate-950 shadow-lg shadow-teal-500/20 ring-1 ring-teal-300/40">
              <Compass className="w-6 h-6 stroke-[2.3]" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <span className="font-black text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-teal-300 bg-clip-text text-transparent">
                  TriagePilot<span className="text-teal-400 font-bold text-xs align-top ml-0.5">™</span>
                </span>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md bg-teal-950/90 text-teal-300 border border-teal-500/30">
                  v1.0 ENTERPRISE
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block tracking-tight">
                Autonomous Incident Analyst &amp; Verifiable Evidentiary Bridge
              </p>
            </div>
          </div>

          {/* Primary Navigation Workspace Switcher */}
          <nav className="flex items-center bg-slate-900/90 p-1 rounded-xl border border-slate-800/90 text-xs font-semibold shadow-inner">
            <button
              onClick={() => setActiveTab('cockpit')}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg transition-all ${
                activeTab === 'cockpit'
                  ? 'bg-gradient-to-r from-teal-600 to-teal-500 text-white shadow-md shadow-teal-950/80'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Triage Command Center</span>
            </button>

            <button
              onClick={() => setActiveTab('eval')}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg transition-all ${
                activeTab === 'eval'
                  ? 'bg-gradient-to-r from-teal-600 to-teal-500 text-white shadow-md shadow-teal-950/80'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Quality &amp; Ablation</span>
            </button>

            <button
              onClick={() => setActiveTab('architecture')}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg transition-all ${
                activeTab === 'architecture'
                  ? 'bg-gradient-to-r from-teal-600 to-teal-500 text-white shadow-md shadow-teal-950/80'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Workflow className="w-3.5 h-3.5" />
              <span>Architecture &amp; Integration</span>
            </button>
          </nav>

          {/* Right Live Telemetry & Cryptographic Ledger Trigger */}
          <div className="flex items-center gap-2.5">
            <div className="hidden xl:flex items-center gap-2 text-[11px] font-mono px-2.5 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <Cpu className="w-3.5 h-3.5 text-teal-400" />
              <span>{aiLabel}</span>
            </div>

            <div className="hidden lg:flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300">
              <Database className="w-3.5 h-3.5 text-sky-400" />
              <span>{storeLabel}</span>
            </div>

            <div className="hidden 2xl:flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1.5 rounded-lg bg-slate-900/90 border border-teal-500/30 text-teal-300" title="Deterministic Parallel Specialist Runner with Google ADK Agent Topology & A2A v0.2 JSON-RPC">
              <span>ADK Topology • A2A v0.2</span>
            </div>

            <button
              onClick={() => setIsAuditDrawerOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-100 text-xs font-semibold border border-teal-500/40 shadow-sm transition-all hover:border-teal-400"
            >
              <ShieldCheck className="w-4 h-4 text-teal-400" />
              <span>SHA-256 Ledger</span>
              {auditCount !== null && (
                <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-teal-950 text-teal-300 border border-teal-500/30">
                  {auditCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Fluid Enterprise Workspace */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-5">
        {activeTab === 'cockpit' && <CockpitScreen />}
        {activeTab === 'eval' && <EvalScreen />}
        {activeTab === 'architecture' && <ArchitectureScreen />}
      </main>

      {/* Cryptographic Ledger Drawer */}
      <AuditDrawer
        isOpen={isAuditDrawerOpen}
        onClose={() => setIsAuditDrawerOpen(false)}
      />

      {/* Clean Product Trademark Footer */}
      <footer className="border-t border-slate-900/90 bg-[#050811] py-3.5 text-xs text-slate-500">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-300">TriagePilot™</span>
            <span>•</span>
            <span>Autonomous Incident Analyst &amp; Evidentiary Bridge</span>
          </div>
          <span className="flex items-center gap-1.5 font-mono text-[11px] text-slate-400">
            <Lock className="w-3.5 h-3.5 text-teal-400" />
            Every claim deterministically verified against pinned Git commits, logs, runbooks &amp; ledger state
          </span>
        </div>
      </footer>
    </div>
  );
}
