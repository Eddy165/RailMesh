import csv
import os
from typing import List
from datetime import datetime
from app.models.base import Station, TrackSegment, Train, TrainSchedule, PriorityClass, ScheduleEntry
from app.data.manager import DataLoader

class StaticDataLoader(DataLoader):
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.environ.get("RAILMESH_DATA_DIR", "data/static")

    def _read_csv(self, filename: str) -> List[dict]:
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            return []
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def load_stations(self) -> List[Station]:
        data = self._read_csv("stations.csv")
        return [Station(id=row["id"], name=row["name"], capacity=int(row.get("capacity", 2))) for row in data]

    def load_segments(self) -> List[TrackSegment]:
        data = self._read_csv("segments.csv")
        return [
            TrackSegment(
                id=row["id"],
                source_id=row["source_id"],
                target_id=row["target_id"],
                length_km=float(row["length_km"]),
                capacity=int(row.get("capacity", 1)),
                travel_time_mins=int(row["travel_time_mins"])
            ) for row in data
        ]

    def load_trains(self) -> List[Train]:
        data = self._read_csv("trains.csv")
        return [
            Train(
                id=row["id"],
                name=row["name"],
                priority_class=PriorityClass(row["priority_class"])
            ) for row in data
        ]

    def load_schedules(self) -> List[TrainSchedule]:
        data = self._read_csv("schedules.csv")
        schedules_dict = {}
        
        for row in data:
            train_id = row["train_id"]
            if train_id not in schedules_dict:
                schedules_dict[train_id] = {
                    "train_id": train_id,
                    "route": [],
                    "entries": []
                }
            
            schedules_dict[train_id]["route"].append(row["segment_id"])
            schedules_dict[train_id]["entries"].append(
                ScheduleEntry(
                    segment_id=row["segment_id"],
                    arrival_time=datetime.fromisoformat(row["arrival_time"]),
                    departure_time=datetime.fromisoformat(row["departure_time"])
                )
            )
            
        return [TrainSchedule(**v) for v in schedules_dict.values()]
