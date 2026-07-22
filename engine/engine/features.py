"""Multivariate feature extraction for the hero model.

Fifteen engineered features per timestep: five per-channel z-scores (what
a single-channel system already has), five short trailing slopes (is it
*trending*, even from within the normal band), and five contextual
features (wind, worker/permit exposure, relief capacity, hot-work permit,
equipment health). The context features are what let the model catch a
compound pattern no single sensor reading would ever flag alone.
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

SLOPE_WINDOW_STEPS = 15  # 30 minutes at 2-min resolution

FEATURE_NAMES = (
    [f"z_{ch}" for ch in CHANNEL_SPECS]
    + [f"slope_{ch}" for ch in CHANNEL_SPECS]
    + ["calm_factor", "worker_exposure", "relief_deficit", "hot_work_permit", "health_deficit"]
)


def build_feature_matrix(df: pd.DataFrame, normal_stats: dict | None = None) -> pd.DataFrame:
    if normal_stats is None:
        from calibration import get_normal_stats
        normal_stats = get_normal_stats()

    cols = {}
    for ch in CHANNEL_SPECS:
        mu, sigma = normal_stats[ch]["mean"], normal_stats[ch]["std"]
        cols[f"z_{ch}"] = (df[ch] - mu) / max(sigma, 1e-6)
        cols[f"slope_{ch}"] = (df[ch] - df[ch].shift(SLOPE_WINDOW_STEPS)) / SLOPE_WINDOW_STEPS

    reference_wind = normal_stats["wind_speed_kmh"]["mean"]
    cols["calm_factor"] = (1.0 - df["wind_speed_kmh"] / max(reference_wind, 1e-6)).clip(lower=0)
    cols["worker_exposure"] = df["workers_in_tank_farm"].astype(float) * (
        1.0 - df["tank_farm_permit_active"].astype(float)
    )
    cols["relief_deficit"] = (1.0 - df["relief_capacity_pct"] / 100.0).clip(lower=0)
    cols["hot_work_permit"] = df["hot_work_permit_active"].astype(float)
    cols["health_deficit"] = (1.0 - df["compressor_health"]).clip(lower=0)

    features = pd.DataFrame(cols, index=df.index)
    features = features.fillna(0.0)
    return features[FEATURE_NAMES]


if __name__ == "__main__":
    from simulator import generate_scenario

    scenario_df, _plant, _events = generate_scenario()
    feats = build_feature_matrix(scenario_df)
    print(f"Feature matrix: {feats.shape[0]} rows x {feats.shape[1]} columns")
    print(feats.describe().T[["mean", "std", "min", "max"]])
