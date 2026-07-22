"""Active permit-to-work risk context.

Reads whether an ignition-source permit (hot work) is active. On its own
a hot-work permit is routine and authorized — it only becomes a
compounding risk factor when the fused score sees it alongside elevated
tank pressure/temperature and a degraded relief path, which is exactly
what risk_agent.py is for.
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
    return df["hot_work_permit_active"].astype(float)


def summarize(df: pd.DataFrame, series: pd.Series) -> dict:
    active_mask = series > 0
    if not active_mask.any():
        return {
            "agent": "permit_agent",
            "peak_idx": None,
            "peak_score": 0.0,
            "peak_time": None,
            "summary": "No hot-work permit active at any point today.",
        }
    peak_idx = int(active_mask.idxmax())
    return {
        "agent": "permit_agent",
        "peak_idx": peak_idx,
        "peak_score": 1.0,
        "peak_time": df["timestamp"].iloc[peak_idx] if "timestamp" in df.columns else None,
        "summary": f"Hot-work permit goes active at index {peak_idx} in a restricted zone.",
    }


if __name__ == "__main__":
    from simulator import generate_scenario

    scenario_df, _plant, _events = generate_scenario()
    s = raw_score(scenario_df)
    print(summarize(scenario_df, s)["summary"])
