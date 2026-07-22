"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// ---- Types mirroring the exported JSON (engine/export.py) ----

export interface TimelineRow {
  timestamp: string;
  pressure_bar: number;
  gas_ppm: number;
  temp_tank_c: number;
  temp_compressor_c: number;
  vibration_mms: number;
  wind_speed_kmh: number;
  ambient_temp_c: number;
  humidity_pct: number;
  wind_direction_deg: number;
  compressor_health: number;
  relief_capacity_pct: number;
  workers_in_tank_farm: number;
  hot_work_permit_active: boolean;
  tank_farm_permit_active: boolean;
}

export interface ChannelSpec {
  baseline: number;
  normal_band: [number, number];
  alarm_high: number;
  unit: string;
}

export interface WorkerIntrusion {
  worker_id: string;
  start_idx: number;
  end_idx: number;
  zone_id: string;
}

export interface ScenarioEvent {
  id: string;
  archetype: string;
  title: string;
  asset_ids: string[];
  zone_id: string;
  start_idx: number;
  end_idx: number;
  start_time: string;
  end_time: string;
  ramp_steps: number;
  affected_channels: string[];
  worker_intrusion?: WorkerIntrusion;
  narrative: string;
  single_channel_would_alarm: boolean;
  ground_truth_risk: string;
}

export interface PlantAsset {
  id: string;
  name: string;
  type: string;
  zone_id: string;
  location: { x: number; y: number };
  status: string;
  temperature_c: number;
  pressure_bar: number;
  health_score: number;
  maintenance_state: string;
  last_maintenance_at: string | null;
  next_maintenance_at: string | null;
}

export interface PlantZone {
  id: string;
  name: string;
  type: string;
  bounds: [number, number, number, number];
  asset_ids: string[];
}

export interface PlantWorker {
  id: string;
  name: string;
  role: string;
  shift: string;
  current_zone_id: string;
  location: { x: number; y: number };
  permit_id: string | null;
  home_zone_id: string;
}

export interface ScenarioData {
  meta: {
    plant_name: string;
    seed: number;
    dt_minutes: number;
    n_points: number;
    start_time: string;
    end_time: string;
    channel_specs: Record<string, ChannelSpec>;
  };
  timeline: TimelineRow[];
  plant: {
    name: string;
    zones: PlantZone[];
    assets: PlantAsset[];
    workers: PlantWorker[];
    worker_zone_overrides: WorkerIntrusion[];
    permits: unknown[];
    maintenance_tasks: unknown[];
  };
  events: ScenarioEvent[];
}

export interface RiskPoint {
  idx: number;
  risk: number;
  confidence: number;
  contributors: Record<string, number>;
}

export interface RiskTimelineData {
  operating_threshold: number;
  points: RiskPoint[];
}

export interface LiveWorker extends PlantWorker {
  zone_id: string;
  intruding: boolean;
}

const STEP_MS_BASE = 90; // ~65s for a full 720-point day at 1x speed

export interface KGNode {
  id: string;
  kind: string;
  label: string;
  [key: string]: unknown;
}
export interface KGEdge {
  source: string;
  target: string;
  relation: string;
}
export interface KGPath {
  event_id: string;
  path_nodes: string[];
  sentence: string;
}
export interface KGData {
  nodes: KGNode[];
  edges: KGEdge[];
  paths: KGPath[];
}

export function useDemoPlayer() {
  const [scenario, setScenario] = useState<ScenarioData | null>(null);
  const [riskTimeline, setRiskTimeline] = useState<RiskTimelineData | null>(null);
  const [kg, setKg] = useState<KGData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndexState] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch("/data/scenario.json").then((r) => r.json()),
      fetch("/data/risk_timeline.json").then((r) => r.json()),
      fetch("/data/kg.json").then((r) => r.json()),
    ])
      .then(([s, r, k]: [ScenarioData, RiskTimelineData, KGData]) => {
        if (cancelled) return;
        setScenario(s);
        setRiskTimeline(r);
        setKg(k);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!playing || !scenario) return;
    intervalRef.current = setInterval(() => {
      setIndexState((i) => {
        const next = i + 1;
        if (next >= scenario.timeline.length) {
          setPlaying(false);
          return i;
        }
        return next;
      });
    }, STEP_MS_BASE / speed);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, speed, scenario]);

  const play = useCallback(() => setPlaying(true), []);
  const pause = useCallback(() => setPlaying(false), []);
  const reset = useCallback(() => {
    setPlaying(false);
    setIndexState(0);
  }, []);
  const scrub = useCallback(
    (i: number) => {
      setPlaying(false);
      setIndexState(Math.max(0, Math.min(i, (scenario?.timeline.length ?? 1) - 1)));
    },
    [scenario]
  );

  const ready = !!scenario && !!riskTimeline && !!kg;
  const row = ready ? scenario!.timeline[index] : null;
  const riskPoint = ready ? riskTimeline!.points[index] : null;
  const activeEvent = ready
    ? scenario!.events.find((e) => index >= e.start_idx && index <= e.end_idx) ?? null
    : null;

  const workerPositions: LiveWorker[] = ready
    ? scenario!.plant.workers.map((w) => {
        const override = scenario!.plant.worker_zone_overrides.find(
          (o) => o.worker_id === w.id && index >= o.start_idx && index <= o.end_idx
        );
        return { ...w, zone_id: override ? override.zone_id : w.home_zone_id, intruding: !!override };
      })
    : [];

  return {
    ready,
    error,
    scenario,
    riskTimeline,
    kg,
    index,
    setIndex: scrub,
    playing,
    play,
    pause,
    reset,
    speed,
    setSpeed,
    row,
    riskPoint,
    activeEvent,
    workerPositions,
    totalPoints: scenario?.timeline.length ?? 0,
  };
}
