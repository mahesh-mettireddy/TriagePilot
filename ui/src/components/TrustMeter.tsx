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

  const currentPolicy = policyActionBadges[trust.policy_action] || {
    label: `POLICY: ${trust.policy_action}`,
    class: 'bg-slate-800 text-slate-300 border-slate-700',
  };

  const comps = trust.components || {
    c_ver: 0,
    c_div: 0,
    c_spec: 0,
    c_time: 0,
    p_contra: 0,
    p_unver: 0,
  };

  return (
    <div className={`rounded-xl border ${bandConfig.border} ${bandConfig.bg} p-4 transition-all duration-300 shadow-lg backdrop-blur-sm`}>
      {/* Top Header */}
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${bandConfig.color}`} />
          <span className="font-semibold text-sm text-slate-200">
            Evidentiary Trust Score
          </span>
          <span className={`text-[11px] font-bold px-2 py-0.5 rounded border ${bandConfig.border} ${bandConfig.color} bg-slate-900/80`}>
            {trust.band} BAND
          </span>
        </div>

        <div className="flex items-center gap-2">
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

      {/* Expand formula toggle */}
      <div className="mt-3 pt-2 border-t border-slate-800/80">
        <button
          onClick={() => setShowBreakdown(!showBreakdown)}
          className="flex items-center justify-between w-full text-[11px] font-medium text-slate-400 hover:text-slate-200 transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-teal-400" />
            Inspect Trust Formula Breakdown: T = c_ver + c_div + c_spec + c_time - p_contra - p_unver
          </span>
          {showBreakdown ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {showBreakdown && (
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs font-mono bg-slate-950/90 p-3 rounded-lg border border-slate-800">
            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">c_ver (max 0.35)</div>
              <div className="text-teal-400 font-bold mt-0.5">+{comps.c_ver.toFixed(2)}</div>
              <div className="text-[9px] text-slate-400">Verified Fraction</div>
            </div>

            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">c_div (max 0.25)</div>
              <div className="text-teal-400 font-bold mt-0.5">+{comps.c_div.toFixed(2)}</div>
              <div className="text-[9px] text-slate-400">Source Diversity</div>
            </div>

            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">c_spec (max 0.20)</div>
              <div className="text-teal-400 font-bold mt-0.5">+{comps.c_spec.toFixed(2)}</div>
              <div className="text-[9px] text-slate-400">Specialist Coverage</div>
            </div>

            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">c_time (max 0.20)</div>
              <div className="text-teal-400 font-bold mt-0.5">+{comps.c_time.toFixed(2)}</div>
              <div className="text-[9px] text-slate-400">Time Correlation</div>
            </div>

            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">p_contra (penalty)</div>
              <div className="text-rose-400 font-bold mt-0.5">-{comps.p_contra.toFixed(2)}</div>
              <div className="text-[9px] text-slate-400">Contradictions</div>
            </div>

            <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
              <div className="text-[10px] text-slate-500">p_unver (penalty)</div>
              <div className="text-rose-400 font-bold mt-0.5">-{comps.p_unver.toFixed(2)}</div>
              <div className="text-[9px] text-slate-400">Dropped/Unverified</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
