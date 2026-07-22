"""Run the simulator with a fixed seed and write the deterministic scenario
to web/public/data/scenario.json for the Next.js control room to render.

Usage:
    python engine/export.py
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from simulator import CHANNEL_SPECS, DT_MINUTES, N_POINTS, SEED, generate_scenario

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "web" / "public" / "data" / "scenario.json"


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def build_payload() -> dict:
    df, plant, events = generate_scenario(seed=SEED)

    timeline = json.loads(df.to_json(orient="records"))

    plant_payload = {
        "name": plant.name,
        "zones": [asdict(z) for z in plant.zones.values()],
        "assets": [asdict(a) for a in plant.assets.values()],
        "workers": [asdict(w) for w in plant.workers.values()],
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


if __name__ == "__main__":
    main()
