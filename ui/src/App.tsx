import React, { useState } from 'react';
import { CockpitScreen } from './screens/CockpitScreen';
import { EvalScreen } from './screens/EvalScreen';
import { ArchitectureScreen } from './screens/ArchitectureScreen';
import { AuditDrawer } from './components/AuditDrawer';
import { 
  Compass, 
  BarChart3, 
  Workflow, 
  ShieldCheck, 
  Activity, 
  Cloud, 
  Lock 
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<'cockpit' | 'eval' | 'architecture'>('cockpit');
  const [isAuditDrawerOpen, setIsAuditDrawerOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-black">
      {/* Top Enterprise Header */}
      <header className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-slate-800 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-teal-500 to-teal-700 text-slate-950 shadow-lg shadow-teal-500/20">
              <Compass className="w-6 h-6 stroke-[2.2]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black text-lg tracking-tight bg-gradient-to-r from-teal-300 via-teal-100 to-white bg-clip-text text-transparent">
                  TriagePilot
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-teal-950 text-teal-300 border border-teal-500/30">
                  v1.0 • AI Builder Cup
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Autonomous Initial Analyst & Evidentiary Bridge
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center bg-slate-900/80 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
            <button
              onClick={() => setActiveTab('cockpit')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition-all ${
                activeTab === 'cockpit'
                  ? 'bg-teal-600 text-white shadow-md shadow-teal-950'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Triage Cockpit</span>
            </button>

            <button
              onClick={() => setActiveTab('eval')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition-all ${
                activeTab === 'eval'
                  ? 'bg-teal-600 text-white shadow-md shadow-teal-950'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Ablation & Evals</span>
            </button>

            <button
              onClick={() => setActiveTab('architecture')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition-all ${
                activeTab === 'architecture'
                  ? 'bg-teal-600 text-white shadow-md shadow-teal-950'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Workflow className="w-3.5 h-3.5" />
              <span>Architecture & Profile</span>
            </button>
          </nav>

          {/* Right Action: Audit Drawer & Cloud Run Badge */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setIsAuditDrawerOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-850 text-slate-200 text-xs font-medium border border-teal-500/30 shadow-sm transition-all hover:border-teal-500/60"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
              <span className="hidden md:inline">Verify</span> SHA-256 Ledger
            </button>

            <div className="hidden lg:flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-400">
              <Cloud className="w-3.5 h-3.5 text-sky-400" />
              <span>Cloud Run Ready</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'cockpit' && <CockpitScreen />}
        {activeTab === 'eval' && <EvalScreen />}
        {activeTab === 'architecture' && <ArchitectureScreen />}
      </main>

      {/* Cryptographic Ledger Drawer */}
      <AuditDrawer
        isOpen={isAuditDrawerOpen}
        onClose={() => setIsAuditDrawerOpen(false)}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>TriagePilot © 2026 Google Cloud AI Builder Cup • Team Submission</span>
          <span className="flex items-center gap-1.5 font-mono text-[11px]">
            <Lock className="w-3 h-3 text-teal-500" /> All conclusions deterministically verified against AST & logs
          </span>
        </div>
      </footer>
    </div>
  );
}
