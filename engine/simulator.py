"""Seeded time-series simulator for PlantPulse.

Generates one 24h "plant day" of correlated sensor channels plus the
entity state (assets, workers, permits, weather) around them, and
injects three compound-risk incident archetypes. Each archetype is
built so every individual sensor stays under its own single-channel
alarm threshold for the entire window — `_validate_single_channel_normalcy`
enforces this at generation time. The danger only shows up when the
channels and the surrounding context (weather, permits, maintenance
state, worker location) are read together, which is the whole thesis
of PlantPulse.

Deterministic: same seed -> byte-identical DataFrame, every time.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from data_model import (
    Asset,
    AssetStatus,
    AssetType,
    MaintenanceState,
    MaintenanceTask,
    MaintenanceTaskStatus,
    Permit,
    PermitStatus,
    PermitType,
    Plant,
    Point,
    Worker,
    WorkerShift,
    Zone,
    ZoneType,
)

# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

SEED = 42
DT_MINUTES = 2
HOURS = 24
N_POINTS = int(HOURS * 60 / DT_MINUTES)  # 720 samples/day
START_TIME = datetime(2026, 7, 22, 0, 0, 0)

# Single-channel setpoints. `normal_band` is where the reading spends most
# of an uneventful day; `alarm_high` is the point a conventional single-
# sensor DCS/SCADA trip would fire. Representative of typical process-plant
# instrumentation (ISO 10816-style vibration zones, standard toxic/LEL gas
# detector bands, tank/compressor high-high trip points) — illustrative
# setpoints for this simulation, not any specific real facility's actuals.
CHANNEL_SPECS = {
    "pressure_bar": {"baseline": 10.0, "normal_band": (8.5, 11.5), "alarm_high": 15.0, "unit": "bar"},
    "gas_ppm": {"baseline": 3.0, "normal_band": (0.0, 10.0), "alarm_high": 50.0, "unit": "ppm"},
    "temp_tank_c": {"baseline": 45.0, "normal_band": (35.0, 55.0), "alarm_high": 80.0, "unit": "°C"},
    "temp_compressor_c": {"baseline": 70.0, "normal_band": (55.0, 85.0), "alarm_high": 110.0, "unit": "°C"},
    "vibration_mms": {"baseline": 2.2, "normal_band": (0.0, 4.5), "alarm_high": 7.1, "unit": "mm/s RMS"},
}

# Event windows, as [start_idx, end_idx] into the 720-point day (30 pts/hour).
GAS_LEAK_WINDOW = (60, 120)          # 02:00 - 04:00, night, low staffing
BEARING_FAILURE_WINDOW = (270, 390)  # 09:00 - 13:00, day shift, gradual trend
OVERPRESSURE_WINDOW = (480, 540)     # 16:00 - 18:00, afternoon heat load


# ---------------------------------------------------------------------------
# Plant layout
# ---------------------------------------------------------------------------

def build_plant(rng: np.random.Generator) -> Plant:
    """Static plant layout: 3 zones, 5 assets, 5 workers, 2 permits, 3 tasks."""
    plant = Plant(name="PlantPulse Demo Site — Process Unit 7")

    plant.zones["Z1"] = Zone(
        id="Z1", name="Tank Farm", type=ZoneType.RESTRICTED,
        bounds=(0, 0, 40, 30), asset_ids=["TANK-01", "PIPE-01", "VALVE-01"],
    )
    plant.zones["Z2"] = Zone(
        id="Z2", name="Compressor House", type=ZoneType.CAUTION,
        bounds=(40, 0, 80, 30), asset_ids=["COMP-01"],
    )
    plant.zones["Z3"] = Zone(
        id="Z3", name="Utility & Control Area", type=ZoneType.NORMAL,
        bounds=(0, 30, 80, 60), asset_ids=["BOIL-01"],
    )

    plant.assets["TANK-01"] = Asset(
        id="TANK-01", name="Crude Storage Tank 01", type=AssetType.STORAGE_TANK,
        zone_id="Z1", location=Point(15, 15), temperature_c=45.0, pressure_bar=10.0,
        health_score=0.91,
    )
    plant.assets["PIPE-01"] = Asset(
        id="PIPE-01", name="Tank Farm → Compressor Feed Line", type=AssetType.PIPELINE,
        zone_id="Z1", location=Point(35, 15), temperature_c=40.0, pressure_bar=10.0,
        health_score=0.88,
    )
    plant.assets["VALVE-01"] = Asset(
        id="VALVE-01", name="TANK-01 Pressure Relief Valve", type=AssetType.VALVE,
        zone_id="Z1", location=Point(20, 8), health_score=0.90,
    )
    plant.assets["COMP-01"] = Asset(
        id="COMP-01", name="Feed Compressor 01", type=AssetType.COMPRESSOR,
        zone_id="Z2", location=Point(60, 15), temperature_c=70.0, pressure_bar=9.6,
        health_score=0.86, maintenance_state=MaintenanceState.DUE,
    )
    plant.assets["BOIL-01"] = Asset(
        id="BOIL-01", name="Utility Boiler 01", type=AssetType.BOILER,
        zone_id="Z3", location=Point(20, 45), temperature_c=92.0, pressure_bar=6.5,
        health_score=0.95,
    )

    shifts = [WorkerShift.DAY, WorkerShift.DAY, WorkerShift.DAY, WorkerShift.EVENING, WorkerShift.NIGHT]
    roles = ["Process Operator", "Process Operator", "Field Technician", "Field Technician", "Shift Supervisor"]
    home_zones = ["Z2", "Z3", "Z2", "Z3", "Z3"]
    for i in range(5):
        wid = f"W-{i + 1:02d}"
        zid = home_zones[i]
        zone = plant.zones[zid]
        loc = Point((zone.bounds[0] + zone.bounds[2]) / 2, (zone.bounds[1] + zone.bounds[3]) / 2)
        plant.workers[wid] = Worker(
            id=wid, name=f"Worker {i + 1:02d}", role=roles[i], shift=shifts[i],
            current_zone_id=zid, location=loc,
        )

    plant.permits["P-01"] = Permit(
        id="P-01", worker_id="W-01", zone_id="Z1", type=PermitType.CONFINED_SPACE,
        status=PermitStatus.ACTIVE, issued_at=START_TIME, expires_at=START_TIME + timedelta(hours=24),
    )
    plant.permits["P-02"] = Permit(
        id="P-02", worker_id="W-03", zone_id="Z2", type=PermitType.COLD_WORK,
        status=PermitStatus.ACTIVE, issued_at=START_TIME, expires_at=START_TIME + timedelta(hours=24),
    )

    plant.maintenance_tasks.append(MaintenanceTask(
        id="MT-01", asset_id="COMP-01", task_type="Bearing inspection & lubrication",
        scheduled_at=START_TIME - timedelta(days=6), status=MaintenanceTaskStatus.OVERDUE,
    ))
    plant.maintenance_tasks.append(MaintenanceTask(
        id="MT-02", asset_id="VALVE-01", task_type="Relief valve function test",
        scheduled_at=START_TIME + timedelta(hours=15, minutes=30), status=MaintenanceTaskStatus.SCHEDULED,
    ))
    plant.maintenance_tasks.append(MaintenanceTask(
        id="MT-03", asset_id="TANK-01", task_type="Shell thickness ultrasonic survey",
        scheduled_at=START_TIME + timedelta(days=3), status=MaintenanceTaskStatus.SCHEDULED,
    ))

    return plant


# ---------------------------------------------------------------------------
# Noise / cycle helpers
# ---------------------------------------------------------------------------

def _ar1_noise(rng: np.random.Generator, n: int, phi: float = 0.85, scale: float = 1.0) -> np.ndarray:
    """Correlated AR(1) noise: x[t] = phi*x[t-1] + e[t]. Smooths white noise
    into the kind of drifting-but-continuous trace a real sensor produces.
    """
    e = rng.normal(0.0, scale, n)
    x = np.empty(n)
    x[0] = e[0]
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def _diurnal(n: int, dt_minutes: int, peak_hour: float, amplitude: float) -> np.ndarray:
    """Smooth cosine daily cycle peaking at `peak_hour`."""
    minutes = np.arange(n) * dt_minutes
    hours = (minutes / 60.0) % 24.0
    return amplitude * np.cos(2 * np.pi * (hours - peak_hour) / 24.0)


def _envelope(n: int, start_idx: int, end_idx: int, ramp_frac: float = 0.2) -> np.ndarray:
    """0 -> 1 -> 0 trapezoid with cosine-smoothed ramps, flat at 1.0 inside
    [start_idx, end_idx]. Used so injected events fade in/out instead of
    stepping discontinuously.
    """
    idx = np.arange(n)
    width = max(end_idx - start_idx, 1)
    ramp = max(1, int(width * ramp_frac))
    env = np.zeros(n)

    in_window = (idx >= start_idx) & (idx <= end_idx)
    env[in_window] = 1.0

    up = (idx >= start_idx) & (idx < start_idx + ramp)
    env[up] = 0.5 - 0.5 * np.cos(np.pi * (idx[up] - start_idx) / ramp)

    down = (idx > end_idx - ramp) & (idx <= end_idx)
    env[down] = 0.5 - 0.5 * np.cos(np.pi * (end_idx - idx[down]) / ramp)

    return env


# ---------------------------------------------------------------------------
# Baseline (uneventful) time series
# ---------------------------------------------------------------------------

def _simulate_baseline(rng: np.random.Generator) -> pd.DataFrame:
    n = N_POINTS
    timestamps = [START_TIME + timedelta(minutes=DT_MINUTES * i) for i in range(n)]

    # Shared latent "operational load" factor — the reason pressure, compressor
    # temperature, and vibration drift together rather than independently.
    load_factor = _ar1_noise(rng, n, phi=0.92, scale=1.0)
    load_factor = (load_factor - load_factor.mean()) / (load_factor.std() + 1e-9)

    pressure = (
        CHANNEL_SPECS["pressure_bar"]["baseline"]
        + _diurnal(n, DT_MINUTES, peak_hour=13, amplitude=0.45)
        + load_factor * 0.30
        + _ar1_noise(rng, n, phi=0.6, scale=0.12)
    )
    gas = (
        CHANNEL_SPECS["gas_ppm"]["baseline"]
        + _diurnal(n, DT_MINUTES, peak_hour=2, amplitude=1.2)
        + load_factor * 0.08
        + _ar1_noise(rng, n, phi=0.7, scale=0.5)
    )
    gas = np.clip(gas, 0.1, None)

    temp_tank = (
        CHANNEL_SPECS["temp_tank_c"]["baseline"]
        + _diurnal(n, DT_MINUTES, peak_hour=15, amplitude=5.5)
        + load_factor * 0.4
        + _ar1_noise(rng, n, phi=0.75, scale=0.6)
    )
    temp_compressor = (
        CHANNEL_SPECS["temp_compressor_c"]["baseline"]
        + _diurnal(n, DT_MINUTES, peak_hour=13, amplitude=6.5)
        + load_factor * 2.6
        + _ar1_noise(rng, n, phi=0.75, scale=0.9)
    )
    vibration = (
        CHANNEL_SPECS["vibration_mms"]["baseline"]
        + _diurnal(n, DT_MINUTES, peak_hour=13, amplitude=0.28)
        + load_factor * 0.32
        + _ar1_noise(rng, n, phi=0.65, scale=0.10)
    )
    vibration = np.clip(vibration, 0.3, None)

    wind_speed = 12.0 + _diurnal(n, DT_MINUTES, peak_hour=14, amplitude=6.0) + _ar1_noise(rng, n, phi=0.7, scale=1.1)
    wind_speed = np.clip(wind_speed, 0.5, None)

    ambient_temp = 28.0 + _diurnal(n, DT_MINUTES, peak_hour=15, amplitude=6.0) + _ar1_noise(rng, n, phi=0.85, scale=0.4)

    humidity = 55.0 + _diurnal(n, DT_MINUTES, peak_hour=5, amplitude=14.0) + _ar1_noise(rng, n, phi=0.8, scale=1.5)
    humidity = np.clip(humidity, 20.0, 95.0)

    wind_direction = np.cumsum(rng.normal(0, 4.0, n)) % 360.0

    # Gentle natural wear over the day; archetype 2 adds a much sharper drop.
    compressor_health = 0.94 - np.cumsum(np.full(n, 0.02 / n))

    relief_capacity = np.full(n, 100.0)

    shift_hours = (np.arange(n) * DT_MINUTES / 60.0) % 24.0
    workers_in_tank_farm = np.where(
        (shift_hours >= 6) & (shift_hours < 18), 3,
        np.where((shift_hours >= 18) & (shift_hours < 22), 1, 0),
    ).astype(int)

    hot_work_permit_active = np.zeros(n, dtype=bool)
    tank_farm_permit_active = np.ones(n, dtype=bool)

    return pd.DataFrame({
        "timestamp": [t.isoformat() for t in timestamps],
        "pressure_bar": pressure,
        "gas_ppm": gas,
        "temp_tank_c": temp_tank,
        "temp_compressor_c": temp_compressor,
        "vibration_mms": vibration,
        "wind_speed_kmh": wind_speed,
        "ambient_temp_c": ambient_temp,
        "humidity_pct": humidity,
        "wind_direction_deg": wind_direction,
        "compressor_health": compressor_health,
        "relief_capacity_pct": relief_capacity,
        "workers_in_tank_farm": workers_in_tank_farm,
        "hot_work_permit_active": hot_work_permit_active,
        "tank_farm_permit_active": tank_farm_permit_active,
    })


# ---------------------------------------------------------------------------
# Compound incident archetypes
# ---------------------------------------------------------------------------

def _idx_time(idx: int) -> str:
    return (START_TIME + timedelta(minutes=DT_MINUTES * idx)).isoformat()


def _inject_gas_leak_archetype(df: pd.DataFrame, plant: Plant, rng: np.random.Generator,
                                start_idx: int, end_idx: int) -> dict:
    """Archetype 1 — slow gas leak masked by a ventilation (wind) failure.

    Gas concentration ramps up slowly enough to stay well under the
    detector's alarm threshold. In isolation that reads as "normal, trending."
    What makes it dangerous is that it coincides with near-calm wind (no
    dispersion) AND an unpermitted worker entering the Tank Farm — neither of
    which a gas detector alone would ever know about.
    """
    n = len(df)
    env = _envelope(n, start_idx, end_idx, ramp_frac=0.3)

    df["gas_ppm"] = df["gas_ppm"] + env * rng.uniform(16.0, 20.0)
    df["pressure_bar"] = df["pressure_bar"] - env * rng.uniform(0.25, 0.4)

    window_slice = slice(start_idx, end_idx + 1)
    df.loc[df.index[window_slice], "wind_speed_kmh"] = np.clip(
        df.loc[df.index[window_slice], "wind_speed_kmh"] * 0.25, 0.5, None
    )

    worker_start = start_idx + int((end_idx - start_idx) * 0.4)
    worker_end = start_idx + int((end_idx - start_idx) * 0.85)
    worker_slice = slice(worker_start, worker_end + 1)
    df.loc[df.index[worker_slice], "workers_in_tank_farm"] = 1
    df.loc[df.index[worker_slice], "tank_farm_permit_active"] = False

    worker = plant.workers["W-05"]  # night-shift supervisor, normally based in Z3
    worker.current_zone_id = "Z1"

    return {
        "id": "evt-gas-leak-01",
        "archetype": "gas_leak_ventilation_failure",
        "title": "Slow Gas Leak Masked by Ventilation Failure",
        "asset_ids": ["TANK-01", "PIPE-01"],
        "zone_id": "Z1",
        "start_idx": int(start_idx),
        "end_idx": int(end_idx),
        "start_time": _idx_time(start_idx),
        "end_time": _idx_time(end_idx),
        "affected_channels": ["gas_ppm", "pressure_bar", "wind_speed_kmh", "workers_in_tank_farm"],
        "narrative": (
            "Gas concentration near TANK-01 climbs gradually while wind speed "
            "collapses to near-calm, killing natural dispersion. Neither reading "
            "alone would trip an alarm. Partway through the window, night-shift "
            "supervisor W-05 enters the Tank Farm without an active gas-zone entry "
            "permit — exactly when the gas has nowhere to go."
        ),
        "single_channel_would_alarm": False,
        "ground_truth_risk": "high",
    }


def _inject_bearing_failure_archetype(df: pd.DataFrame, plant: Plant, rng: np.random.Generator,
                                       start_idx: int, end_idx: int) -> dict:
    """Archetype 2 — early bearing failure on an overdue-maintenance compressor.

    Vibration and discharge temperature both trend upward but stay under
    their alarm thresholds all day. The tell is that COMP-01's maintenance
    task has been overdue for six days going into the window, and health
    score is falling in a way that does not recover after the window ends
    (mechanical wear, not noise).
    """
    n = len(df)
    env = _envelope(n, start_idx, end_idx, ramp_frac=0.15)

    df["vibration_mms"] = df["vibration_mms"] + env * rng.uniform(1.6, 1.9)
    df["temp_compressor_c"] = df["temp_compressor_c"] + env * rng.uniform(13.0, 16.0)

    cum_env = np.cumsum(env)
    health_drop = (cum_env / max(cum_env.max(), 1e-9)) * rng.uniform(0.32, 0.40)
    df["compressor_health"] = np.clip(df["compressor_health"] - health_drop, 0.05, 1.0)

    asset = plant.asset_by_id("COMP-01")
    asset.maintenance_state = MaintenanceState.OVERDUE
    asset.health_score = float(df["compressor_health"].iloc[end_idx])
    for task in plant.maintenance_tasks:
        if task.asset_id == "COMP-01":
            task.status = MaintenanceTaskStatus.OVERDUE

    return {
        "id": "evt-bearing-failure-01",
        "archetype": "bearing_failure_overdue_maintenance",
        "title": "Early Bearing Failure on an Overdue-Maintenance Compressor",
        "asset_ids": ["COMP-01"],
        "zone_id": "Z2",
        "start_idx": int(start_idx),
        "end_idx": int(end_idx),
        "start_time": _idx_time(start_idx),
        "end_time": _idx_time(end_idx),
        "affected_channels": ["vibration_mms", "temp_compressor_c", "compressor_health"],
        "narrative": (
            "COMP-01 vibration and discharge temperature both trend upward across "
            "the day shift but never cross their single-sensor alarm setpoints. "
            "Task MT-01 (bearing inspection & lubrication) has been overdue for six "
            "days, and health score declines and does not recover — the "
            "signature of accumulating mechanical wear, not sensor noise."
        ),
        "single_channel_would_alarm": False,
        "ground_truth_risk": "high",
    }


def _inject_overpressure_archetype(df: pd.DataFrame, plant: Plant, rng: np.random.Generator,
                                    start_idx: int, end_idx: int) -> dict:
    """Archetype 3 — overpressure risk while the relief path is degraded.

    Tank pressure and temperature both rise with the afternoon heat load but
    stay under their alarm thresholds. The compounding fact is that TANK-01's
    relief valve is mid-maintenance (reduced relief capacity) at the same
    time an active hot-work permit is issued in the same restricted zone.
    """
    n = len(df)
    env = _envelope(n, start_idx, end_idx, ramp_frac=0.2)

    df["pressure_bar"] = df["pressure_bar"] + env * rng.uniform(2.1, 2.5)
    df["temp_tank_c"] = df["temp_tank_c"] + env * rng.uniform(20.0, 25.0)
    df["relief_capacity_pct"] = df["relief_capacity_pct"] - env * rng.uniform(38.0, 45.0)

    permit_start = start_idx + int((end_idx - start_idx) * 0.25)
    permit_end = start_idx + int((end_idx - start_idx) * 0.9)
    df.loc[df.index[permit_start:permit_end + 1], "hot_work_permit_active"] = True

    valve = plant.asset_by_id("VALVE-01")
    valve.maintenance_state = MaintenanceState.IN_PROGRESS
    valve.status = AssetStatus.MAINTENANCE
    for task in plant.maintenance_tasks:
        if task.asset_id == "VALVE-01":
            task.status = MaintenanceTaskStatus.IN_PROGRESS

    return {
        "id": "evt-overpressure-01",
        "archetype": "overpressure_degraded_relief",
        "title": "Overpressure Risk While the Relief Path Is Degraded",
        "asset_ids": ["TANK-01", "VALVE-01"],
        "zone_id": "Z1",
        "start_idx": int(start_idx),
        "end_idx": int(end_idx),
        "start_time": _idx_time(start_idx),
        "end_time": _idx_time(end_idx),
        "affected_channels": ["pressure_bar", "temp_tank_c", "relief_capacity_pct", "hot_work_permit_active"],
        "narrative": (
            "TANK-01 pressure and shell temperature both climb with the afternoon "
            "heat load but stay under their high-high alarm setpoints. At the same "
            "time, VALVE-01 (the relief valve) is mid function-test — cutting "
            "effective relief capacity roughly in half — while an active "
            "hot-work permit is in force in the same restricted zone."
        ),
        "single_channel_would_alarm": False,
        "ground_truth_risk": "critical",
    }


def _validate_single_channel_normalcy(df: pd.DataFrame, events: list[dict]) -> None:
    """Enforce the core thesis: every event stays under each affected raw
    channel's alarm threshold. If this ever fails, the archetype has drifted
    into being a normal single-sensor alarm and needs retuning, not a patched
    number.
    """
    raw_channels = set(CHANNEL_SPECS)
    for evt in events:
        window = df.iloc[evt["start_idx"]:evt["end_idx"] + 1]
        for channel in evt["affected_channels"]:
            if channel not in raw_channels:
                continue
            alarm = CHANNEL_SPECS[channel]["alarm_high"]
            peak = window[channel].max()
            if peak >= alarm:
                raise AssertionError(
                    f"{evt['id']}: {channel} peaked at {peak:.2f}, breaching the "
                    f"single-channel alarm threshold of {alarm:.2f}. This archetype "
                    f"is no longer a compound near-miss — retune the injection, "
                    f"don't edit the output."
                )


# ---------------------------------------------------------------------------
# Illustrative-only compound risk index (S1 sanity-check plots)
# ---------------------------------------------------------------------------

def preview_compound_risk_index(df: pd.DataFrame) -> pd.Series:
    """Transparent, illustrative-only compound score used solely for the S1
    preview plots. This is NOT the S2 fusion model (engine/engine/model.py) —
    it is a plain sum of per-channel normalized deviations, scaled by a
    context multiplier built from exactly the compounding facts each
    archetype relies on (calm wind + worker presence, degraded relief
    capacity + active hot-work permit, declining equipment health).
    """
    def _norm(col: str) -> pd.Series:
        spec = CHANNEL_SPECS[col]
        return ((df[col] - spec["baseline"]).clip(lower=0) / (spec["alarm_high"] - spec["baseline"])).clip(upper=1.5)

    base = _norm("pressure_bar") + _norm("gas_ppm") + _norm("temp_tank_c") + _norm("temp_compressor_c") + _norm("vibration_mms")

    calm_boost = (1.0 - df["wind_speed_kmh"] / 12.0).clip(lower=0.0, upper=1.0)
    worker_boost = df["workers_in_tank_farm"].clip(upper=1)
    relief_boost = (1.0 - df["relief_capacity_pct"] / 100.0).clip(lower=0.0, upper=1.0)
    permit_boost = df["hot_work_permit_active"].astype(float)
    health_boost = (1.0 - df["compressor_health"]).clip(lower=0.0, upper=1.0)

    context_multiplier = (
        1.0
        + 1.2 * calm_boost * worker_boost
        + 1.5 * relief_boost * permit_boost
        + 1.3 * health_boost
    )

    return base * context_multiplier


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_scenario(seed: int = SEED) -> tuple[pd.DataFrame, Plant, list[dict]]:
    """Generate one full deterministic scenario: baseline day + 3 compound
    incidents layered in. Returns (timeseries, plant, ground_truth_events).
    """
    rng = np.random.default_rng(seed)
    plant = build_plant(rng)
    df = _simulate_baseline(rng)

    events = [
        _inject_gas_leak_archetype(df, plant, rng, *GAS_LEAK_WINDOW),
        _inject_bearing_failure_archetype(df, plant, rng, *BEARING_FAILURE_WINDOW),
        _inject_overpressure_archetype(df, plant, rng, *OVERPRESSURE_WINDOW),
    ]

    _validate_single_channel_normalcy(df, events)

    return df, plant, events


if __name__ == "__main__":
    scenario_df, scenario_plant, scenario_events = generate_scenario()
    print(f"Generated {len(scenario_df)} timesteps for '{scenario_plant.name}'")
    print(f"Assets: {list(scenario_plant.assets)}")
    print(f"Workers: {list(scenario_plant.workers)}")
    print("Events:")
    for e in scenario_events:
        print(f"  - [{e['start_idx']:>3}:{e['end_idx']:>3}] {e['title']} (channels: {', '.join(e['affected_channels'])})")
    print("\nAll events verified single-channel-normal — compound thesis holds.")
