import pytest
import os
from app.data.manager import get_data_loader
from app.data.synthetic import SyntheticDataLoader
from app.data.static import StaticDataLoader
from app.models.base import Station, TrackSegment, Train, TrainSchedule

def test_synthetic_loader():
    loader = get_data_loader("synthetic")
    assert isinstance(loader, SyntheticDataLoader)
    
    stations = loader.load_stations()
    assert len(stations) > 0
    assert isinstance(stations[0], Station)
    
    segments = loader.load_segments()
    assert len(segments) > 0
    assert isinstance(segments[0], TrackSegment)
    
    trains = loader.load_trains()
    assert len(trains) > 0
    assert isinstance(trains[0], Train)
    
    schedules = loader.load_schedules()
    assert len(schedules) > 0
    assert isinstance(schedules[0], TrainSchedule)

def test_static_loader(monkeypatch):
    test_dir = os.path.join(os.path.dirname(__file__), "data", "static")
    monkeypatch.setenv("RAILMESH_DATA_DIR", test_dir)
    
    loader = get_data_loader("static")
    assert isinstance(loader, StaticDataLoader)
    
    stations = loader.load_stations()
    assert len(stations) == 2
    assert stations[0].id == "NDLS"
    assert isinstance(stations[0], Station)
    
    segments = loader.load_segments()
    assert len(segments) == 1
    assert segments[0].source_id == "NDLS"
    assert isinstance(segments[0], TrackSegment)
    
    trains = loader.load_trains()
    assert len(trains) == 1
    assert trains[0].name == "Mumbai Rajdhani"
    assert isinstance(trains[0], Train)
    
    schedules = loader.load_schedules()
    assert len(schedules) == 1
    assert schedules[0].train_id == "T12952"
    assert isinstance(schedules[0], TrainSchedule)
    assert len(schedules[0].entries) == 1

def test_invalid_mode():
    with pytest.raises(ValueError):
        get_data_loader("invalid")
