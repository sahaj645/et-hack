"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { riskColorSmooth } from "@/lib/theme";

const API_BASE = "http://localhost:8000";

interface ScoreResult {
  index: number;
  risk: number;
  confidence: number;
  contributors: Record<string, number>;
}

interface FallbackGridEntry {
  ventilation_pct: number;
  delay_maintenance: boolean;
  result: ScoreResult;
}

interface FallbackData {
  index: number;
  baseline: ScoreResult;
  grid: FallbackGridEntry[];
}

type ApiStatus = "checking" | "live" | "offline";

export default function WhatIf() {
  const [ventilation, setVentilation] = useState(100);
  const [delayMaintenance, setDelayMaintenance] = useState(false);
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [baseline, setBaseline] = useState<ScoreResult | null>(null);
  const [status, setStatus] = useState<ApiStatus>("checking");
  const [fallback, setFallback] = useState<FallbackData | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetch("/data/whatif_fallback.json")
      .then((r) => r.json())
      .then((data: FallbackData) => {
        setFallback(data);
        setBaseline(data.baseline);
        setResult(data.baseline);
      })
      .catch(() => {});
  }, []);

  function lookupFallback(vent: number, delay: boolean): ScoreResult | null {
    if (!fallback) return null;
    // nearest ventilation step in the precomputed grid
    let best: FallbackGridEntry | null = null;
    let bestDist = Infinity;
    for (const entry of fallback.grid) {
      if (entry.delay_maintenance !== delay) continue;
      const dist = Math.abs(entry.ventilation_pct - vent);
      if (dist < bestDist) {
        bestDist = dist;
        best = entry;
      }
    }
    return best?.result ?? fallback.baseline;
  }

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      if (!fallback) return;
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 1500);
        const res = await fetch(`${API_BASE}/whatif`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            index: fallback.index,
            ventilation_pct: ventilation,
            delay_maintenance: delayMaintenance,
          }),
          signal: controller.signal,
        });
        clearTimeout(timeout);
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        const data = await res.json();
        setResult(data.adjusted);
        setBaseline(data.baseline);
        setStatus("live");
      } catch {
        setResult(lookupFallback(ventilation, delayMaintenance));
        setStatus("offline");
      }
    }, 250);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ventilation, delayMaintenance, fallback]);

  const delta = useMemo(() => {
    if (!result || !baseline) return 0;
    return result.risk - baseline.risk;
  }, [result, baseline]);

  return (
    <div className="rounded-lg border border-[#232a38] bg-[#10141c] p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="font-mono-readout text-[10px] uppercase tracking-widest text-slate-500">
          Live What-If
        </div>
        <div className="flex items-center gap-1.5 font-mono-readout text-[10px]">
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{
              background: status === "live" ? "#10b981" : status === "offline" ? "#f59e0b" : "#475569",
            }}
          />
          <span className="text-slate-500">
            {status === "live" ? "API LIVE" : status === "offline" ? "OFFLINE — precomputed fallback" : "checking…"}
          </span>
        </div>
      </div>

      <div className="mb-4 space-y-3">
        <div>
          <div className="mb-1 flex justify-between font-mono-readout text-[11px] text-slate-400">
            <span>Ventilation</span>
            <span>{ventilation}%</span>
          </div>
          <input
            type="range"
            min={70}
            max={100}
            step={5}
            value={ventilation}
            onChange={(e) => setVentilation(Number(e.target.value))}
            className="h-1.5 w-full accent-[#2dd4bf]"
          />
        </div>

        <label className="flex items-center gap-2 font-mono-readout text-[11px] text-slate-400">
          <input
            type="checkbox"
            checked={delayMaintenance}
            onChange={(e) => setDelayMaintenance(e.target.checked)}
            className="accent-[#2dd4bf]"
          />
          Delay maintenance further
        </label>
      </div>

      {result && baseline && (
        <div className="flex items-center gap-4">
          <div>
            <div className="font-mono-readout text-[10px] uppercase tracking-widest text-slate-500">
              Compound Risk
            </div>
            <div className="font-mono-readout text-3xl font-bold" style={{ color: riskColorSmooth(result.risk) }}>
              {result.risk.toFixed(0)}
            </div>
          </div>
          <div className="font-mono-readout text-sm">
            <span className="text-slate-500">vs baseline {baseline.risk.toFixed(0)}: </span>
            <span style={{ color: delta > 0.5 ? "#ef4444" : delta < -0.5 ? "#10b981" : "#64748b" }}>
              {delta > 0 ? "+" : ""}
              {delta.toFixed(1)}
            </span>
          </div>
        </div>
      )}

      <p className="mt-3 text-[11px] leading-relaxed text-slate-600">
        Recomputes a real counterfactual (ventilation applied to wind speed, maintenance delay applied to
        compressor health) through the same fusion model used everywhere else in this app. Falls back to a
        precomputed grid — built with the identical function — if the API is unreachable.
      </p>
    </div>
  );
}
