"use client";

import type { useDemoPlayer } from "@/lib/demo";
import { riskColorSmooth } from "@/lib/theme";
import Gauge from "./Gauge";
import Traces from "./Traces";
import Twin from "./Twin";
import Heatmap from "./Heatmap";
import ContributorBars from "./ContributorBars";
import Confidence from "./Confidence";

function formatClock(ts: string | undefined): string {
  if (!ts) return "--:--";
  return ts.slice(11, 16);
}

export default function LiveTab({ player }: { player: ReturnType<typeof useDemoPlayer> }) {
  if (player.error) {
    return <div className="p-8 text-red-400">Failed to load scenario data: {player.error}</div>;
  }
  if (!player.ready || !player.scenario || !player.riskTimeline || !player.row || !player.riskPoint) {
    return <div className="p-8 font-mono-readout text-slate-500">Loading scenario…</div>;
  }

  const { scenario, index, row, riskPoint, activeEvent, workerPositions } = player;
  const activeAssetIds = activeEvent?.asset_ids ?? [];
  const progressPct = (index / (player.totalPoints - 1)) * 100;

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[#232a38] bg-[#10141c] px-4 py-3">
        <button
          onClick={player.playing ? player.pause : player.play}
          className="rounded-md border border-[#2dd4bf]/40 bg-[#2dd4bf]/10 px-4 py-1.5 font-mono-readout text-sm font-semibold text-[#2dd4bf] transition hover:bg-[#2dd4bf]/20"
        >
          {player.playing ? "PAUSE" : "PLAY"}
        </button>
        <button
          onClick={player.reset}
          className="rounded-md border border-[#232a38] px-3 py-1.5 font-mono-readout text-sm text-slate-400 transition hover:text-slate-200"
        >
          RESET
        </button>
        <div className="flex items-center gap-1">
          {[1, 2, 4].map((s) => (
            <button
              key={s}
              onClick={() => player.setSpeed(s)}
              className={`rounded px-2 py-1 font-mono-readout text-xs ${
                player.speed === s ? "bg-[#232a38] text-slate-100" : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {s}x
            </button>
          ))}
        </div>

        <input
          type="range"
          min={0}
          max={player.totalPoints - 1}
          value={index}
          onChange={(e) => player.setIndex(Number(e.target.value))}
          className="mx-2 h-1.5 flex-1 accent-[#2dd4bf]"
        />

        <div className="font-mono-readout text-sm text-slate-300">
          {formatClock(row.timestamp)} <span className="text-slate-600">·</span>{" "}
          <span className="text-slate-500">
            {index}/{player.totalPoints - 1}
          </span>
        </div>
      </div>

      {activeEvent && (
        <div
          className="rounded-lg border px-4 py-2.5 font-mono-readout text-sm"
          style={{ borderColor: riskColorSmooth(riskPoint.risk), background: `${riskColorSmooth(riskPoint.risk)}14` }}
        >
          <span className="font-bold" style={{ color: riskColorSmooth(riskPoint.risk) }}>
            ACTIVE INCIDENT
          </span>{" "}
          <span className="text-slate-200">{activeEvent.title}</span>
          <span className="ml-2 text-slate-500">({activeEvent.zone_id})</span>
        </div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr_1fr]">
        <div className="flex flex-col items-center gap-4 rounded-lg border border-[#232a38] bg-[#10141c] p-4">
          <Gauge risk={riskPoint.risk} />
          <Confidence confidence={riskPoint.confidence} />
          <ContributorBars contributors={riskPoint.contributors} risk={riskPoint.risk} />
        </div>

        <Twin
          assets={scenario.plant.assets}
          zones={scenario.plant.zones}
          workers={workerPositions}
          contributors={riskPoint.contributors}
          overallRisk={riskPoint.risk}
          activeEventAssetIds={activeAssetIds}
          row={row}
        />

        <Heatmap
          zones={scenario.plant.zones}
          workers={workerPositions}
          overallRisk={riskPoint.risk}
          activeEvent={activeEvent}
        />
      </div>

      <div className="rounded-lg border border-[#232a38] bg-[#10141c] p-3">
        <div className="mb-1 font-mono-readout text-[10px] uppercase tracking-widest text-slate-500">
          Live Sensor Traces
        </div>
        <Traces timeline={scenario.timeline} channelSpecs={scenario.meta.channel_specs} index={index} />
      </div>

      <div className="h-1 w-full overflow-hidden rounded-full bg-[#1a202c]">
        <div className="h-full bg-[#232a38]" style={{ width: `${progressPct}%` }} />
      </div>
    </div>
  );
}
