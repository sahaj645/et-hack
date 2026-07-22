"use client";

import { useEffect, useState } from "react";
import type { useDemoPlayer } from "@/lib/demo";
import Timeline from "./Timeline";
import WhatIf from "./WhatIf";
import ImpactBoard from "./ImpactBoard";

interface CopilotEntry {
  event_id: string;
  question: string;
  answer: {
    cause: string[];
    sop_procedure_id: string;
    sop_procedure_title: string;
    estimated_risk_reduction_pct: number;
  };
}

interface DemoHighlight {
  event_id: string;
  hero_detect_idx: number;
  hero_detect_time: string;
  reference_idx: number;
  reference_time_estimated: string | null;
  lead_time_minutes: number;
  methodology: string;
}

export default function DemoTab({ player }: { player: ReturnType<typeof useDemoPlayer> }) {
  const [copilotCache, setCopilotCache] = useState<CopilotEntry[] | null>(null);
  const [demoHighlight, setDemoHighlight] = useState<DemoHighlight | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/data/copilot_cache.json").then((r) => r.json()),
      fetch("/data/demo_highlight.json").then((r) => r.json()),
    ])
      .then(([cache, highlight]) => {
        setCopilotCache(cache);
        setDemoHighlight(highlight);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (player.error || error) {
    return <div className="p-8 text-red-400">Failed to load demo data: {player.error ?? error}</div>;
  }
  if (!player.ready || !player.scenario || !player.riskTimeline || !player.kg || !copilotCache || !demoHighlight) {
    return <div className="p-8 font-mono-readout text-slate-500">Loading demo…</div>;
  }

  return (
    <div className="flex flex-col gap-6">
      <Timeline
        scenario={player.scenario}
        riskTimeline={player.riskTimeline}
        kg={player.kg}
        copilotCache={copilotCache}
        demoHighlight={demoHighlight}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <WhatIf />
        <div className="flex flex-col justify-center gap-1 rounded-lg border border-[#232a38] bg-[#10141c] p-4 text-[12px] text-slate-500">
          <div className="font-mono-readout text-[10px] uppercase tracking-widest text-slate-400">
            About the movie above
          </div>
          <p>
            Every scene is a real index into the exported demo scenario, played back with curated pacing — the
            underlying risk score, contributors, knowledge-graph path, SOP recommendation, and lead time are the
            same numbers shown on the Live, Knowledge, and Metrics tabs. The final "projected alarm" beat is
            explicitly labeled as an extrapolation, not a value present in the recorded data.
          </p>
        </div>
      </div>

      <ImpactBoard />
    </div>
  );
}
