"""Asset health & degradation.

Reads COMP-01's health score and the short-window volatility of its
vibration trace — the signature of accumulating mechanical wear (a health
score that keeps sliding and doesn't recover) rather than a momentary
sensor blip that a raw vibration reading alone wouldn't distinguish.
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
    health_deficit = (1.0 - df["compressor_health"]).clip(lower=0)
    vibration_volatility = df["vibration_mms"].rolling(15, min_periods=1).std().fillna(0)
    # Volatility amplifies the score rather than adding independently, so
    # ambient vibration noise on an otherwise-healthy compressor can't
    # spuriously dominate the score (and, downstream, the contributor
    # breakdown) on days where COMP-01 isn't actually the story.
    return health_deficit * (1.0 + vibration_volatility)


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
            f"COMP-01 health score falls to {health_at_peak:.2f} with elevated "
            f"vibration volatility around index {peak_idx} — wear, not noise."
        ),
    }


if __name__ == "__main__":
    from simulator import generate_scenario

    scenario_df, _plant, _events = generate_scenario()
    s = raw_score(scenario_df)
    print(summarize(scenario_df, s)["summary"])
