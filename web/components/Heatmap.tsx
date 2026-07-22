"use client";

import { motion } from "framer-motion";
import type { LiveWorker, PlantZone, ScenarioEvent } from "@/lib/demo";
import { riskColorSmooth } from "@/lib/theme";

interface HeatmapProps {
  zones: PlantZone[];
  workers: LiveWorker[];
  overallRisk: number;
  activeEvent: ScenarioEvent | null;
}

const VIEW_MIN_X = -4;
const VIEW_MIN_Y = -4;
const VIEW_W = 92;
const VIEW_H = 72;
const CAUTION_THRESHOLD = 65;

// The zone hosting the currently active compound incident (from the
// exported event's own zone_id — not inferred) carries the full fused
// risk score; other zones show a low ambient share of the same score, so
// nothing on this panel is ever a value that didn't come from the data.
function zoneRisk(zone: PlantZone, activeEvent: ScenarioEvent | null, overallRisk: number): number {
  if (activeEvent && activeEvent.zone_id === zone.id) return overallRisk;
  return overallRisk * 0.12;
}

export default function Heatmap({ zones, workers, overallRisk, activeEvent }: HeatmapProps) {
  const workersByZone: Record<string, LiveWorker[]> = {};
  for (const w of workers) {
    (workersByZone[w.zone_id] ??= []).push(w);
  }

  return (
    <div className="rounded-lg border border-[#232a38] bg-[#10141c] p-3">
      <svg viewBox={`${VIEW_MIN_X} ${VIEW_MIN_Y} ${VIEW_W} ${VIEW_H}`} className="h-auto w-full">
        {zones.map((z) => {
          const [x0, y0, x1, y1] = z.bounds;
          const risk = zoneRisk(z, activeEvent, overallRisk);
          const color = riskColorSmooth(risk);
          const restricted = risk >= CAUTION_THRESHOLD;
          return (
            <g key={z.id}>
              <motion.rect
                x={x0}
                y={y0}
                width={x1 - x0}
                height={y1 - y0}
                initial={false}
                animate={{ fill: color, fillOpacity: 0.12 + (risk / 100) * 0.4 }}
                transition={{ duration: 0.4 }}
                stroke={color}
                strokeWidth={restricted ? 0.5 : 0.25}
                rx={1.5}
              />
              {restricted && (
                <rect
                  x={x0}
                  y={y0}
                  width={x1 - x0}
                  height={y1 - y0}
                  fill="none"
                  stroke={color}
                  strokeWidth={0.6}
                  strokeDasharray="1.5 1"
                  rx={1.5}
                  className="animate-pulse-glow"
                />
              )}
              <text x={x0 + 1.2} y={y0 + 3} fontSize={2.4} fill="#cbd5e1" fontFamily="ui-monospace, monospace">
                {z.name.toUpperCase()}
              </text>
              {restricted && (
                <text
                  x={x1 - 1.2}
                  y={y0 + 3}
                  fontSize={1.9}
                  fill={color}
                  textAnchor="end"
                  fontFamily="ui-monospace, monospace"
                  fontWeight={700}
                >
                  RESTRICTED
                </text>
              )}
              <text x={x0 + 1.2} y={y1 - 1.4} fontSize={2} fill="#64748b" fontFamily="ui-monospace, monospace">
                risk {risk.toFixed(0)}
              </text>
            </g>
          );
        })}

        {Object.entries(workersByZone).map(([zoneId, group]) =>
          group.map((w, i) => {
            const zone = zones.find((z) => z.id === zoneId);
            if (!zone) return null;
            const [x0, y0, x1, y1] = zone.bounds;
            const col = i % 4;
            const rowIdx = Math.floor(i / 4);
            const cx = Math.min(x1 - 2, x0 + 3 + col * 2.4);
            const cy = Math.min(y1 - 2, y0 + 8 + rowIdx * 2.4);
            const color = w.intruding ? "#fca5a5" : "#e2e8f0";
            return (
              <motion.circle
                key={w.id}
                initial={false}
                animate={{ cx, cy }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                r={1}
                fill={color}
                stroke="#0a0e14"
                strokeWidth={0.3}
                style={w.intruding ? { filter: "drop-shadow(0 0 2px #ef4444)" } : undefined}
              >
                <title>
                  {w.name}
                  {w.intruding ? " — unpermitted presence" : ""}
                </title>
              </motion.circle>
            );
          })
        )}
      </svg>
    </div>
  );
}
