from abc import ABC, abstractmethod
from typing import List
from app.models.base import Station, TrackSegment, Train, TrainSchedule
import os


class DataLoader(ABC):
    @abstractmethod
    def load_stations(self) -> List[Station]:
        pass

    @abstractmethod
    def load_segments(self) -> List[TrackSegment]:
        pass

    @abstractmethod
    def load_trains(self) -> List[Train]:
        pass

    @abstractmethod
    def load_schedules(self) -> List[TrainSchedule]:
        pass


class DataProvider:
    """Unified facade used by MCP servers and agents — never raw loader directly."""

    def __init__(self, loader: DataLoader):
        self._loader = loader
        self._stations = {s.id: s for s in loader.load_stations()}
        self._segments = {seg.id: seg for seg in loader.load_segments()}
        self._trains = {t.id: t for t in loader.load_trains()}
        self._schedules = {sch.train_id: sch for sch in loader.load_schedules()}

    def get_stations(self):
        return list(self._stations.values())

    def get_segments(self):
        return list(self._segments.values())

    def get_trains(self):
        return list(self._trains.values())

    def get_schedules(self):
        return list(self._schedules.values())

    def get_schedule(self, train_id: str):
        return self._schedules.get(train_id)

    def get_segment(self, segment_id: str):
        return self._segments.get(segment_id)

    def get_station(self, station_id: str):
        return self._stations.get(station_id)

    def get_route_graph(self) -> dict:
        """Return adjacency dict: station -> [(next_station, segment_id, travel_time_mins)]"""
        graph = {s: [] for s in self._stations}
        for seg in self._segments.values():
            graph.setdefault(seg.source_id, []).append((
                seg.target_id, seg.id, seg.travel_time_mins
            ))
            # Bidirectional
            graph.setdefault(seg.target_id, []).append((
                seg.source_id, seg.id, seg.travel_time_mins
            ))
        return graph

    def get_downstream_dependents(self, train_id: str) -> List[dict]:
        """Return trains sharing segments downstream of the given train."""
        sched = self._schedules.get(train_id)
        if not sched:
            return []
        deps = []
        for other_id, other_sched in self._schedules.items():
            if other_id == train_id:
                continue
            shared = set(sched.route) & set(other_sched.route)
            if shared:
                deps.append({"train_id": other_id, "shared_segments": list(shared)})
        return deps


def get_data_loader(mode: str = None) -> DataLoader:
    if mode is None:
        mode = os.environ.get("RAILMESH_DATA_MODE", "synthetic")

    if mode in ("synthetic", "SYNTHETIC"):
        from app.data.synthetic import SyntheticDataLoader
        seed = int(os.environ.get("RAILMESH_SEED", "42"))
        return SyntheticDataLoader(seed=seed)
    elif mode in ("static", "STATIC_REAL"):
        from app.data.static import StaticDataLoader
        return StaticDataLoader()
    else:
        raise ValueError(f"Unknown data mode: {mode}")


def get_data_provider(mode: str = None) -> DataProvider:
    return DataProvider(get_data_loader(mode))
