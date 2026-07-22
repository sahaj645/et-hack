"use client";

import type { useDemoPlayer } from "@/lib/demo";
import KnowledgeGraph from "./KnowledgeGraph";

export default function KnowledgeTab({ player }: { player: ReturnType<typeof useDemoPlayer> }) {
  if (player.error) {
    return <div className="p-8 text-red-400">Failed to load graph data: {player.error}</div>;
  }
  if (!player.ready || !player.kg) {
    return <div className="p-8 font-mono-readout text-slate-500">Loading knowledge graph…</div>;
  }

  const { kg, activeEvent, scenario } = player;

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-[#232a38] bg-[#10141c] px-4 py-3 text-sm text-slate-400">
        Playback position on the <span className="text-slate-200">Live</span> tab drives which hazardous
        path lights up here — scrub into any of the three incident windows to see it highlight.
      </div>
      <KnowledgeGraph kg={kg} activeEventId={activeEvent?.id ?? null} />
      <div className="rounded-lg border border-[#232a38] bg-[#10141c] p-3">
        <div className="mb-2 font-mono-readout text-[10px] uppercase tracking-widest text-slate-500">
          All Incident Paths
        </div>
        <div className="flex flex-col gap-2">
          {kg.paths.map((p) => {
            const event = scenario?.events.find((e) => e.id === p.event_id);
            return (
              <div key={p.event_id} className="rounded-md border border-[#232a38] bg-[#161b26] p-2.5">
                <div className="font-mono-readout text-xs font-semibold text-slate-300">
                  {event?.title ?? p.event_id}
                </div>
                <div className="mt-1 font-mono-readout text-xs text-slate-500">{p.sentence}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
