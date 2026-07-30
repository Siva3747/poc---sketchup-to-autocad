import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.database import Base, Project
from backend.parser.skp_parser import generate_mock_floorplan
from backend.geometry.detector import detect_architectural_elements
from backend.geometry.processor import merge_colinear_segments
from backend.dxf_generator.generator import generate_dxf_file

# Set up SQLite memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_mock_generation():
    """Tests that our mock generation produces a valid, populated floorplan."""
    data = generate_mock_floorplan("test_model.skp")
    
    assert data["metadata"]["name"] == "test_model.skp"
    assert len(data["walls"]) > 0
    assert len(data["doors"]) > 0
    assert len(data["windows"]) > 0
    assert len(data["rooms"]) > 0
    
    # Verify coordinates are positive numbers or within standard ranges
    for w in data["walls"]:
        assert w["thickness"] in [150, 250]
        assert "start" in w and "end" in w
        assert w["start"]["x"] >= 0

def test_geometry_merging():
    """Tests the colinear line segment merging logic."""
    # Group of horizontal segments aligned at y=100
    segments = [
        ((0.0, 100.0), (100.0, 100.0)),
        ((110.0, 100.0), (200.0, 100.0)), # overlaps with gap of 10
        ((250.0, 100.0), (300.0, 100.0))  # overlap with gap of 50
    ]
    
    # Merge with tolerance 20
    merged = merge_colinear_segments(segments, tolerance=20.0)
    
    # First two should merge into ((0.0, 100.0), (200.0, 100.0)) because gap is 10 (<20)
    # Third one should NOT merge because gap from 200 to 250 is 50 (>20)
    assert len(merged) == 2
    
    # Sort by start point x to make verification order-independent
    merged = sorted(merged, key=lambda s: s[0][0])
    assert merged[0][0] == (0.0, 100.0)
    assert merged[0][1] == (200.0, 100.0)
    
    assert merged[1][0] == (250.0, 100.0)
    assert merged[1][1] == (300.0, 100.0)

def test_gap_based_door_detection():
    """Tests that a simple gap between colinear walls is inferred as a door opening."""
    raw = {
        "metadata": {"unit": "mm"},
        "walls": [
            {"id": "w1", "start": {"x": 0, "y": 0}, "end": {"x": 1000, "y": 0}, "thickness": 200, "height": 2800, "layer": "Walls"},
            {"id": "w2", "start": {"x": 1400, "y": 0}, "end": {"x": 3000, "y": 0}, "thickness": 200, "height": 2800, "layer": "Walls"}
        ],
        "doors": [],
        "windows": [],
        "rooms": []
    }
    result = detect_architectural_elements(raw)
    assert len(result["doors"]) == 1
    assert result["doors"][0]["width"] == 400
    assert result["doors"][0]["wallId"] in {"w1", "w2"}

def test_dxf_generation():
    """Tests that DXF file generation executes without throwing exceptions and saves the output."""
    data = generate_mock_floorplan("sample.skp")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        dxf_path = os.path.join(tmpdir, "output.dxf")
        saved_path = generate_dxf_file(data, dxf_path)
        
        assert os.path.exists(saved_path)
        assert os.path.getsize(saved_path) > 0

def test_database_crud(db_session):
    """Tests adding and updating a project in the database."""
    project = Project(
        id="test-uuid-123",
        filename="house.skp",
        status="PENDING"
    )
    db_session.add(project)
    db_session.commit()
    
    db_proj = db_session.query(Project).filter(Project.id == "test-uuid-123").first()
    assert db_proj is not None
    assert db_proj.filename == "house.skp"
    assert db_proj.status == "PENDING"
    
    db_proj.status = "COMPLETED"
    db_session.commit()
    
    db_proj_updated = db_session.query(Project).filter(Project.id == "test-uuid-123").first()
    assert db_proj_updated.status == "COMPLETED"

def test_dynamic_mock_generation():
    """Tests that mock generation outputs different, filename-dependent layouts."""
    data_res = generate_mock_floorplan("residential_villa.skp")
    data_off = generate_mock_floorplan("commercial_office.skp")
    
    # Verify name metadata
    assert data_res["metadata"]["name"] == "residential_villa.skp"
    assert data_off["metadata"]["name"] == "commercial_office.skp"
    
    # Verify that different seeds lead to different structures
    assert data_res != data_off
    
    # Check that office filenames yield office-like room names
    office_room_names = [r["name"] for r in data_off["rooms"]]
    assert any(any(k in name.lower() for k in ["office", "reception", "restroom", "pantry", "breakroom", "conference"]) for name in office_room_names)
    
    # Check that residential filenames yield residential-like room names
    res_room_names = [r["name"] for r in data_res["rooms"]]
    assert any(any(k in name.lower() for k in ["living", "bedroom", "kitchen", "bathroom"]) for name in res_room_names)
