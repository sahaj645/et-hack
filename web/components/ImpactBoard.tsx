"use client";

import { useEffect, useState } from "react";
import { COLORS } from "@/lib/theme";

interface ImpactSummary {
  measured: {
    archetypes_validated: number;
    detection_rate_pct: number;
    median_lead_time_min: number;
    false_alarms_per_day_hero: number;
    false_alarms_per_day_baseline_b: number;
    unsafe_zone_entries_flagged: number;
    eval_seed_count: number;
  };
  assumptions: {
    recurrence_per_archetype_per_year: number;
    downtime_hours_per_incident: number;
    cost_per_incident_inr: number;
    basis: string;
  };
  derived: {
    incidents_per_year_assumed: number;
    near_misses_prevented_per_year: number;
    downtime_avoided_hours_per_year: number;
    cost_avoided_inr_per_year: number;
  };
  label: string;
}

function formatInr(n: number): string {
  return `₹${n.toLocaleString("en-IN")}`;
}

function SimLabel() {
  return (
    <span className="ml-1.5 rounded border border-[#3f4a5e] px-1 py-0.5 font-mono-readout text-[8px] font-semibold uppercase tracking-wide text-slate-500">
      Simulation output
    </span>
  );
}

function Card({ title, value, sub }: { title: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-[#232a38] bg-[#161b26] p-3">
      <div className="flex items-center font-mono-readout text-[10px] uppercase tracking-widest text-slate-500">
        {title}
        <SimLabel />
      </div>
      <div className="mt-1.5 font-mono-readout text-2xl font-bold text-slate-100">{value}</div>
      {sub && <div className="mt-0.5 text-[11px] text-slate-500">{sub}</div>}
    </div>
  );
}

export default function ImpactBoard() {
  const [data, setData] = useState<ImpactSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/data/impact_summary.json")
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="p-4 text-sm text-red-400">Failed to load impact summary: {error}</div>;
  if (!data) return <div className="p-4 font-mono-readout text-sm text-slate-500">Loading impact board…</div>;

  return (
    <div className="rounded-lg border border-[#232a38] bg-[#10141c] p-3">
      <div className="mb-1 font-mono-readout text-[10px] uppercase tracking-widest text-slate-500">
        Impact Board
      </div>
      <p className="mb-3 max-w-2xl text-[12px] leading-relaxed text-slate-500">{data.label}</p>

      <div className="mb-3 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        <Card title="Near-misses prevented / yr" value={`${data.derived.near_misses_prevented_per_year}`} sub={`${data.measured.archetypes_validated} archetypes x ${data.assumptions.recurrence_per_archetype_per_year}/yr assumed x ${data.measured.detection_rate_pct.toFixed(0)}% detected`} />
        <Card title="Downtime avoided / yr" value={`${data.derived.downtime_avoided_hours_per_year}h`} sub={`${data.assumptions.downtime_hours_per_incident}h assumed per incident`} />
        <Card title="Cost avoided / yr" value={formatInr(data.derived.cost_avoided_inr_per_year)} sub={`${formatInr(data.assumptions.cost_per_incident_inr)} assumed per incident`} />
        <Card
          title="Unsafe entries flagged"
          value={`${data.measured.unsafe_zone_entries_flagged}/${data.measured.eval_seed_count}`}
          sub="Measured, not assumed — evaluation seeds"
        />
      </div>

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
        <Card title="Detection rate" value={`${data.measured.detection_rate_pct.toFixed(0)}%`} sub="60 archetype instances, 20 seeds" />
        <Card title="Median lead time" value={`${data.measured.median_lead_time_min.toFixed(0)} min`} sub="over extrapolated conventional alarm" />
        <Card
          title="False alarms/day"
          value={`${data.measured.false_alarms_per_day_hero.toFixed(2)}`}
          sub={`vs ${data.measured.false_alarms_per_day_baseline_b.toFixed(2)} for rolling z-score baseline`}
        />
      </div>

      <div className="mt-3 rounded-md border border-[#232a38] bg-[#0d1017] p-2.5 text-[11px] leading-relaxed text-slate-500">
        No "lives saved" figure is shown here on purpose — a life-safety claim tied to a simulation would be
        dishonest regardless of labeling. Assumptions and their rationale are fully disclosed in{" "}
        <span className="font-mono-readout" style={{ color: COLORS.calm }}>
          data/cost_basis.md
        </span>
        .
      </div>
    </div>
  );
}
