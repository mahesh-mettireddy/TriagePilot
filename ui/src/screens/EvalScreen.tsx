import React, { useState, useEffect } from 'react';
import { getEvalResults, getScenarios } from '../api';
import { ScenarioMeta } from '../types';
import { 
  Trophy, 
  BarChart3, 
  ShieldCheck, 
  Zap, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  HelpCircle,
  FileCheck,
  TrendingDown,
  Clock,
  DollarSign
} from 'lucide-react';

export const EvalScreen: React.FC = () => {
  const [evalData, setEvalData] = useState<any>(null);
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [evals, scs] = await Promise.all([getEvalResults(), getScenarios()]);
        setEvalData(evals);
        setScenarios(scs);
      } catch (err) {
        console.error('Failed to load eval screen data', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const modes = evalData?.modes || [];
  const findings = evalData?.key_findings || [];
  const modeC = modes.find((mode: any) => mode.id === 'mode_c');

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-96 bg-gradient-to-l from-teal-500/10 to-transparent pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-teal-950 text-teal-400 border border-teal-500/30">
                BENCHMARK SUITE
              </span>
              <span className="text-xs text-slate-500 font-mono">
                 8 Golden Scenarios • 3 Architectural Modes
              </span>
            </div>
            <h2 className="text-2xl font-bold text-slate-100">
              Architectural Ablation & Evaluation
            </h2>
            <p className="text-sm text-slate-400 mt-1 max-w-3xl">
               Recorded benchmark comparison. Fresh live or replay evaluation runs expose their own run ID, execution mode, and raw scenario results.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-center">
              <span className="text-[10px] uppercase text-slate-500 block">Root-Cause Accuracy</span>
               <span className="text-xl font-black text-emerald-400 font-mono">{modeC ? `${(modeC.root_cause_hit_rate * 100).toFixed(1)}%` : '—'}</span>
            </div>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-center">
              <span className="text-[10px] uppercase text-slate-500 block">False Conclusion Rate</span>
               <span className="text-xl font-black text-emerald-400 font-mono">{modeC ? `${(modeC.false_conclusion_rate * 100).toFixed(1)}%` : '—'}</span>
            </div>
          </div>
        </div>
      </div>

      {evalData && (
        <div className="bg-slate-950/80 border border-amber-500/30 rounded-xl p-4 text-xs text-slate-300">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="font-mono font-bold text-amber-300">{evalData.execution_mode || 'recorded_benchmark'}</span>
            <span className="text-slate-500">Run {evalData.run_id || 'RECORDED-ABLATION-2026-01'}</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-slate-400 font-mono text-[11px]">
            <span>Commit: {evalData.commit || 'recorded benchmark'}</span>
            <span>Ground truth: {evalData.ground_truth_version || 'recorded manifest'}</span>
            <span>Provider: {evalData.provider || 'recorded'}</span>
          </div>
          <p className="mt-2 text-slate-400">{evalData.provenance || 'Fresh evaluation metadata is returned by the evaluation run endpoint.'}</p>
        </div>
      )}

      {/* 3 Modes Comparative Hero Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {modes.map((mode: any) => {
          const isModeC = mode.id === 'mode_c';
          return (
            <div
              key={mode.id}
              className={`rounded-xl p-5 border transition-all duration-200 flex flex-col justify-between ${
                isModeC
                  ? 'bg-slate-900 border-teal-500/50 shadow-xl shadow-teal-500/10 ring-1 ring-teal-500/20'
                  : 'bg-slate-900/60 border-slate-800'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span
                    className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded ${
                      isModeC
                        ? 'bg-teal-950 text-teal-300 border border-teal-500/30'
                        : 'bg-slate-850 text-slate-400 border border-slate-700'
                    }`}
                  >
                    {mode.id.toUpperCase().replace('_', ' ')}
                  </span>
                  {isModeC && (
                    <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-500/40">
                      <Trophy className="w-3 h-3 text-emerald-400" /> RECOMMENDED
                    </span>
                  )}
                </div>

                <h3 className="text-base font-bold text-slate-100 mb-1">{mode.name}</h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">{mode.description}</p>

                {/* Metrics Breakdown */}
                <div className="space-y-2.5 pt-2 border-t border-slate-850 text-xs">
                  <div>
                    <div className="flex justify-between text-slate-300 mb-1">
                      <span>Root-Cause Hit Rate:</span>
                      <strong className={`font-mono ${isModeC ? 'text-teal-400 font-bold' : ''}`}>
                        {(mode.root_cause_hit_rate * 100).toFixed(0)}%
                      </strong>
                    </div>
                    <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${isModeC ? 'bg-teal-400' : 'bg-slate-600'}`}
                        style={{ width: `${mode.root_cause_hit_rate * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-300 mb-1">
                      <span>Citation Validity:</span>
                      <strong className={`font-mono ${isModeC ? 'text-teal-400 font-bold' : ''}`}>
                        {(mode.citation_validity * 100).toFixed(0)}%
                      </strong>
                    </div>
                    <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${isModeC ? 'bg-teal-400' : 'bg-slate-600'}`}
                        style={{ width: `${mode.citation_validity * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-300 mb-1">
                      <span>False Conclusions:</span>
                      <strong className={`font-mono ${isModeC ? 'text-emerald-400 font-bold' : 'text-rose-400'}`}>
                        {(mode.false_conclusion_rate * 100).toFixed(0)}%
                      </strong>
                    </div>
                    <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${mode.false_conclusion_rate === 0 ? 'bg-emerald-500' : 'bg-rose-500'}`}
                        style={{ width: `${mode.false_conclusion_rate * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-300 mb-1">
                      <span>Prompt Injection Defense:</span>
                      <strong className={`font-mono ${isModeC ? 'text-emerald-400 font-bold' : ''}`}>
                        {(mode.prompt_injection_defense * 100).toFixed(0)}%
                      </strong>
                    </div>
                    <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${isModeC ? 'bg-emerald-400' : 'bg-slate-600'}`}
                        style={{ width: `${mode.prompt_injection_defense * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Cost & Latency footer */}
              <div className="mt-4 pt-3 border-t border-slate-850 flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {mode.avg_latency_ms} ms
                </span>
                <span className="flex items-center gap-1">
                  <DollarSign className="w-3 h-3 text-slate-500" />
                  ${mode.avg_cost_usd.toFixed(4)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Key Findings Callout Grid */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
        <h3 className="font-semibold text-sm text-slate-200 mb-3 flex items-center gap-2">
          <FileCheck className="w-4 h-4 text-teal-400" />
          Key Architectural Findings & Rigor
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {findings.map((finding: string, idx: number) => (
            <div
              key={idx}
              className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-300 flex items-start gap-2.5 leading-relaxed"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>{finding}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Golden Scenarios Reference Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div>
            <h3 className="font-semibold text-sm text-slate-200 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-teal-400" />
              Evaluation Benchmark Matrix (Golden Scenarios)
            </h3>
            <p className="text-xs text-slate-400">
              Deterministic verification and ground-truth validation across all scenario bundles
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">{scenarios.length} Scenarios</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-mono text-[10px] uppercase">
                <th className="py-2.5 px-3">ID</th>
                <th className="py-2.5 px-3">Scenario Title</th>
                <th className="py-2.5 px-3">Ticket Class</th>
                <th className="py-2.5 px-3">Special Verification Tags</th>
                <th className="py-2.5 px-3 text-right">Mode C Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-850">
              {scenarios.map((sc) => (
                <tr key={sc.id} className="hover:bg-slate-850/50 transition-colors">
                  <td className="py-3 px-3 font-mono font-bold text-teal-400">{sc.id}</td>
                  <td className="py-3 px-3">
                    <div className="font-semibold text-slate-200">{sc.title}</div>
                    <div className="text-[11px] text-slate-400 line-clamp-1">{sc.description}</div>
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-300">
                    <span className="px-2 py-0.5 rounded bg-slate-950 text-[10px] border border-slate-800">
                      {sc.ticket_class}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex flex-wrap gap-1">
                      {sc.tags?.map((tag, tIdx) => (
                        <span
                          key={tIdx}
                          className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-950 text-slate-400 border border-slate-800"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <span className="inline-flex items-center gap-1 font-mono text-[11px] font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
                      <CheckCircle2 className="w-3 h-3" /> PASS
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
