import React, { useState } from 'react';
import { TrustSummary } from '../types';
import { Shield, ShieldAlert, ShieldCheck, Info, ChevronDown, ChevronUp } from 'lucide-react';

interface TrustMeterProps {
  trust?: TrustSummary;
}

export const TrustMeter: React.FC<TrustMeterProps> = ({ trust }) => {
  const [showBreakdown, setShowBreakdown] = useState(false);

  if (!trust) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center text-slate-500 text-xs">
        No trust assessment available yet
      </div>
    );
  }

  const scorePct = Math.round(trust.score * 100);

  // Band styles
  const bandConfig = {
    HIGH: {
      color: 'text-emerald-400',
      bg: 'bg-emerald-950/40',
      border: 'border-emerald-500/30',
      bar: 'bg-gradient-to-r from-teal-500 to-emerald-400',
      icon: ShieldCheck,
      desc: 'High confidence. Deterministically grounded across multi-source evidence.',
    },
    MEDIUM: {
      color: 'text-amber-400',
      bg: 'bg-amber-950/40',
      border: 'border-amber-500/30',
      bar: 'bg-gradient-to-r from-amber-500 to-yellow-400',
      icon: Shield,
      desc: 'Medium confidence. Single specialist or minor contradiction detected.',
    },
    LOW: {
      color: 'text-rose-400',
      bg: 'bg-rose-950/40',
      border: 'border-rose-500/30',
      bar: 'bg-gradient-to-r from-rose-600 to-rose-400',
      icon: ShieldAlert,
      desc: 'Low confidence / Abstention policy triggered. Manual engineering triage required.',
    },
  }[trust.band] || {
    color: 'text-slate-400',
    bg: 'bg-slate-800/40',
    border: 'border-slate-700',
    bar: 'bg-slate-500',
    icon: Shield,
    desc: 'Unclassified',
  };

  const Icon = bandConfig.icon;

  const policyActionBadges: Record<string, { label: string; class: string }> = {
    CONCLUDE: { label: 'POLICY: CONCLUDE', class: 'bg-emerald-900/60 text-emerald-300 border-emerald-500/40' },
    CONCLUDE_WITH_CAVEAT: { label: 'POLICY: CONCLUDE WITH CAVEAT', class: 'bg-amber-900/60 text-amber-300 border-amber-500/40' },
    ABSTAIN: { label: 'POLICY: ABSTAIN (LOW TRUST)', class: 'bg-rose-900/60 text-rose-300 border-rose-500/40' },
    ESCALATE_SECURITY: { label: 'POLICY: ESCALATE SECURITY', class: 'bg-purple-900/60 text-purple-300 border-purple-500/40' },
  };

  const gateOutcomeBadges: Record<string, { label: string; class: string }> = {
    REPRODUCED_IN_FIXTURE: {
      label: 'GATE: REPRODUCED IN FIXTURE',
      class: 'bg-emerald-950/80 text-emerald-300 border-emerald-400/40',
    },
    SUPPORTED_HYPOTHESIS: {
      label: 'GATE: SUPPORTED HYPOTHESIS',
      class: 'bg-teal-950/80 text-teal-300 border-teal-400/40',
    },
    NEED_EVIDENCE: {
      label: 'GATE: NEED EVIDENCE',
      class: 'bg-amber-950/80 text-amber-300 border-amber-400/40',
    },
    BLOCKED: {
      label: 'GATE: BLOCKED',
      class: 'bg-rose-950/80 text-rose-300 border-rose-400/40',
    },
  };

  const currentPolicy = policyActionBadges[trust.policy_action] || {
    label: `POLICY: ${trust.policy_action}`,
    class: 'bg-slate-800 text-slate-300 border-slate-700',
  };
  const currentGate = trust.gate_outcome ? gateOutcomeBadges[trust.gate_outcome] : undefined;

  const comps = trust.components || {
    c_ver: 0,
    c_div: 0,
    c_spec: 0,
    c_time: 0,
    p_contra: 0,
    p_unver: 0,
    unique_provenance_count: 0,
  };

  return (
    <div className={`rounded-xl border ${bandConfig.border} ${bandConfig.bg} p-4 transition-all duration-300 shadow-lg backdrop-blur-sm`}>
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${bandConfig.color}`} />
          <span className="font-semibold text-sm text-slate-200">
            Evidentiary Trust Gate
          </span>
          <span className={`text-[11px] font-bold px-2 py-0.5 rounded border ${bandConfig.border} ${bandConfig.color} bg-slate-900/80`}>
            {trust.band} BAND
          </span>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {currentGate && (
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${currentGate.class}`}>
              {currentGate.label}
            </span>
          )}
          <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${currentPolicy.class}`}>
            {currentPolicy.label}
          </span>
          <span className={`text-2xl font-mono font-black ${bandConfig.color}`}>
            {trust.score.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2.5 bg-slate-950/80 rounded-full overflow-hidden border border-slate-800 my-2">
        <div
          className={`h-full ${bandConfig.bar} transition-all duration-700 ease-out`}
          style={{ width: `${Math.min(100, Math.max(5, scorePct))}%` }}
        />
      </div>

      {/* Rationale text */}
      <p className="text-xs text-slate-300 mt-2 leading-relaxed">
        {trust.rationale || bandConfig.desc}
      </p>

      {/* Hard Conclusion Gate Reasons */}
      {trust.gate_reasons && trust.gate_reasons.length > 0 && (
        <div className="mt-2 pt-2 border-t border-slate-800/70 text-[11px] font-mono text-slate-300 space-y-0.5">
          {trust.gate_reasons.map((reason, idx) => (
            <div key={idx} className="flex items-start gap-1.5">
              <span className="text-teal-400">▸</span>
              <span>{reason}</span>
            </div>
          ))}
        </div>
      )}

      {/* Expand formula toggle */}
      <div className="mt-3 pt-2 border-t border-slate-800/80">
        <button
          onClick={() => setShowBreakdown(!showBreakdown)}
          className="flex items-center justify-between w-full text-[11px] font-medium text-slate-400 hover:text-slate-200 transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-teal-400" />
            Inspect Trust Formula: T = 0.40·c_ver + 0.25·c_div + 0.20·c_spec + 0.15·c_time − 0.30·p_contra − 0.20·p_unver
          </span>
          {showBreakdown ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {showBreakdown && (
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs font-mono bg-slate-950/90 p-3 rounded-lg border border-slate-800">
            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">c_ver (weight 0.40)</div>
              <div className="text-teal-400 font-bold mt-0.5">
                +{(0.40 * comps.c_ver).toFixed(2)}{' '}
                <span className="text-[10px] text-slate-400 font-normal">(raw {comps.c_ver.toFixed(2)})</span>
              </div>
              <div className="text-[9px] text-slate-400">
                Deduplicated ({comps.unique_provenance_count ?? 0} unique)
              </div>
            </div>

            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">c_div (weight 0.25)</div>
              <div className="text-teal-400 font-bold mt-0.5">
                +{(0.25 * comps.c_div).toFixed(2)}{' '}
                <span className="text-[10px] text-slate-400 font-normal">(raw {comps.c_div.toFixed(2)})</span>
              </div>
              <div className="text-[9px] text-slate-400">Source Diversity</div>
            </div>

            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">c_spec (weight 0.20)</div>
              <div className="text-teal-400 font-bold mt-0.5">
                +{(0.20 * comps.c_spec).toFixed(2)}{' '}
                <span className="text-[10px] text-slate-400 font-normal">(raw {comps.c_spec.toFixed(2)})</span>
              </div>
              <div className="text-[9px] text-slate-400">Specialist Coverage</div>
            </div>

            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">c_time (weight 0.15)</div>
              <div className="text-teal-400 font-bold mt-0.5">
                +{(0.15 * comps.c_time).toFixed(2)}{' '}
                <span className="text-[10px] text-slate-400 font-normal">(raw {comps.c_time.toFixed(2)})</span>
              </div>
              <div className="text-[9px] text-slate-400">Time Correlation</div>
            </div>

            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">p_contra (weight −0.30)</div>
              <div className="text-rose-400 font-bold mt-0.5">
                −{(0.30 * comps.p_contra).toFixed(2)}{' '}
                <span className="text-[10px] text-slate-400 font-normal">(raw {comps.p_contra.toFixed(2)})</span>
              </div>
              <div className="text-[9px] text-slate-400">Contradictions</div>
            </div>

            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">p_unver (weight −0.20)</div>
              <div className="text-rose-400 font-bold mt-0.5">
                −{(0.20 * comps.p_unver).toFixed(2)}{' '}
                <span className="text-[10px] text-slate-400 font-normal">(raw {comps.p_unver.toFixed(2)})</span>
              </div>
              <div className="text-[9px] text-slate-400">Dropped/Unverified</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
