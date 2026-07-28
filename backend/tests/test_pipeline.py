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
