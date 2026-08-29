import random
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from app.models.base import (
    Station, TrackSegment, Train, TrainSchedule,
    PriorityClass, ScheduleEntry, DisruptionEvent
)
from app.data.manager import DataLoader


SCENARIO_EVENTS = {
    "scenario_1_two_train_conflict": {
        "affected_station_or_segment": "NGP_MMCT",
        "delay_minutes": 45,
        "cause": "Signal failure at Nagpur causes platform conflict between T12952 and T12810",
        "scenario_tag": "scenario_1",
    },
    "scenario_2_three_hop_cascade": {
        "affected_station_or_segment": "NDLS",
        "delay_minutes": 60,
        "cause": "Track obstruction at NDLS cascades through NGP to MMCT",
        "scenario_tag": "scenario_2",
    },
    "scenario_3_deadlock": {
        "affected_station_or_segment": "NGP_MMCT",
        "delay_minutes": 90,
        "cause": "Complete block on NGP-MMCT segment, both express trains require same single-line slot",
        "scenario_tag": "scenario_3",
    },
    "scenario_4_agent_dropout": {
        "affected_station_or_segment": "HWH_NGP",
        "delay_minutes": 30,
        "cause": "Power failure on HWH-NGP segment; T12810 comms partially degraded",
        "scenario_tag": "scenario_4",
    },
}


class SyntheticDataLoader(DataLoader):
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._rng = random.Random(seed)

        self.stations_data = [
            ("NDLS", "New Delhi", 16),
            ("MMCT", "Mumbai Central", 9),
            ("HWH", "Howrah", 23),
            ("MAS", "Chennai Central", 15),
            ("BZA", "Vijayawada", 10),
            ("NGP", "Nagpur", 8),
        ]

        self.segments_data = [
            ("NDLS_NGP", "NDLS", "NGP", 1094.0, 1, 840),
            ("NGP_MMCT", "NGP", "MMCT", 837.0, 1, 720),
            ("NGP_BZA", "NGP", "BZA", 571.0, 1, 480),
            ("HWH_NGP", "HWH", "NGP", 1131.0, 1, 900),
            ("BZA_MAS", "BZA", "MAS", 431.0, 1, 360),
        ]

        self.trains_data = [
            ("T12952", "Mumbai Rajdhani", PriorityClass.EXPRESS),
            ("T12810", "Howrah Mail", PriorityClass.EXPRESS),
            ("T11040", "Maharashtra Express", PriorityClass.PASSENGER),
            ("F8492", "Coal Freight HWH-NGP", PriorityClass.FREIGHT),
        ]

    def load_stations(self) -> List[Station]:
        return [Station(id=sid, name=name, capacity=cap) for sid, name, cap in self.stations_data]

    def load_segments(self) -> List[TrackSegment]:
        return [
            TrackSegment(
                id=seg_id, source_id=src, target_id=tgt,
                length_km=length, capacity=cap, travel_time_mins=t
            )
            for seg_id, src, tgt, length, cap, t in self.segments_data
        ]

    def load_trains(self) -> List[Train]:
        return [
            Train(id=tid, name=name, priority_class=p_class)
            for tid, name, p_class in self.trains_data
        ]

    def load_schedules(self) -> List[TrainSchedule]:
        now = datetime.now(timezone.utc)
        schedules = []

        # T12952: Mumbai Rajdhani — NDLS → NGP → MMCT
        t1 = now + timedelta(hours=1)
        t2 = t1 + timedelta(minutes=840)
        t3 = t2 + timedelta(minutes=720)
        schedules.append(TrainSchedule(
            train_id="T12952",
            route=["NDLS_NGP", "NGP_MMCT"],
            entries=[
                ScheduleEntry(segment_id="NDLS_NGP", arrival_time=t1, departure_time=t2),
                ScheduleEntry(segment_id="NGP_MMCT", arrival_time=t2, departure_time=t3),
            ],
        ))

        # T12810: Howrah Mail — HWH → NGP → MMCT (overlaps NGP_MMCT with T12952)
        t1_h = now + timedelta(hours=2)
        t2_h = t1_h + timedelta(minutes=900)
        t3_h = t2_h + timedelta(minutes=720)
        schedules.append(TrainSchedule(
            train_id="T12810",
            route=["HWH_NGP", "NGP_MMCT"],
            entries=[
                ScheduleEntry(segment_id="HWH_NGP", arrival_time=t1_h, departure_time=t2_h),
                ScheduleEntry(segment_id="NGP_MMCT", arrival_time=t2_h, departure_time=t3_h),
            ],
        ))

        # T11040: Maharashtra Express — NDLS → NGP → BZA → MAS
        t1_m = now + timedelta(hours=3)
        t2_m = t1_m + timedelta(minutes=840)
        t3_m = t2_m + timedelta(minutes=480)
        t4_m = t3_m + timedelta(minutes=360)
        schedules.append(TrainSchedule(
            train_id="T11040",
            route=["NDLS_NGP", "NGP_BZA", "BZA_MAS"],
            entries=[
                ScheduleEntry(segment_id="NDLS_NGP", arrival_time=t1_m, departure_time=t2_m),
                ScheduleEntry(segment_id="NGP_BZA", arrival_time=t2_m, departure_time=t3_m),
                ScheduleEntry(segment_id="BZA_MAS", arrival_time=t3_m, departure_time=t4_m),
            ],
        ))

        # F8492: Coal Freight — HWH → NGP (slowest, shares HWH_NGP with T12810)
        t1_f = now + timedelta(hours=4)
        t2_f = t1_f + timedelta(minutes=1000)
        schedules.append(TrainSchedule(
            train_id="F8492",
            route=["HWH_NGP"],
            entries=[
                ScheduleEntry(segment_id="HWH_NGP", arrival_time=t1_f, departure_time=t2_f),
            ],
        ))

        return schedules

    def generate_disruption_event(self, scenario: str) -> DisruptionEvent:
        """Generate a scripted disruption event for the given scenario key."""
        if scenario not in SCENARIO_EVENTS:
            raise ValueError(f"Unknown scenario: {scenario}. Valid: {list(SCENARIO_EVENTS.keys())}")
        ev = SCENARIO_EVENTS[scenario].copy()
        return DisruptionEvent(**ev)
