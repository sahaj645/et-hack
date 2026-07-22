"use client";

import { useState } from "react";
import type { LiveWorker, PlantAsset, PlantZone, TimelineRow } from "@/lib/demo";
import { riskColorSmooth } from "@/lib/theme";

interface TwinProps {
  assets: PlantAsset[];
  zones: PlantZone[];
  workers: LiveWorker[];
  contributors: Record<string, number>;
  overallRisk: number;
  activeEventAssetIds: string[];
  row: TimelineRow;
}

// Which agents' contribution share is relevant to each asset's own glow —
// derived from the same archetype design as the engine (gas leak/overpressure
// touch the tank farm assets, bearing failure touches the compressor).
const ASSET_CONTRIBUTORS: Record<string, string[]> = {
  "TANK-01": ["sensor", "permit", "maintenance", "weather"],
  "PIPE-01": ["sensor", "weather"],
  "VALVE-01": ["maintenance"],
  "COMP-01": ["equipment", "sensor"],
  "BOIL-01": [],
};

function assetLiveReadout(asset: PlantAsset, row: TimelineRow): { label: string; value: string }[] {
  switch (asset.id) {
    case "TANK-01":
      return [
        { label: "Temp", value: `${row.temp_tank_c.toFixed(1)} °C` },
        { label: "Pressure", value: `${row.pressure_bar.toFixed(1)} bar` },
        { label: "Health", value: `${(asset.health_score * 100).toFixed(0)}%` },
      ];
    case "PIPE-01":
      return [
        { label: "Temp", value: `${row.temp_tank_c.toFixed(1)} °C` },
        { label: "Pressure", value: `${row.pressure_bar.toFixed(1)} bar` },
      ];
    case "VALVE-01":
      return [
        { label: "Relief capacity", value: `${row.relief_capacity_pct.toFixed(0)}%` },
        { label: "Maintenance", value: asset.maintenance_state },
      ];
    case "COMP-01":
      return [
        { label: "Temp", value: `${row.temp_compressor_c.toFixed(1)} °C` },
        { label: "Vibration", value: `${row.vibration_mms.toFixed(2)} mm/s` },
        { label: "Health", value: `${(row.compressor_health * 100).toFixed(0)}%` },
      ];
    default:
      return [
        { label: "Temp", value: `${asset.temperature_c.toFixed(1)} °C` },
        { label: "Health", value: `${(asset.health_score * 100).toFixed(0)}%` },
      ];
  }
}

const VIEW_MIN_X = -4;
const VIEW_MIN_Y = -4;
const VIEW_W = 92;
const VIEW_H = 72;

export default function Twin({ assets, zones, workers, contributors, overallRisk, activeEventAssetIds, row }: TwinProps) {
  const [hovered, setHovered] = useState<PlantAsset | null>(null);

  function assetRisk(asset: PlantAsset): number {
    const keys = ASSET_CONTRIBUTORS[asset.id] ?? [];
    const share = keys.reduce((sum, k) => sum + (contributors[k] ?? 0), 0);
    return (overallRisk * share) / 100;
  }

  const workersByZone: Record<string, LiveWorker[]> = {};
  for (const w of workers) {
    (workersByZone[w.zone_id] ??= []).push(w);
  }

  return (
    <div className="relative rounded-lg border border-[#232a38] bg-[#10141c] p-3">
      <svg viewBox={`${VIEW_MIN_X} ${VIEW_MIN_Y} ${VIEW_W} ${VIEW_H}`} className="h-auto w-full">
        {zones.map((z) => {
          const [x0, y0, x1, y1] = z.bounds;
          return (
            <g key={z.id}>
              <rect x={x0} y={y0} width={x1 - x0} height={y1 - y0} fill="none" stroke="#232a38" strokeDasharray="1.2 1.2" rx={1.5} />
              <text x={x0 + 1.2} y={y0 + 3} fontSize={2.4} fill="#475569" fontFamily="ui-monospace, monospace">
                {z.name.toUpperCase()}
              </text>
            </g>
          );
        })}

        {assets.map((a) => {
          const r = assetRisk(a);
          const amplified = Math.min(100, r * 3.2);
          const glowColor = r > 2 ? riskColorSmooth(amplified) : "#334155";
          const isActive = activeEventAssetIds.includes(a.id);
          return (
            <g
              key={a.id}
              transform={`translate(${a.location.x}, ${a.location.y})`}
              onMouseEnter={() => setHovered(a)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: "pointer" }}
            >
              <title>{a.name}</title>
              {isActive && (
                <circle r={5.4} fill={glowColor} opacity={0.28} className="animate-pulse-glow" />
              )}
              <circle r={3.4} fill={glowColor} opacity={isActive ? 0.95 : 0.55} style={isActive ? { filter: `drop-shadow(0 0 3px ${glowColor})` } : undefined} />
              <circle r={1.7} fill="#0a0e14" stroke={glowColor} strokeWidth={0.5} />
              <text y={5.8} fontSize={2.1} textAnchor="middle" fill="#94a3b8" fontFamily="ui-monospace, monospace">
                {a.id}
              </text>
            </g>
          );
        })}

        {Object.entries(workersByZone).map(([zoneId, group]) => {
          const zone = zones.find((z) => z.id === zoneId);
          if (!zone) return null;
          const [x0, y0, x1, y1] = zone.bounds;
          return group.map((w, i) => {
            const col = i % 4;
            const rowIdx = Math.floor(i / 4);
            const wx = x1 - 4 - col * 2.4;
            const wy = y1 - 4 - rowIdx * 2.4;
            const color = w.intruding ? "#ef4444" : "#38bdf8";
            return (
              <g key={w.id} transform={`translate(${Math.max(x0 + 2, wx)}, ${Math.max(y0 + 4, wy)})`}>
                <title>
                  {w.name} ({w.role}) {w.intruding ? "— unpermitted presence" : ""}
                </title>
                <circle r={0.9} fill={color} opacity={0.9} style={w.intruding ? { filter: `drop-shadow(0 0 3px ${color})` } : undefined} />
              </g>
            );
          });
        })}
      </svg>

      {hovered && (
        <div className="absolute right-3 top-3 w-52 rounded-md border border-[#232a38] bg-[#161b26]/95 p-2.5 font-mono-readout text-[11px] text-slate-300 shadow-lg backdrop-blur">
          <div className="mb-1.5 font-semibold text-slate-100">{hovered.name}</div>
          <div className="flex justify-between">
            <span className="text-slate-500">Status</span>
            <span>{hovered.status}</span>
          </div>
          {assetLiveReadout(hovered, row).map((r) => (
            <div key={r.label} className="flex justify-between">
              <span className="text-slate-500">{r.label}</span>
              <span>{r.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
