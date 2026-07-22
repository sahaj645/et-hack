"""Open maintenance windows raising exposure.

Reads how much of TANK-01's relief capacity is currently offline for
maintenance. A relief valve mid function-test is routine and scheduled —
it only matters because it removes a safety margin exactly when something
else might need it.
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
    return (1.0 - df["relief_capacity_pct"] / 100.0).clip(lower=0)


def summarize(df: pd.DataFrame, series: pd.Series) -> dict:
    peak_idx = int(series.idxmax())
    peak_val = series.iloc[peak_idx]
    capacity_at_peak = float(df["relief_capacity_pct"].iloc[peak_idx])
    if peak_val <= 0.001:
        summary = "Relief capacity stays at 100% all day — no open maintenance exposure."
    else:
        summary = (
            f"Relief capacity drops to {capacity_at_peak:.0f}% at index {peak_idx} "
            f"while a maintenance action is in progress."
        )
    return {
        "agent": "maintenance_agent",
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
