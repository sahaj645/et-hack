"""Worker presence in hazardous/restricted zones.

Reads how many workers are in the Tank Farm and whether their presence is
covered by an active gas-zone entry permit. Presence during a permitted
day shift is routine; presence without a valid permit is the risk this
agent exists to catch.
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
    unpermitted = 1.0 - df["tank_farm_permit_active"].astype(float)
    return df["workers_in_tank_farm"].astype(float) * unpermitted


def summarize(df: pd.DataFrame, series: pd.Series) -> dict:
    peak_idx = int(series.idxmax())
    peak_val = series.iloc[peak_idx]
    if peak_val <= 0.001:
        summary = "No unpermitted worker presence in the Tank Farm today."
    else:
        count = int(df["workers_in_tank_farm"].iloc[peak_idx])
        summary = (
            f"{count} worker(s) in the Tank Farm without an active entry permit "
            f"at index {peak_idx}."
        )
    return {
        "agent": "worker_agent",
        "peak_idx": peak_idx,
        "peak_score": float(peak_val),
        "peak_time": df["timestamp"].iloc[peak_idx] if "timestamp" in df.columns else None,
        "summary": summary,
    }


if __name__ == "__main__":
    from simulator import generate_scenario

    scenario_df, _plant, _events = generate_scenario()
    s = raw_score(scenario_df)
    print(summarize(scenario_df, s)["summary"])
