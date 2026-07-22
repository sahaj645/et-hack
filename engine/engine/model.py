"""The hero model: a genuinely multivariate anomaly detector.

Model choice: IsolationForest, trained ONLY on the 15-feature vectors from
30 held-out quiet calibration days (engine/engine/calibration.py) — never
on labeled incidents. Three reasons this beats a supervised
logistic/GBM here:

1. Honesty about data. We have exactly 3 hand-designed archetypes. A
   supervised model trained on 3 shapes would learn to recognize those 3
   shapes, not "compound risk" in general — it would overfit to our own
   fixtures and the metrics would be measuring memorization, not
   detection.
2. Real plants match this: safety incidents are rare and mostly unlabeled.
   An operator can always give you months of normal operation; they
   cannot give you a labeled training set of real overpressure events.
   An unsupervised approach is the honest thing to ship.
3. It's still genuinely multivariate. IsolationForest isolates a point by
   randomly partitioning the *joint* feature space — a point that's
   unremarkable on every individual feature but sits in a region no
   partition reaches quickly (because several features are jointly
   unusual at once) still gets a short average path length, i.e. a high
   anomaly score. That is precisely the "normal on every channel,
   dangerous in combination" pattern this product exists to catch.

MODEL_RANDOM_STATE controls sklearn's internal bootstrap/split randomness
only (not simulator data) — fixed so the same feature matrix always
produces the same fitted model and the same scores.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1]
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

MODEL_RANDOM_STATE = 42
OPERATING_PERCENTILE = 0.99  # ~1%/day false-alarm budget, calibrated on quiet days


class HeroModel:
    def __init__(self, n_estimators: int = 200, contamination: float = 0.02):
        self.scaler = StandardScaler()
        self.forest = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=MODEL_RANDOM_STATE,
        )
        self.calibration_scores_: np.ndarray | None = None
        self.threshold_: float | None = None

    def fit(self, X_normal: pd.DataFrame) -> "HeroModel":
        Xs = self.scaler.fit_transform(X_normal)
        self.forest.fit(Xs)
        # sklearn's score_samples: higher = more normal. We flip sign so
        # higher = more anomalous, which is the intuitive direction for a
        # risk score.
        self.calibration_scores_ = -self.forest.score_samples(Xs)
        self.threshold_ = float(np.quantile(self.calibration_scores_, OPERATING_PERCENTILE))
        return self

    def anomaly_score(self, X: pd.DataFrame) -> np.ndarray:
        Xs = self.scaler.transform(X)
        return -self.forest.score_samples(Xs)

    def percentile(self, raw_scores: np.ndarray) -> np.ndarray:
        """Percentile of each raw score relative to the calibration (normal)
        distribution: 50 = typical normal reading, 99 = as anomalous as the
        worst 1% of normal operation, 100+ territory = worse than anything
        seen on a quiet day.
        """
        if self.calibration_scores_ is None:
            raise RuntimeError("HeroModel.fit() must run before percentile()")
        sorted_cal = np.sort(self.calibration_scores_)
        ranks = np.searchsorted(sorted_cal, raw_scores, side="right")
        return ranks / len(sorted_cal) * 100.0


def build_and_fit_hero_model() -> HeroModel:
    """Train the hero model on the 30 calibration (quiet) days — the only
    data it is ever allowed to learn "normal" from.
    """
    from calibration import get_calibration_frames, get_normal_stats
    from features import build_feature_matrix

    normal_stats = get_normal_stats()
    frames = get_calibration_frames()
    X = pd.concat([build_feature_matrix(f, normal_stats) for f in frames], ignore_index=True)

    model = HeroModel()
    model.fit(X)
    return model


if __name__ == "__main__":
    from simulator import generate_scenario
    from features import build_feature_matrix

    hero = build_and_fit_hero_model()
    print(f"Trained on {len(hero.calibration_scores_)} normal-day timesteps.")
    print(f"Operating threshold (raw score, {OPERATING_PERCENTILE:.0%} percentile): {hero.threshold_:.4f}")

    scenario_df, _plant, events = generate_scenario()
    X = build_feature_matrix(scenario_df)
    raw = hero.anomaly_score(X)
    pct = hero.percentile(raw)

    for evt in events:
        window = slice(evt["start_idx"], evt["end_idx"] + 1)
        peak_pct = pct[window].max()
        print(f"  {evt['id']:>24}: peak percentile = {peak_pct:5.1f}  (alert at 99.0)")
