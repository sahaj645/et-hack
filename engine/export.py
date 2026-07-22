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
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from simulator import CHANNEL_SPECS, DT_MINUTES, N_POINTS, SEED, WORKER_HOME_ZONES, generate_scenario  # noqa: E402

REPO_ROOT = _ENGINE_DIR.parent
OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "scenario.json"
RISK_TIMELINE_OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "risk_timeline.json"
METRICS_SOURCE_PATH = _ENGINE_DIR / "metrics" / "results.json"
METRICS_OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "metrics.json"


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

    if METRICS_SOURCE_PATH.exists():
        METRICS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(METRICS_SOURCE_PATH, METRICS_OUTPUT_PATH)
        print(f"Wrote {METRICS_OUTPUT_PATH.relative_to(REPO_ROOT)} (copied from {METRICS_SOURCE_PATH.relative_to(REPO_ROOT)})")
    else:
        print(
            f"Skipped metrics.json — {METRICS_SOURCE_PATH.relative_to(REPO_ROOT)} doesn't exist yet. "
            f"Run `python engine/metrics/run.py` first."
        )


if __name__ == "__main__":
    main()
