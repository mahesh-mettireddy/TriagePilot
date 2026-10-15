import React from 'react';
import { AgentRoutingPlan } from '../types';
import { 
  GitBranch, 
  BookOpen, 
  FileText, 
  Code, 
  Database, 
  ShieldAlert, 
  ShieldCheck, 
  Cpu, 
  ZapOff 
} from 'lucide-react';

interface RouterBarProps {
  routingPlan?: AgentRoutingPlan;
  activeAgents?: string[];
}

const ALL_AGENTS: Array<{
  id: 'HistoryAgent' | 'KnowledgeAgent' | 'LogsAgent' | 'CodeAgent' | 'RecordAgent';
  name: string;
  desc: string;
  icon: React.ComponentType<{ className?: string }>;
}> = [
  { id: 'HistoryAgent', name: 'History Agent', desc: 'Resolved tickets & past incidents', icon: GitBranch },
  { id: 'KnowledgeAgent', name: 'Knowledge Agent', desc: 'Runbooks, architecture docs & specs', icon: BookOpen },
  { id: 'LogsAgent', name: 'Logs Agent', desc: 'Trace events, metrics & exceptions', icon: FileText },
  { id: 'CodeAgent', name: 'Code Agent', desc: 'Git commits, blame, AST & diffs', icon: Code },
  { id: 'RecordAgent', name: 'Record Agent', desc: 'System of record & ledgers', icon: Database },
];

export const RouterBar: React.FC<RouterBarProps> = ({ routingPlan, activeAgents = [] }) => {
  if (!routingPlan) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center text-slate-500 text-xs">
        Dynamic router initializing...
      </div>
    );
  }

  const activeSet = new Set(activeAgents.length > 0 ? activeAgents : routingPlan.active_agents || []);
  const skippedMap = routingPlan.skipped_agents || {};

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-xl backdrop-blur-sm">
      {/* Top Banner: Classification, Severity, Injection Defense */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-slate-400">Classification:</span>
          <span className="font-mono text-xs font-bold px-2.5 py-0.5 rounded bg-teal-950/80 text-teal-300 border border-teal-500/30">
            {routingPlan.ticket_class}
          </span>
          <span
            className={`font-mono text-xs font-bold px-2 py-0.5 rounded border ${
              routingPlan.severity === 'P1'
                ? 'bg-rose-950/90 text-rose-300 border-rose-500/50 animate-pulse'
                : routingPlan.severity === 'P2'
                ? 'bg-amber-950/90 text-amber-300 border-amber-500/50'
                : 'bg-slate-800 text-slate-300 border-slate-700'
            }`}
          >
            {routingPlan.severity}
          </span>
        </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Cpu className="w-3.5 h-3.5 text-teal-400" />
              <span>
                Budget: <strong className="text-slate-200">{routingPlan.tool_calls_used || 0}</strong> used /{' '}
                <strong className="text-slate-200">{routingPlan.max_tool_calls || 12}</strong> max
                <span className="text-teal-300"> ({Math.max(0, (routingPlan.max_tool_calls || 12) - (routingPlan.tool_calls_used || 0))} remaining)</span>
              </span>
            </div>

          {routingPlan.injection_detected ? (
            <div className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-rose-950 text-rose-300 border border-rose-500/50 animate-pulse">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>Prompt Injection Deflected</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-[11px] font-medium text-emerald-400/90 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              <span>Anti-Jailbreak Guard Active</span>
            </div>
          )}
        </div>
      </div>

      {/* 5 Specialists Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5">
        {ALL_AGENTS.map((agent) => {
          const isActive = activeSet.has(agent.id);
          const skipReason = skippedMap[agent.id];
          const Icon = agent.icon;

          return (
            <div
              key={agent.id}
              className={`relative rounded-lg p-3 transition-all duration-200 border flex flex-col justify-between ${
                isActive
                  ? 'bg-slate-850 border-teal-500/40 shadow-sm shadow-teal-500/10'
                  : 'bg-slate-950/60 border-slate-800 opacity-60'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className={`p-1.5 rounded-md ${isActive ? 'bg-teal-950/80 text-teal-300' : 'bg-slate-900 text-slate-500'}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  {isActive ? (
                    <span className="flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping inline-block" />
                      ACTIVE
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[9px] font-semibold px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                      <ZapOff className="w-2.5 h-2.5 text-amber-500" />
                      PRUNED
                    </span>
                  )}
                </div>

                <div className="font-semibold text-xs text-slate-200 mb-0.5">
                  {agent.name}
                </div>
                <div className="text-[10px] text-slate-400 leading-tight">
                  {agent.desc}
                </div>
              </div>

              {!isActive && skipReason && (
                <div className="mt-2 pt-1.5 border-t border-slate-800/80">
                  <span className="text-[9px] font-mono text-amber-400/90 block truncate" title={skipReason}>
                    ⚡ {skipReason}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
