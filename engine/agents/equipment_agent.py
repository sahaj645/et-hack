"""Asset health & degradation.

Reads how fast COMP-01's health score is actively falling — the signature
of accumulating mechanical wear while it's happening. Deliberately a rate,
not the absolute deficit: real wear doesn't self-heal, so an absolute
deficit stays elevated indefinitely once damage occurs, which would leave
this agent (and the fused risk score downstream) reporting "elevated"
for the rest of the day after a single past event even though nothing is
actively getting worse anymore. A monitoring agent should flag new
degradation, not keep re-flagging an old, stable, already-known condition.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1]
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pandas as pd

DECLINE_WINDOW_STEPS = 30  # ~1 hour: "how much has health dropped recently"


def raw_score(df: pd.DataFrame, normal_stats: dict | None = None) -> pd.Series:
    decline = (df["compressor_health"].shift(DECLINE_WINDOW_STEPS) - df["compressor_health"]).clip(lower=0)
    return decline.fillna(0.0)


def summarize(df: pd.DataFrame, series: pd.Series) -> dict:
    peak_idx = int(series.idxmax())
    peak_val = series.iloc[peak_idx]
    health_at_peak = float(df["compressor_health"].iloc[peak_idx])
    return {
        "agent": "equipment_agent",
        "peak_idx": peak_idx,
        "peak_score": float(peak_val),
        "peak_time": df["timestamp"].iloc[peak_idx] if "timestamp" in df.columns else None,
        "summary": (
            f"COMP-01 health drops {peak_val:.2f} points within an hour around index "
            f"{peak_idx}, reaching {health_at_peak:.2f} — active wear, not a stable reading."
        ),
    }


if __name__ == "__main__":
    from simulator import generate_scenario

    scenario_df, _plant, _events = generate_scenario()
    s = raw_score(scenario_df)
    print(summarize(scenario_df, s)["summary"])
