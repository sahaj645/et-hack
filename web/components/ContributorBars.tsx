"use client";

import { motion } from "framer-motion";
import { riskColorSmooth } from "@/lib/theme";

interface ContributorBarsProps {
  contributors: Record<string, number>;
  risk: number;
}

const CONTRIBUTOR_LABEL: Record<string, string> = {
  sensor: "Sensor Deviation",
  equipment: "Equipment Degradation",
  permit: "Permit Status",
  maintenance: "Maintenance Exposure",
  worker: "Worker Exposure",
  weather: "Weather / Dispersion",
};

/** Ranked contributor breakdown from risk_agent.contributor_breakdown() —
 * every value here is read straight from risk_timeline.json, nothing is
 * computed or guessed in the UI.
 */
export default function ContributorBars({ contributors, risk }: ContributorBarsProps) {
  const ranked = Object.entries(contributors)
    .sort((a, b) => b[1] - a[1])
    .filter(([, pct]) => pct > 0);
  const color = riskColorSmooth(risk);

  return (
    <div className="w-full">
      <div className="mb-1.5 font-mono-readout text-[10px] uppercase tracking-widest text-slate-500">
        Ranked Contributors
      </div>
      <div className="flex flex-col gap-1.5">
        {ranked.length === 0 && <div className="text-xs text-slate-600">No active signals</div>}
        {ranked.map(([agent, pct]) => (
          <div key={agent} className="flex items-center gap-2">
            <span className="w-36 shrink-0 font-mono-readout text-[11px] text-slate-400">
              {CONTRIBUTOR_LABEL[agent] ?? agent}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-[#1a202c]">
              <motion.div
                className="h-full rounded-full"
                style={{ background: color }}
                initial={false}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.35, ease: "easeOut" }}
              />
            </div>
            <span className="w-11 text-right font-mono-readout text-[11px] text-slate-500">
              +{pct.toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
