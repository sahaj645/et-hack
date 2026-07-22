"use client";

import { Line, LineChart, ReferenceLine, ResponsiveContainer, YAxis } from "recharts";
import type { ChannelSpec, TimelineRow } from "@/lib/demo";

interface TracesProps {
  timeline: TimelineRow[];
  channelSpecs: Record<string, ChannelSpec>;
  index: number;
  windowSize?: number;
}

const CHANNELS: { key: keyof TimelineRow; label: string; color: string }[] = [
  { key: "pressure_bar", label: "Pressure", color: "#f87171" },
  { key: "gas_ppm", label: "Gas", color: "#c084fc" },
  { key: "temp_tank_c", label: "Tank Temp", color: "#fb923c" },
  { key: "temp_compressor_c", label: "Compressor Temp", color: "#2dd4bf" },
  { key: "vibration_mms", label: "Vibration", color: "#60a5fa" },
];

export default function Traces({ timeline, channelSpecs, index, windowSize = 120 }: TracesProps) {
  const start = Math.max(0, index - windowSize);
  const data = timeline.slice(start, index + 1).map((row, i) => ({ ...row, i: start + i }));

  return (
    <div className="flex flex-col gap-2">
      {CHANNELS.map((ch) => {
        const spec = channelSpecs[ch.key as string];
        const latest = data.length ? (data[data.length - 1][ch.key] as number) : null;
        return (
          <div key={ch.key} className="relative">
            <div className="mb-0.5 flex items-baseline justify-between font-mono-readout text-[10px] text-slate-400">
              <span>
                {ch.label} <span className="text-slate-600">({spec?.unit})</span>
              </span>
              <span className="text-slate-300">{latest !== null ? latest.toFixed(2) : "--"}</span>
            </div>
            <ResponsiveContainer width="100%" height={44}>
              <LineChart data={data} margin={{ top: 2, right: 4, bottom: 0, left: 4 }}>
                <YAxis domain={[0, spec ? spec.alarm_high * 1.1 : "auto"]} hide />
                {spec && <ReferenceLine y={spec.alarm_high} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.5} />}
                <Line type="monotone" dataKey={ch.key as string} stroke={ch.color} dot={false} strokeWidth={1.5} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        );
      })}
    </div>
  );
}
