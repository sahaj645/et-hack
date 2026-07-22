"""Dispersion / ventilation modifier.

Reads wind speed as a proxy for how effectively any airborne release would
disperse. Calm conditions aren't dangerous by themselves — they're a
multiplier on whatever else is in the air, which is exactly why this
agent's contribution only matters when it's fused with the others.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1]
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pandas as pd


def raw_score(df: pd.DataFrame, normal_stats: dict | None = None) -> pd.Series:
    if normal_stats is None:
        from calibration import get_normal_stats
        normal_stats = get_normal_stats()
    # Compare against the expected wind for THIS hour of day, not a flat
    # 24h average — wind has a genuine diurnal cycle (calmer at night by
    # design), so a flat reference would flag every ordinary night as
    # anomalously calm.
    by_hour = normal_stats["wind_speed_kmh_by_hour"]
    hours = pd.to_datetime(df["timestamp"]).dt.hour
    reference_wind = hours.map(by_hour).astype(float)
    return (1.0 - df["wind_speed_kmh"] / reference_wind.clip(lower=1e-6)).clip(lower=0)


def summarize(df: pd.DataFrame, series: pd.Series) -> dict:
    peak_idx = int(series.idxmax())
    peak_val = series.iloc[peak_idx]
    wind_at_peak = float(df["wind_speed_kmh"].iloc[peak_idx])
    return {
        "agent": "weather_agent",
        "peak_idx": peak_idx,
        "peak_score": float(peak_val),
        "peak_time": df["timestamp"].iloc[peak_idx] if "timestamp" in df.columns else None,
        "summary": (
            f"Wind drops to {wind_at_peak:.1f} km/h at index {peak_idx} — "
            f"near-calm, dispersion effectively stalled."
        ),
    }


if __name__ == "__main__":
    from simulator import generate_scenario

    scenario_df, _plant, _events = generate_scenario()
    s = raw_score(scenario_df)
    print(summarize(scenario_df, s)["summary"])
