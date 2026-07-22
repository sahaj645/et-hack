"use client";

import { useEffect, useMemo, useState } from "react";
import { riskColorSmooth } from "@/lib/theme";

interface CopilotAnswer {
  cause: string[];
  recommendation: string[];
  sop_procedure_id: string;
  sop_procedure_title: string;
  sop_steps: string[];
  sop_source: string;
  estimated_risk_reduction_pct: number;
  peak_risk: number;
  confidence: number;
}

interface CopilotEntry {
  event_id: string;
  question: string;
  answer: CopilotAnswer;
}

interface CopilotProps {
  activeEventId?: string | null;
  eventTitles?: Record<string, string>;
}

export default function Copilot({ activeEventId, eventTitles = {} }: CopilotProps) {
  const [cache, setCache] = useState<CopilotEntry[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/data/copilot_cache.json")
      .then((r) => r.json())
      .then((data: CopilotEntry[]) => setCache(data))
      .catch((e) => setError(String(e)));
  }, []);

  // Follow the Live tab's active incident when one is playing, without
  // fighting a manual selection once the user has made one.
  useEffect(() => {
    if (activeEventId) setSelectedId(activeEventId);
  }, [activeEventId]);

  const selected = useMemo(
    () => cache?.find((c) => c.event_id === selectedId) ?? cache?.[0] ?? null,
    [cache, selectedId]
  );

  if (error) return <div className="p-4 text-sm text-red-400">Failed to load copilot cache: {error}</div>;
  if (!cache) return <div className="p-4 font-mono-readout text-sm text-slate-500">Loading copilot…</div>;

  return (
    <div className="rounded-lg border border-[#232a38] bg-[#10141c] p-3">
      <div className="mb-2 font-mono-readout text-[10px] uppercase tracking-widest text-slate-500">
        Operations Copilot
      </div>

      <div className="mb-3 flex flex-wrap gap-1.5">
        {cache.map((entry) => (
          <button
            key={entry.event_id}
            onClick={() => setSelectedId(entry.event_id)}
            className={`rounded-md border px-2.5 py-1 font-mono-readout text-[11px] transition ${
              selected?.event_id === entry.event_id
                ? "border-[#2dd4bf]/50 bg-[#2dd4bf]/10 text-[#2dd4bf]"
                : "border-[#232a38] text-slate-400 hover:text-slate-200"
            }`}
          >
            {eventTitles[entry.event_id] ?? entry.question}
          </button>
        ))}
      </div>

      {selected && (
        <div className="flex flex-col gap-3">
          <div className="font-mono-readout text-sm font-semibold text-slate-200">{selected.question}</div>

          <div>
            <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">Cause</div>
            <ul className="list-inside list-disc space-y-0.5 text-[13px] text-slate-300">
              {selected.answer.cause.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </div>

          <div>
            <div className="mb-1 text-[10px] uppercase tracking-widest text-slate-500">Recommendation</div>
            <ul className="list-inside list-disc space-y-0.5 text-[13px] text-slate-300">
              {selected.answer.recommendation.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>

          <div>
            <div className="mb-1 flex items-baseline justify-between">
              <span className="text-[10px] uppercase tracking-widest text-slate-500">
                SOP — {selected.answer.sop_procedure_id}: {selected.answer.sop_procedure_title}
              </span>
            </div>
            <div className="mb-1 text-[10px] italic text-slate-600">{selected.answer.sop_source}</div>
            <ol className="list-inside list-decimal space-y-0.5 text-[13px] text-slate-300">
              {selected.answer.sop_steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </div>

          <div className="flex items-center justify-between rounded-md border border-[#232a38] bg-[#161b26] px-3 py-2">
            <span className="font-mono-readout text-[11px] text-slate-400">Estimated risk reduction</span>
            <span
              className="font-mono-readout text-lg font-bold"
              style={{ color: riskColorSmooth(100 - selected.answer.estimated_risk_reduction_pct) }}
            >
              {selected.answer.estimated_risk_reduction_pct.toFixed(0)}%
            </span>
          </div>

          <a
            href={`/reports/${selected.event_id}.pdf`}
            download
            className="rounded-md border border-[#2dd4bf]/40 bg-[#2dd4bf]/10 px-3 py-1.5 text-center font-mono-readout text-xs font-semibold text-[#2dd4bf] transition hover:bg-[#2dd4bf]/20"
          >
            GENERATE REPORT (PDF)
          </a>
        </div>
      )}
    </div>
  );
}
