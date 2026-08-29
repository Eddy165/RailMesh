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

def get_data_loader(mode: str = None) -> DataLoader:
    if mode is None:
        mode = os.environ.get("RAILMESH_DATA_MODE", "synthetic")
        
    if mode == "synthetic":
        from app.data.synthetic import SyntheticDataLoader
        return SyntheticDataLoader()
    elif mode == "static":
        from app.data.static import StaticDataLoader
        return StaticDataLoader()
    else:
        raise ValueError(f"Unknown data mode: {mode}")
