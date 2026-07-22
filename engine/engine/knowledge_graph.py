"""Plant knowledge graph: the entities a control room actually reasons
about (workers, zones, permits, assets, the specific sensor channels
monitoring them, maintenance tasks) and the relationships between them.

For each of the 3 compound incidents, `compute_hazardous_path` walks the
real graph plus that event's real data (which channels moved, which
worker was where, which maintenance task was overdue) to produce an
ordered path and a templated one-sentence explanation. Nothing here is
hand-written per incident — the sentence is assembled from the same
fields already in the exported event dict and timeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1]
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import networkx as nx
import pandas as pd

# Which raw channels a given asset is monitored by — the same physical
# mapping used for Twin.tsx's live readouts and risk_agent's contributor
# attribution, so the graph agrees with the rest of the product.
ASSET_CHANNELS = {
    "TANK-01": ["pressure_bar", "gas_ppm", "temp_tank_c"],
    "PIPE-01": ["pressure_bar", "temp_tank_c"],
    "VALVE-01": ["relief_capacity_pct"],
    "COMP-01": ["temp_compressor_c", "vibration_mms"],
    "BOIL-01": [],
}

CHANNEL_LABELS = {
    "pressure_bar": "Pressure",
    "gas_ppm": "Gas Concentration",
    "temp_tank_c": "Tank Temperature",
    "temp_compressor_c": "Compressor Temperature",
    "vibration_mms": "Vibration",
    "relief_capacity_pct": "Relief Capacity",
    "wind_speed_kmh": "Wind Speed",
}

# Physical plant topology, independent of any single incident.
TOPOLOGY_EDGES = [
    ("VALVE-01", "TANK-01", "relieves"),
    ("TANK-01", "PIPE-01", "feeds"),
    ("PIPE-01", "COMP-01", "feeds"),
]


def build_plant_graph(plant) -> nx.DiGraph:
    """The static graph: every worker, zone, permit, asset, channel, and
    maintenance task, plus how they relate. Built fresh from the Plant
    object each run — no cached/hand-authored structure.
    """
    g = nx.DiGraph()

    for zone in plant.zones.values():
        g.add_node(zone.id, kind="zone", label=zone.name, zone_type=zone.type.value)

    for worker in plant.workers.values():
        node_id = f"worker:{worker.id}"
        g.add_node(node_id, kind="worker", label=worker.name, role=worker.role, shift=worker.shift.value, worker_id=worker.id)
        g.add_edge(node_id, worker.current_zone_id, relation="in")

    for permit in plant.permits.values():
        node_id = f"permit:{permit.id}"
        g.add_node(node_id, kind="permit", label=f"{permit.id} ({permit.type.value})", permit_id=permit.id, status=permit.status.value)
        g.add_edge(permit.zone_id, node_id, relation="governed_by")
        g.add_edge(node_id, f"worker:{permit.worker_id}", relation="held_by")

    for asset in plant.assets.values():
        node_id = f"asset:{asset.id}"
        g.add_node(node_id, kind="asset", label=asset.name, asset_type=asset.type.value, asset_id=asset.id)
        g.add_edge(asset.zone_id, node_id, relation="contains")
        for channel in ASSET_CHANNELS.get(asset.id, []):
            channel_node = f"channel:{channel}@{asset.id}"
            g.add_node(channel_node, kind="channel", label=f"{CHANNEL_LABELS.get(channel, channel)} @ {asset.id}", channel=channel, asset_id=asset.id)
            g.add_edge(node_id, channel_node, relation="monitored_by")

    for task in plant.maintenance_tasks:
        node_id = f"task:{task.id}"
        g.add_node(node_id, kind="maintenance_task", label=f"{task.id}: {task.task_type}", status=task.status.value)
        g.add_edge(f"asset:{task.asset_id}", node_id, relation="scheduled_task")

    for src, dst, relation in TOPOLOGY_EDGES:
        g.add_edge(f"asset:{src}", f"asset:{dst}", relation=relation)

    return g


def _worker_name(plant, worker_id: str) -> str:
    return plant.workers[worker_id].name if worker_id in plant.workers else worker_id


def _permit_covering(plant, zone_id: str) -> "object | None":
    for permit in plant.permits.values():
        if permit.zone_id == zone_id:
            return permit
    return None


def _direction(df: pd.DataFrame, channel: str, start_idx: int, end_idx: int, lookback: int = 20) -> str:
    """Which way this channel actually moved during the event, judged by
    its biggest deviation from the immediate pre-event baseline — not by
    comparing window-start to window-end, which is wrong whenever the
    channel rises then partially recovers before the window closes (true
    of all three archetypes' trapezoid-shaped ramps).
    """
    baseline_start = max(0, start_idx - lookback)
    baseline = float(df[channel].iloc[baseline_start:start_idx].mean()) if start_idx > baseline_start else float(df[channel].iloc[start_idx])
    window = df[channel].iloc[start_idx:end_idx + 1]
    high_dev = float(window.max()) - baseline
    low_dev = baseline - float(window.min())
    return "rising" if high_dev >= low_dev else "falling"


def compute_hazardous_path(graph: nx.DiGraph, event: dict, df: pd.DataFrame, plant) -> dict:
    """Walk the graph nodes this specific event actually touches (its own
    asset_ids, zone_id, and — where present — worker_intrusion), and
    assemble a one-sentence explanation entirely from real fields on the
    event dict, the timeline, and the graph.
    """
    zone_id = event["zone_id"]
    zone = plant.zones[zone_id]
    path_nodes = [zone_id]
    clauses = []

    intrusion = event.get("worker_intrusion")
    if intrusion:
        worker_node = f"worker:{intrusion['worker_id']}"
        path_nodes.append(worker_node)
        name = _worker_name(plant, intrusion["worker_id"])
        covering_permit = _permit_covering(plant, zone_id)
        if covering_permit and covering_permit.worker_id != intrusion["worker_id"]:
            permit_node = f"permit:{covering_permit.id}"
            path_nodes.append(permit_node)
            clauses.append(
                f"{name} enters {zone.name} ({zone_id}) — {zone_id}'s standing entry permit "
                f"{covering_permit.id} is held by {_worker_name(plant, covering_permit.worker_id)}, not {name}"
            )
        else:
            clauses.append(f"{name} enters {zone.name} ({zone_id}) without an active entry permit")

    for asset_id in event["asset_ids"]:
        asset_node = f"asset:{asset_id}"
        path_nodes.append(asset_node)
        asset_clauses = []
        for channel in ASSET_CHANNELS.get(asset_id, []):
            if channel not in event["affected_channels"]:
                continue
            channel_node = f"channel:{channel}@{asset_id}"
            path_nodes.append(channel_node)
            direction = _direction(df, channel, event["start_idx"], event["end_idx"])
            asset_clauses.append(f"{CHANNEL_LABELS.get(channel, channel)} {direction}")
        if asset_clauses:
            clauses.append(f"{asset_id} shows {', '.join(asset_clauses)}")

        for task in plant.maintenance_tasks:
            if task.asset_id == asset_id and task.status.value in ("overdue", "in_progress"):
                task_node = f"task:{task.id}"
                path_nodes.append(task_node)
                clauses.append(f"{task.id} ({task.task_type}) is {task.status.value.replace('_', ' ')}")

    if "hot_work_permit_active" in event["affected_channels"]:
        clauses.append("a hot-work permit is active in the same restricted zone")

    if "wind_speed_kmh" in event["affected_channels"]:
        wind_node = f"channel:wind_speed_kmh@{zone_id}"
        path_nodes.append(wind_node)
        clauses.append("wind has dropped to near-calm, stalling dispersion")

    # de-duplicate while preserving order (a node can legitimately recur,
    # e.g. an asset referenced by both a channel and a maintenance clause)
    seen = set()
    ordered_path = [n for n in path_nodes if not (n in seen or seen.add(n))]

    sentence = "; ".join(clauses) + "." if clauses else f"Compound risk building in {zone.name} ({zone_id})."
    sentence = sentence[0].upper() + sentence[1:]

    return {
        "event_id": event["id"],
        "path_nodes": ordered_path,
        "sentence": sentence,
        "clauses": clauses,
    }


def export_graph_payload(plant, events: list, df: pd.DataFrame) -> dict:
    graph = build_plant_graph(plant)

    nodes = [
        {"id": node_id, **{k: v for k, v in data.items()}}
        for node_id, data in graph.nodes(data=True)
    ]
    edges = [
        {"source": u, "target": v, "relation": data.get("relation", "")}
        for u, v, data in graph.edges(data=True)
    ]
    paths = [compute_hazardous_path(graph, event, df, plant) for event in events]

    return {"nodes": nodes, "edges": edges, "paths": paths}


if __name__ == "__main__":
    from simulator import generate_scenario

    scenario_df, scenario_plant, scenario_events = generate_scenario()
    payload = export_graph_payload(scenario_plant, scenario_events, scenario_df)
    print(f"Graph: {len(payload['nodes'])} nodes, {len(payload['edges'])} edges")
    for path in payload["paths"]:
        print(f"\n{path['event_id']}")
        print(f"  path: {' -> '.join(path['path_nodes'])}")
        print(f"  sentence: {path['sentence']}")
