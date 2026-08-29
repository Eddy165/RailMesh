"""
RailMesh Cascade Propagation Engine
Deterministic, inspectable function — NOT an LLM call.
Inputs: DisruptionEvent + current network state (store)
Outputs: ordered list of CascadeImpact objects

Models:
- Platform contention (same station, overlapping times)
- Single-track segment blocking (shared segment, capacity=1)
- Connecting-service dependencies (sequential route segments)
"""
from typing import List, Dict, Set, Optional
from app.models.base import DisruptionEvent, CascadeImpact, TrainSchedule
from app.store import InMemoryStore
import networkx as nx


def propagate(event: DisruptionEvent, network_store: InMemoryStore) -> List[CascadeImpact]:
    """
    Main entry point.
    Given a disruption event and current network state, return ordered cascade impacts.
    """
    impacts: List[CascadeImpact] = []
    visited_trains: Set[str] = set()

    affected = event.affected_station_or_segment
    delay_mins = event.delay_minutes

    # Build a graph of segment → trains
    segment_to_trains: Dict[str, List[str]] = {}
    for train_id, sched in network_store.schedules.items():
        for seg_id in sched.route:
            segment_to_trains.setdefault(seg_id, []).append(train_id)

    # Build station → trains
    station_to_trains: Dict[str, List[str]] = {}
    for seg in network_store.segments.values():
        for station_id in [seg.source_id, seg.target_id]:
            station_to_trains.setdefault(station_id, [])
            for train_id, sched in network_store.schedules.items():
                if seg.id in sched.route and train_id not in station_to_trains[station_id]:
                    station_to_trains[station_id].append(train_id)

    # 1. Direct segment impacts (single-track blocking)
    if affected in network_store.segments:
        seg = network_store.segments[affected]
        direct_trains = segment_to_trains.get(affected, [])
        for train_id in direct_trains:
            if train_id not in visited_trains:
                visited_trains.add(train_id)
                impacts.append(CascadeImpact(
                    train_id=train_id,
                    affected_segment_or_station=affected,
                    estimated_delay_minutes=delay_mins,
                    impact_type="segment_blocked",
                    confidence=0.95,
                    hop_distance=1,
                ))

    # 2. Direct station impacts (platform contention)
    if affected in network_store.stations:
        platform_trains = station_to_trains.get(affected, [])
        for train_id in platform_trains:
            if train_id not in visited_trains:
                visited_trains.add(train_id)
                impacts.append(CascadeImpact(
                    train_id=train_id,
                    affected_segment_or_station=affected,
                    estimated_delay_minutes=delay_mins,
                    impact_type="platform_conflict",
                    confidence=0.85,
                    hop_distance=1,
                ))

    # 3. Connecting-service cascade (hop propagation using NetworkX)
    G = nx.DiGraph()
    for seg in network_store.segments.values():
        G.add_edge(seg.source_id, seg.target_id, segment_id=seg.id, travel_time=seg.travel_time_mins)
        G.add_edge(seg.target_id, seg.source_id, segment_id=seg.id, travel_time=seg.travel_time_mins)

    # Find stations reachable from the affected point within 2 hops
    hop_stations = set()
    if affected in G:
        for hop1 in G.successors(affected):
            hop_stations.add((hop1, 1))
            for hop2 in G.successors(hop1):
                if hop2 != affected:
                    hop_stations.add((hop2, 2))
    elif affected in network_store.segments:
        seg = network_store.segments[affected]
        for station in [seg.source_id, seg.target_id]:
            if station in G:
                for hop1 in G.successors(station):
                    hop_stations.add((hop1, 1))
                    for hop2 in G.successors(hop1):
                        if hop2 != station:
                            hop_stations.add((hop2, 2))

    for (station, hop_dist) in hop_stations:
        downstream_trains = station_to_trains.get(station, [])
        propagated_delay = max(1, int(delay_mins * (0.7 ** hop_dist)))  # decay per hop
        confidence = max(0.3, 0.9 - 0.2 * hop_dist)

        for train_id in downstream_trains:
            if train_id not in visited_trains:
                visited_trains.add(train_id)
                impacts.append(CascadeImpact(
                    train_id=train_id,
                    affected_segment_or_station=station,
                    estimated_delay_minutes=propagated_delay,
                    impact_type="connecting_dependency",
                    confidence=confidence,
                    hop_distance=hop_dist,
                ))

    # Sort by hop_distance then confidence (most certain first)
    impacts.sort(key=lambda x: (x.hop_distance, -x.confidence))
    return impacts


def get_affected_trains(event: DisruptionEvent, network_store: InMemoryStore) -> List[str]:
    """Convenience wrapper — returns just the list of affected train IDs."""
    impacts = propagate(event, network_store)
    return [imp.train_id for imp in impacts]
