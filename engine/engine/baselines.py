"""Two conventional single-channel baselines, so the hero model's win is
a measured delta rather than a claim.

Baseline A — thresholds: fires the instant any channel crosses its own
fixed alarm_high. This is what most legacy DCS/SCADA setups do, and by
S1's design (`_validate_single_channel_normalcy`) it never fires during
any of the three archetypes as originally scripted — it only ever fires
at the (extrapolated) point a conventional alarm would eventually trip if
the trend were left unaddressed.

Baseline B — rolling z-score: a per-channel statistical control chart,
computed on a trailing window (both mean AND std are rolling, not fixed).
This is deliberately the realistic version of "a smarter conventional
system," and it is a textbook Bollinger-band-style anomaly detector — the
kind of thing a plant might already have. Its known weakness, which this
evaluation is designed to surface honestly rather than hide, is that a
*slow* drift gets partially absorbed into the rolling baseline as it
happens: the window's own mean creeps up with the ramp, so a gradual
compound incident is exactly the case a rolling single-channel baseline
struggles with. That weakness is real and well documented in SPC
literature, not an artifact of this simulation.
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

ROLLING_WINDOW_STEPS = 90  # 3 hours at 2-min resolution
ROLLING_MIN_PERIODS = 30  # 1 hour warm-up before the baseline is trusted
Z_THRESHOLD = 3.0


class ThresholdBaseline:
    name = "Baseline A (threshold)"

    def __init__(self, channel_specs: dict | None = None):
        self.specs = channel_specs or CHANNEL_SPECS

    def alarm_series(self, df: pd.DataFrame) -> pd.Series:
        fired = pd.Series(False, index=df.index)
        for ch, spec in self.specs.items():
            fired = fired | (df[ch] >= spec["alarm_high"])
        return fired


class ZScoreBaseline:
    name = "Baseline B (rolling z-score)"

    def __init__(
        self,
        channels: tuple = tuple(CHANNEL_SPECS),
        window: int = ROLLING_WINDOW_STEPS,
        min_periods: int = ROLLING_MIN_PERIODS,
        z_threshold: float = Z_THRESHOLD,
    ):
        self.channels = channels
        self.window = window
        self.min_periods = min_periods
        self.z_threshold = z_threshold

    def alarm_series(self, df: pd.DataFrame) -> pd.Series:
        fired = pd.Series(False, index=df.index)
        for ch in self.channels:
            roll_mean = df[ch].rolling(self.window, min_periods=self.min_periods).mean()
            roll_std = df[ch].rolling(self.window, min_periods=self.min_periods).std()
            z = (df[ch] - roll_mean).abs() / roll_std.clip(lower=1e-6)
            fired = fired | (z.fillna(0) >= self.z_threshold)
        return fired


if __name__ == "__main__":
    from simulator import generate_scenario

    scenario_df, _plant, events = generate_scenario()
    thresh = ThresholdBaseline()
    zscore = ZScoreBaseline()

    fired_a = thresh.alarm_series(scenario_df)
    fired_b = zscore.alarm_series(scenario_df)

    print(f"Baseline A total alarm-timesteps today: {int(fired_a.sum())}")
    print(f"Baseline B total alarm-timesteps today: {int(fired_b.sum())}")

    for evt in events:
        window = slice(evt["start_idx"], evt["end_idx"] + 1)
        a_fires = bool(fired_a.iloc[window].any())
        b_fires = bool(fired_b.iloc[window].any())
        print(f"  {evt['id']:>24}: Baseline A fires={a_fires}  Baseline B fires={b_fires}")
