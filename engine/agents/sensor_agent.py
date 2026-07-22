"""Per-channel anomaly signal from the 5 raw process sensors.

This agent deliberately knows nothing but the sensors themselves — no
weather, no permits, no maintenance history. It's the same information a
conventional single-channel alarm has. The point of fusing it with the
other five agents (risk_agent.py) is to show what a system stops seeing
the moment it stops here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1]
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pandas as pd

from simulator import CHANNEL_SPECS  # noqa: E402


def raw_score(df: pd.DataFrame, normal_stats: dict | None = None) -> pd.Series:
    """Worst-offending-channel z-score at each instant (positive deviations
    only — a channel reading *below* baseline isn't a sensor anomaly here).
    """
    if normal_stats is None:
        from calibration import get_normal_stats
        normal_stats = get_normal_stats()

    z_scores = []
    for ch in CHANNEL_SPECS:
        mu, sigma = normal_stats[ch]["mean"], normal_stats[ch]["std"]
        z_scores.append(((df[ch] - mu) / max(sigma, 1e-6)).clip(lower=0))
    return pd.concat(z_scores, axis=1).max(axis=1)


def summarize(df: pd.DataFrame, series: pd.Series) -> dict:
    peak_idx = int(series.idxmax())
    peak_channel = None
    peak_val = series.iloc[peak_idx]
    return {
        "agent": "sensor_agent",
        "peak_idx": peak_idx,
        "peak_score": float(peak_val),
        "peak_time": df["timestamp"].iloc[peak_idx] if "timestamp" in df.columns else None,
        "summary": (
            f"Worst single-channel z-score reaches {peak_val:.2f}σ above normal "
            f"at index {peak_idx}."
        ),
    }


if __name__ == "__main__":
    from simulator import generate_scenario

    scenario_df, _plant, _events = generate_scenario()
    s = raw_score(scenario_df)
    print(summarize(scenario_df, s)["summary"])
