"use client";

import { motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import type { KGData, RiskTimelineData, ScenarioData } from "@/lib/demo";
import { riskColorSmooth } from "@/lib/theme";
import Gauge from "./Gauge";
import Confidence from "./Confidence";
import ContributorBars from "./ContributorBars";
import Twin from "./Twin";
import Heatmap from "./Heatmap";
import KnowledgeGraph from "./KnowledgeGraph";

interface CopilotAnswer {
  cause: string[];
  sop_procedure_id: string;
  sop_procedure_title: string;
  estimated_risk_reduction_pct: number;
}
interface CopilotEntry {
  event_id: string;
  question: string;
  answer: CopilotAnswer;
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

interface TimelineProps {
  scenario: ScenarioData;
  riskTimeline: RiskTimelineData;
  kg: KGData;
  copilotCache: CopilotEntry[];
  demoHighlight: DemoHighlight;
}

// Every idx below is a real index into the exported demo scenario (seed
// 42); every caption states only what the data at that idx (or, for the
// final two beats, demo_highlight.json's disclosed projection) actually
// shows. Wall-clock beat timing is curated for pacing — the underlying
// facts are not.
const EVENT_ID = "evt-gas-leak-01";
const BEATS = [
  { t: 0, idx: 30, caption: "02:00 · Process Unit 7 — normal night operation" },
  { t: 7, idx: 55, caption: "Gas concentration near TANK-01 begins a slow climb" },
  { t: 13, idx: 62, caption: "Wind drops to near-calm — dispersion stalling" },
  { t: 19, idx: 63, caption: "ALERT — PlantPulse crosses its threshold. No single sensor has alarmed." },
  { t: 27, idx: 84, caption: "03:08 · Night-shift supervisor W-05 enters Tank Farm without an active permit" },
  { t: 35, idx: 100, caption: "Risk climbs to 88 — Tank Farm turns RESTRICTED" },
  { t: 44, idx: 100, caption: "kg" },
  { t: 53, idx: 100, caption: "copilot" },
  { t: 61, idx: 100, caption: "Incident report generated" },
  { t: 68, idx: 118, caption: "04:00 · incident window closes in the simulation" },
  { t: 76, idx: 118, caption: "projection" },
  { t: 84, idx: 118, caption: "leadtime" },
] as const;

const TOTAL_SECONDS = 90;
const ALERT_AT = 19;
const WORKER_AT = 27;
const HEATMAP_AT = 35;
const KG_AT = 44;
const COPILOT_AT = 53;
const REPORT_AT = 61;
const PROJECTION_AT = 76;
const LEAD_TIME_AT = 84;

function formatClock(ts: string | undefined): string {
  if (!ts) return "--:--";
  return ts.slice(11, 16);
}

function currentBeat(elapsed: number) {
  let active = BEATS[0];
  for (const beat of BEATS) {
    if (beat.t <= elapsed) active = beat;
  }
  return active;
}

export default function Timeline({ scenario, riskTimeline, kg, copilotCache, demoHighlight }: TimelineProps) {
  const [elapsed, setElapsed] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [runCount, setRunCount] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startRef = useRef<number>(0);

  useEffect(() => {
    if (!playing) return;
    // Wall-clock based (Date.now()), not requestAnimationFrame: rAF is
    // throttled or fully paused by the browser when the tab isn't
    // actively focused/rendering, which would silently stall the movie —
    // a real risk for a live demo where the presenter might alt-tab.
    // setInterval ticks recompute elapsed from the start timestamp each
    // time, so a delayed or throttled tick still catches up correctly
    // instead of drifting.
    startRef.current = Date.now() - elapsed * 1000;
    intervalRef.current = setInterval(() => {
      const next = (Date.now() - startRef.current) / 1000;
      if (next >= TOTAL_SECONDS) {
        setElapsed(TOTAL_SECONDS);
        setPlaying(false);
        if (intervalRef.current) clearInterval(intervalRef.current);
        return;
      }
      setElapsed(next);
    }, 200);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing]);

  function play() {
    setElapsed(0);
    setRunCount((c) => c + 1);
    setPlaying(true);
  }

  const beat = currentBeat(elapsed);
  const idx = beat.idx;
  const row = scenario.timeline[idx];
  const riskPoint = riskTimeline.points[idx];
  const event = scenario.events.find((e) => e.id === EVENT_ID)!;
  const kgPath = kg.paths.find((p) => p.event_id === EVENT_ID);
  const copilotEntry = copilotCache.find((c) => c.event_id === EVENT_ID);

  const showAlert = elapsed >= ALERT_AT;
  const showWorker = elapsed >= WORKER_AT;
  const showHeatmap = elapsed >= HEATMAP_AT;
  const showKg = elapsed >= KG_AT;
  const showCopilot = elapsed >= COPILOT_AT;
  const showReport = elapsed >= REPORT_AT;
  const showProjection = elapsed >= PROJECTION_AT;
  const showLeadTime = elapsed >= LEAD_TIME_AT;

  const workerPositions = useMemo(
    () =>
      scenario.plant.workers.map((w) => {
        const override = scenario.plant.worker_zone_overrides.find(
          (o) => o.worker_id === w.id && idx >= o.start_idx && idx <= o.end_idx
        );
        return { ...w, zone_id: override ? override.zone_id : w.home_zone_id, intruding: !!override && showWorker };
      }),
    [scenario, idx, showWorker]
  );

  const activeAssetIds = elapsed >= HEATMAP_AT ? event.asset_ids : [];
  const activeEventForHeatmap = showHeatmap ? event : null;

  const caption =
    beat.caption === "kg"
      ? kgPath?.sentence ?? ""
      : beat.caption === "copilot"
      ? `Copilot — cause identified → ${copilotEntry?.answer.sop_procedure_id ?? "SOP"} → estimated ${copilotEntry?.answer.estimated_risk_reduction_pct ?? "--"}% risk reduction`
      : beat.caption === "projection"
      ? `Projected: an unaddressed trend would not have crossed a conventional single-sensor alarm until ${formatClock(demoHighlight.reference_time_estimated ?? undefined)}`
      : beat.caption === "leadtime"
      ? "LEAD TIME"
      : beat.caption;

  const progressPct = (Math.min(elapsed, TOTAL_SECONDS) / TOTAL_SECONDS) * 100;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between rounded-lg border border-[#232a38] bg-[#10141c] px-4 py-3">
        <button
          onClick={play}
          disabled={playing}
          className="rounded-md border border-[#2dd4bf]/40 bg-[#2dd4bf]/10 px-5 py-2 font-mono-readout text-sm font-semibold text-[#2dd4bf] transition hover:bg-[#2dd4bf]/20 disabled:opacity-40"
        >
          {playing ? "PLAYING…" : runCount > 0 ? "REPLAY MOVIE" : "PLAY MOVIE"}
        </button>
        <div className="font-mono-readout text-xs text-slate-500">
          {elapsed.toFixed(0)}s / {TOTAL_SECONDS}s{runCount > 0 ? ` · run #${runCount}` : ""}
        </div>
      </div>

      <div className="h-1 w-full overflow-hidden rounded-full bg-[#1a202c]">
        <motion.div className="h-full bg-[#2dd4bf]" animate={{ width: `${progressPct}%` }} transition={{ duration: 0.1 }} />
      </div>

      <div className="min-h-[64px] rounded-lg border border-[#232a38] bg-[#10141c] px-5 py-4">
        <motion.div
          key={caption}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="font-mono-readout text-lg text-slate-100"
        >
          {showAlert && !showKg && !showCopilot && beat.caption !== "leadtime" && beat.caption !== "projection" && (
            <span className="mr-2 font-bold" style={{ color: riskColorSmooth(riskPoint.risk) }}>
              ●
            </span>
          )}
          {caption}
        </motion.div>
      </div>

      {!showLeadTime && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[260px_1fr_1fr]">
          <div className="flex flex-col items-center gap-3 rounded-lg border border-[#232a38] bg-[#10141c] p-4">
            <Gauge risk={riskPoint.risk} />
            <Confidence confidence={riskPoint.confidence} />
            {showHeatmap && <ContributorBars contributors={riskPoint.contributors} risk={riskPoint.risk} />}
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
            activeEvent={activeEventForHeatmap}
          />
        </div>
      )}

      {showKg && !showLeadTime && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
          <KnowledgeGraph kg={kg} activeEventId={EVENT_ID} />
        </motion.div>
      )}

      {showCopilot && copilotEntry && !showLeadTime && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="rounded-lg border border-[#2dd4bf]/30 bg-[#2dd4bf]/5 p-4"
        >
          <div className="mb-2 font-mono-readout text-[10px] uppercase tracking-widest text-[#2dd4bf]">
            Operations Copilot
          </div>
          <ul className="mb-2 list-inside list-disc space-y-0.5 text-[13px] text-slate-300">
            {copilotEntry.answer.cause.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
          <div className="font-mono-readout text-sm text-slate-200">
            SOP {copilotEntry.answer.sop_procedure_id}: {copilotEntry.answer.sop_procedure_title} — estimated{" "}
            <span className="font-bold text-[#2dd4bf]">{copilotEntry.answer.estimated_risk_reduction_pct}%</span> risk
            reduction
          </div>
          {showReport && (
            <div className="mt-3 flex items-center gap-2 font-mono-readout text-xs text-slate-400">
              <span className="rounded border border-[#232a38] px-2 py-1">📄 {EVENT_ID}.pdf generated</span>
            </div>
          )}
        </motion.div>
      )}

      {showProjection && !showLeadTime && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3 font-mono-readout text-sm text-amber-200"
        >
          {caption.startsWith("Projected") ? caption : demoHighlight.methodology}
        </motion.div>
      )}

      {showLeadTime && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex flex-col items-center justify-center rounded-lg border border-[#2dd4bf]/40 bg-[#2dd4bf]/5 py-14"
        >
          <div className="font-mono-readout text-xs uppercase tracking-[0.3em] text-slate-400">Lead Time</div>
          <LeadTimeCounter minutes={demoHighlight.lead_time_minutes} active={showLeadTime} />
          <div className="mt-3 max-w-lg text-center text-sm text-slate-400">
            PlantPulse alerted at {formatClock(demoHighlight.hero_detect_time)} — a conventional single-sensor
            system, per the same extrapolation methodology used in engine/metrics/run.py, would not have fired
            until an estimated {formatClock(demoHighlight.reference_time_estimated ?? undefined)}.
          </div>
        </motion.div>
      )}
    </div>
  );
}

function LeadTimeCounter({ minutes, active }: { minutes: number; active: boolean }) {
  const [displayed, setDisplayed] = useState(0);

  useEffect(() => {
    if (!active) {
      setDisplayed(0);
      return;
    }
    // setInterval + wall-clock elapsed, not requestAnimationFrame — see
    // the main beat timer above for why: rAF is throttled/paused when
    // the tab isn't actively rendering, which would leave this counter
    // stuck at 0 instead of settling on the real value.
    const durationMs = 1400;
    const start = Date.now();
    const id = setInterval(() => {
      const t = Math.min(1, (Date.now() - start) / durationMs);
      setDisplayed(minutes * (1 - Math.pow(1 - t, 3)));
      if (t >= 1) clearInterval(id);
    }, 50);
    return () => clearInterval(id);
  }, [active, minutes]);

  const h = Math.floor(displayed / 60);
  const m = Math.floor(displayed % 60);
  const s = Math.floor((displayed * 60) % 60);

  return (
    <div className="font-mono-readout text-6xl font-bold text-[#2dd4bf]" style={{ textShadow: "0 0 24px rgba(45,212,191,0.4)" }}>
      {h > 0 ? `${h}h ` : ""}
      {m}m {s}s
    </div>
  );
}
