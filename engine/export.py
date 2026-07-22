"""Run the simulator with a fixed seed and write the deterministic scenario
to web/public/data/scenario.json for the Next.js control room to render.
Also republishes engine/metrics/results.json (written by
`python engine/metrics/run.py`) to web/public/data/metrics.json — export.py
never computes a metric itself, only repackages the one place metrics are
actually measured, so the web UI can't ever show a number that didn't come
from a real evaluation run.

Usage:
    python engine/export.py
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parent
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents", _ENGINE_DIR / "copilot"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from simulator import CHANNEL_SPECS, DT_MINUTES, N_POINTS, SEED, WORKER_HOME_ZONES, generate_scenario  # noqa: E402

REPO_ROOT = _ENGINE_DIR.parent
OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "scenario.json"
RISK_TIMELINE_OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "risk_timeline.json"
KG_OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "kg.json"
COPILOT_CACHE_OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "copilot_cache.json"
COPILOT_CACHE_SOURCE_PATH = _ENGINE_DIR / "copilot" / "cache.json"
REPORTS_OUTPUT_DIR = REPO_ROOT / "web" / "public" / "reports"
METRICS_SOURCE_PATH = _ENGINE_DIR / "metrics" / "results.json"
METRICS_OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "metrics.json"
IMPACT_SUMMARY_OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "impact_summary.json"
WHATIF_FALLBACK_OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "whatif_fallback.json"

# Mirrors engine/metrics/run.py::EVAL_SEEDS. Kept as a separate literal
# (not imported) because `metrics.run` and engine/engine/metrics.py share
# the bare name "metrics" and importing the former from an external
# caller makes Python's module cache resolve "metrics" to the package,
# permanently shadowing the calc-library module run.py itself needs.
IMPACT_EVAL_SEEDS = list(range(2000, 2020))


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def build_payload() -> dict:
    df, plant, events = generate_scenario(seed=SEED)

    timeline = json.loads(df.to_json(orient="records"))

    workers_payload = []
    for w in plant.workers.values():
        record = asdict(w)
        record["home_zone_id"] = WORKER_HOME_ZONES[w.id]
        workers_payload.append(record)

    # Ground-truth per-timestep worker zone deviations, so the UI can place
    # worker dots accurately without inferring anything client-side — a
    # worker is in their home_zone_id at every index NOT covered by an
    # override below.
    worker_zone_overrides = [e["worker_intrusion"] for e in events if "worker_intrusion" in e]

    plant_payload = {
        "name": plant.name,
        "zones": [asdict(z) for z in plant.zones.values()],
        "assets": [asdict(a) for a in plant.assets.values()],
        "workers": workers_payload,
        "worker_zone_overrides": worker_zone_overrides,
        "permits": [asdict(p) for p in plant.permits.values()],
        "maintenance_tasks": [asdict(t) for t in plant.maintenance_tasks],
    }

    return {
        "meta": {
            "plant_name": plant.name,
            "seed": SEED,
            "dt_minutes": DT_MINUTES,
            "n_points": N_POINTS,
            "start_time": df["timestamp"].iloc[0],
            "end_time": df["timestamp"].iloc[-1],
            "channel_specs": CHANNEL_SPECS,
        },
        "timeline": timeline,
        "plant": plant_payload,
        "events": events,
    }


def build_risk_timeline_payload(df, hero_model) -> dict:
    """Full-day (all 720 points) fused risk score, confidence, and
    per-agent contributor attribution for the demo scenario — what the
    Live tab actually animates against. Computed the same way, with the
    same hero model, as engine/metrics/run.py's sample_incident printout;
    this just runs it over the whole day instead of one event window.
    """
    import risk_agent

    result = risk_agent.compute_risk_timeline(df, hero_model=hero_model)
    threshold = risk_agent.get_hero_operating_threshold()

    points = []
    for idx in range(len(df)):
        contributors = risk_agent.contributor_breakdown(result["agent_scores"], idx)
        points.append({
            "idx": idx,
            "risk": round(float(result["risk"].iloc[idx]), 2),
            "confidence": round(float(result["confidence"].iloc[idx]), 3),
            "contributors": {c["agent"]: c["contribution_pct"] for c in contributors},
        })

    return {"operating_threshold": round(threshold, 2), "points": points}


def main() -> None:
    payload = build_payload()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=_json_default, ensure_ascii=False)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({size_kb:.1f} KB)")
    print(f"  timeline points : {len(payload['timeline'])}")
    print(f"  assets          : {len(payload['plant']['assets'])}")
    print(f"  workers         : {len(payload['plant']['workers'])}")
    print(f"  events          : {len(payload['events'])}")

    print("Fitting hero model and computing full-day risk timeline...")
    from model import build_and_fit_hero_model
    df, _plant, _events = generate_scenario(seed=SEED)
    hero_model = build_and_fit_hero_model()
    risk_payload = build_risk_timeline_payload(df, hero_model)

    with RISK_TIMELINE_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(risk_payload, f, indent=2, ensure_ascii=False)
    risk_size_kb = RISK_TIMELINE_OUTPUT_PATH.stat().st_size / 1024
    print(f"Wrote {RISK_TIMELINE_OUTPUT_PATH.relative_to(REPO_ROOT)} ({risk_size_kb:.1f} KB)")

    print("Computing demo highlight (gas-leak lead-time facts for the cinematic Demo tab)...")
    import numpy as np

    import risk_agent
    from metrics import estimate_single_channel_alarm_time, first_detection_in_range

    demo_event = next(e for e in _events if e["archetype"] == "gas_leak_ventilation_failure")
    demo_alarm_series = risk_agent.alarm_series(df, hero_model=hero_model)
    demo_reference_idx = estimate_single_channel_alarm_time(df, demo_event, CHANNEL_SPECS)
    demo_search_end = int(np.ceil(demo_reference_idx))
    demo_detect_idx = first_detection_in_range(demo_alarm_series, demo_event["start_idx"], demo_search_end)
    demo_lead_minutes = (demo_reference_idx - demo_detect_idx) * DT_MINUTES

    demo_highlight = {
        "event_id": demo_event["id"],
        "hero_detect_idx": demo_detect_idx,
        "hero_detect_time": df["timestamp"].iloc[demo_detect_idx],
        "reference_idx": round(demo_reference_idx, 2),
        "reference_time_estimated": (
            df["timestamp"].iloc[int(demo_reference_idx)]
            if demo_reference_idx < len(df)
            else None
        ),
        "lead_time_minutes": round(demo_lead_minutes, 1),
        "methodology": (
            "reference_idx is a linear extrapolation of the observed ramp-up rate "
            "of the archetype's primary hazard channel(s), projecting forward to "
            "when a conventional single-channel alarm would fire if the trend "
            "continued unaddressed -- the same methodology as "
            "engine/metrics/run.py. It is not a value actually reached in the "
            "recorded (bounded, single-channel-normal) scenario data."
        ),
    }
    DEMO_HIGHLIGHT_OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "demo_highlight.json"
    with DEMO_HIGHLIGHT_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(demo_highlight, f, indent=2, ensure_ascii=False)
    print(f"Wrote {DEMO_HIGHLIGHT_OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  lead time: {demo_highlight['lead_time_minutes']} min (detect idx {demo_detect_idx} vs projected idx {demo_reference_idx:.1f})")

    print("Precomputing what-if fallback grid (offline backstop for WhatIf.tsx)...")
    from whatif import DEFAULT_WHATIF_INDEX, score_whatif

    whatif_grid = []
    for ventilation_pct in (70, 75, 80, 85, 90, 95, 100):
        for delay_maintenance in (False, True):
            whatif_grid.append({
                "ventilation_pct": ventilation_pct,
                "delay_maintenance": delay_maintenance,
                "result": score_whatif(df, hero_model, DEFAULT_WHATIF_INDEX, ventilation_pct, delay_maintenance),
            })
    whatif_payload = {
        "index": DEFAULT_WHATIF_INDEX,
        "baseline": score_whatif(df, hero_model, DEFAULT_WHATIF_INDEX, 100, False),
        "grid": whatif_grid,
    }
    with WHATIF_FALLBACK_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(whatif_payload, f, indent=2, ensure_ascii=False)
    print(f"Wrote {WHATIF_FALLBACK_OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(whatif_grid)} grid points)")

    print("Building plant knowledge graph...")
    from knowledge_graph import export_graph_payload
    _kg_df, kg_plant, kg_events = generate_scenario(seed=SEED)
    kg_payload = export_graph_payload(kg_plant, kg_events, _kg_df)
    with KG_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(kg_payload, f, indent=2, ensure_ascii=False)
    kg_size_kb = KG_OUTPUT_PATH.stat().st_size / 1024
    print(f"Wrote {KG_OUTPUT_PATH.relative_to(REPO_ROOT)} ({kg_size_kb:.1f} KB)")
    print(f"  nodes: {len(kg_payload['nodes'])}  edges: {len(kg_payload['edges'])}  paths: {len(kg_payload['paths'])}")

    print("Building operations copilot cache...")
    from templates import build_demo_cache
    _cp_df, cp_plant, cp_events = generate_scenario(seed=SEED)
    copilot_cache = build_demo_cache(_cp_df, cp_plant, cp_events, hero_model)
    COPILOT_CACHE_SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COPILOT_CACHE_SOURCE_PATH.open("w", encoding="utf-8") as f:
        json.dump(copilot_cache, f, indent=2, ensure_ascii=False)
    COPILOT_CACHE_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COPILOT_CACHE_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(copilot_cache, f, indent=2, ensure_ascii=False)
    print(f"Wrote {COPILOT_CACHE_SOURCE_PATH.relative_to(REPO_ROOT)} and {COPILOT_CACHE_OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  cached answers: {len(copilot_cache)}")

    print("Generating PDF incident reports...")
    import risk_agent
    import sop_agent
    from knowledge_graph import build_plant_graph, compute_hazardous_path
    from report_agent import build_incident_report

    _rp_df, rp_plant, rp_events = generate_scenario(seed=SEED)
    rp_graph = build_plant_graph(rp_plant)
    rp_risk_result = risk_agent.compute_risk_timeline(_rp_df, hero_model=hero_model)
    rp_per_archetype = {}
    if METRICS_SOURCE_PATH.exists():
        rp_per_archetype = json.loads(METRICS_SOURCE_PATH.read_text(encoding="utf-8"))["detection"]["per_archetype"]

    REPORTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for event in rp_events:
        rp_path = compute_hazardous_path(rp_graph, event, _rp_df, rp_plant)
        rp_sop_rec = sop_agent.recommend(_rp_df, event, hero_model=hero_model)
        rp_peak_idx = rp_sop_rec["peak_idx"]
        rp_contributors = risk_agent.contributor_breakdown(rp_risk_result["agent_scores"], rp_peak_idx)

        archetype_stats = rp_per_archetype.get(event["archetype"])
        lead_stats = None
        if archetype_stats and archetype_stats.get("hero"):
            lead_stats = {"n_instances": archetype_stats["n_instances"], **archetype_stats["hero"]}

        report_path = REPORTS_OUTPUT_DIR / f"{event['id']}.pdf"
        build_incident_report(
            report_path,
            event,
            rp_plant.name,
            float(rp_risk_result["risk"].iloc[rp_peak_idx]),
            float(rp_risk_result["confidence"].iloc[rp_peak_idx]),
            rp_contributors,
            rp_path["sentence"],
            rp_sop_rec,
            lead_stats,
        )
    print(f"Wrote {len(rp_events)} PDF reports to {REPORTS_OUTPUT_DIR.relative_to(REPO_ROOT)}")

    if METRICS_SOURCE_PATH.exists():
        METRICS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(METRICS_SOURCE_PATH, METRICS_OUTPUT_PATH)
        print(f"Wrote {METRICS_OUTPUT_PATH.relative_to(REPO_ROOT)} (copied from {METRICS_SOURCE_PATH.relative_to(REPO_ROOT)})")

        print("Building impact board summary...")
        from impact import build_impact_summary

        results = json.loads(METRICS_SOURCE_PATH.read_text(encoding="utf-8"))
        unsafe_entries = 0
        for eval_seed in IMPACT_EVAL_SEEDS:
            _, _, eval_events = generate_scenario(seed=eval_seed)
            unsafe_entries += sum(1 for e in eval_events if "worker_intrusion" in e)
        impact_summary = build_impact_summary(results, unsafe_entries, len(IMPACT_EVAL_SEEDS))

        with IMPACT_SUMMARY_OUTPUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(impact_summary, f, indent=2, ensure_ascii=False)
        print(f"Wrote {IMPACT_SUMMARY_OUTPUT_PATH.relative_to(REPO_ROOT)}")
        print(f"  unsafe zone entries flagged (measured, {len(IMPACT_EVAL_SEEDS)} eval seeds): {unsafe_entries}")
    else:
        print(
            f"Skipped metrics.json / impact_summary.json — {METRICS_SOURCE_PATH.relative_to(REPO_ROOT)} "
            f"doesn't exist yet. Run `python engine/metrics/run.py` first."
        )


if __name__ == "__main__":
    main()
