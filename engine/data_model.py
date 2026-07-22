"""Core domain model for PlantPulse.

Defines the entities a control room actually tracks — assets, workers,
zones, permits, maintenance schedule, and weather — that the fusion
engine (S2) reasons over jointly. Kept deliberately plain (dataclasses,
no ORM/DB) since the simulator and exporter are the only consumers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AssetType(str, Enum):
    STORAGE_TANK = "storage_tank"
    BOILER = "boiler"
    COMPRESSOR = "compressor"
    PIPELINE = "pipeline"
    VALVE = "valve"


class AssetStatus(str, Enum):
    RUNNING = "running"
    IDLE = "idle"
    MAINTENANCE = "maintenance"
    FAULT = "fault"


class MaintenanceState(str, Enum):
    HEALTHY = "healthy"
    DUE = "due"
    OVERDUE = "overdue"
    IN_PROGRESS = "in_progress"


class ZoneType(str, Enum):
    NORMAL = "normal"
    CAUTION = "caution"
    RESTRICTED = "restricted"


class WorkerShift(str, Enum):
    DAY = "day"
    EVENING = "evening"
    NIGHT = "night"


class PermitType(str, Enum):
    HOT_WORK = "hot_work"
    CONFINED_SPACE = "confined_space"
    COLD_WORK = "cold_work"
    ELECTRICAL_ISOLATION = "electrical_isolation"


class PermitStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING = "pending"
    REVOKED = "revoked"


class MaintenanceTaskStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    OVERDUE = "overdue"


class WeatherCondition(str, Enum):
    CLEAR = "clear"
    OVERCAST = "overcast"
    RAIN = "rain"
    STORM = "storm"


# ---------------------------------------------------------------------------
# Spatial primitive
# ---------------------------------------------------------------------------

@dataclass
class Point:
    x: float
    y: float


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------

@dataclass
class Asset:
    id: str
    name: str
    type: AssetType
    zone_id: str
    location: Point
    status: AssetStatus = AssetStatus.RUNNING
    temperature_c: float = 25.0
    pressure_bar: float = 1.0
    health_score: float = 1.0  # 0 (failed) .. 1 (as-new)
    maintenance_state: MaintenanceState = MaintenanceState.HEALTHY
    last_maintenance_at: Optional[datetime] = None
    next_maintenance_at: Optional[datetime] = None


@dataclass
class Worker:
    id: str
    name: str
    role: str
    shift: WorkerShift
    current_zone_id: str
    location: Point
    permit_id: Optional[str] = None


@dataclass
class Zone:
    id: str
    name: str
    type: ZoneType
    bounds: tuple[float, float, float, float]  # (xmin, ymin, xmax, ymax)
    asset_ids: list[str] = field(default_factory=list)


@dataclass
class Permit:
    id: str
    worker_id: str
    zone_id: str
    type: PermitType
    status: PermitStatus
    issued_at: datetime
    expires_at: datetime


@dataclass
class MaintenanceTask:
    id: str
    asset_id: str
    task_type: str
    scheduled_at: datetime
    status: MaintenanceTaskStatus


@dataclass
class Weather:
    timestamp: datetime
    ambient_temp_c: float
    humidity_pct: float
    wind_speed_kmh: float
    wind_direction_deg: float
    condition: WeatherCondition


@dataclass
class Plant:
    name: str
    zones: dict[str, Zone] = field(default_factory=dict)
    assets: dict[str, Asset] = field(default_factory=dict)
    workers: dict[str, Worker] = field(default_factory=dict)
    permits: dict[str, Permit] = field(default_factory=dict)
    maintenance_tasks: list[MaintenanceTask] = field(default_factory=list)

    def asset_by_id(self, asset_id: str) -> Asset:
        return self.assets[asset_id]

    def zone_by_id(self, zone_id: str) -> Zone:
        return self.zones[zone_id]

    def workers_in_zone(self, zone_id: str) -> list[Worker]:
        return [w for w in self.workers.values() if w.current_zone_id == zone_id]

    def permits_for_zone(self, zone_id: str) -> list[Permit]:
        return [p for p in self.permits.values() if p.zone_id == zone_id]
