"""Shared 'what does normal look like' reference, learned once from many
held-out quiet seeded days that never contain an injected archetype.

Every z-score baseline, every specialist agent's normalization, and the
hero model's feature scaler all import this instead of hard-coding a
number — one source of truth for "normal," reproducible from the same
seed range every time.

Calibration seeds (1000-1029) are disjoint from both the demo seed (42)
and the evaluation seeds used in engine/metrics/run.py, so nothing is
ever calibrated and evaluated on the same data.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1]
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np
import pandas as pd

from simulator import CHANNEL_SPECS, _simulate_baseline  # noqa: E402

CALIBRATION_SEEDS = range(1000, 1030)  # 30 held-out quiet days

_CONTEXT_COLUMNS = ["wind_speed_kmh", "compressor_health", "relief_capacity_pct"]

_AGENT_MODULES = (
    "sensor_agent",
    "equipment_agent",
    "permit_agent",
    "maintenance_agent",
    "worker_agent",
    "weather_agent",
)


@lru_cache(maxsize=1)
def get_calibration_frames() -> tuple:
    """The 30 quiet calibration days, simulated once and cached."""
    return tuple(_simulate_baseline(np.random.default_rng(s)) for s in CALIBRATION_SEEDS)


@lru_cache(maxsize=1)
def get_normal_stats() -> dict:
    """Per-channel mean/std across all calibration days, for z-score
    baselines and feature normalization."""
    combined = pd.concat(get_calibration_frames(), ignore_index=True)
    stats = {}
    for channel in list(CHANNEL_SPECS) + _CONTEXT_COLUMNS:
        stats[channel] = {
            "mean": float(combined[channel].mean()),
            "std": float(combined[channel].std()),
        }

    # Wind has a genuine, deliberate diurnal cycle (calmer at night) — a
    # single flat-average reference would make every night look
    # anomalously calm even when nothing is wrong. Hour-of-day buckets let
    # weather_agent compare like against like.
    hours = pd.to_datetime(combined["timestamp"]).dt.hour
    hourly_wind = combined.groupby(hours)["wind_speed_kmh"].mean()
    stats["wind_speed_kmh_by_hour"] = {int(h): float(v) for h, v in hourly_wind.items()}

    return stats


@lru_cache(maxsize=1)
def get_agent_calibration() -> dict:
    """p50 / p99 of each agent's raw (un-normalized) score across the 30
    quiet calibration days — the reference every agent divides by to turn
    its own arbitrary units into "how many times worse than a bad-but-normal
    day is this."
    """
    import importlib

    frames = get_calibration_frames()
    result = {}
    for name in _AGENT_MODULES:
        mod = importlib.import_module(name)
        raws = pd.concat([mod.raw_score(f) for f in frames], ignore_index=True)
        result[name] = {
            "p50": float(raws.quantile(0.50)),
            "p99": float(raws.quantile(0.99)),
            "max": float(raws.max()),
        }
    return result


if __name__ == "__main__":
    stats = get_normal_stats()
    print("Normal-operation stats (30 calibration days):")
    for ch, s in stats.items():
        print(f"  {ch:>22}: mean={s['mean']:.3f}  std={s['std']:.3f}")

    print("\nPer-agent raw-score calibration (p50 / p99 / max):")
    for name, s in get_agent_calibration().items():
        print(f"  {name:>16}: p50={s['p50']:.3f}  p99={s['p99']:.3f}  max={s['max']:.3f}")
