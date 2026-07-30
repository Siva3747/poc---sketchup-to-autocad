import datetime
import uuid
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.utils.config import settings

Base = declarative_base()
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    source_format = Column(String, default="skp")   # skp | dxf | dwg | json
    status = Column(String, default="PENDING")       # PENDING | UPLOADED | PARSING | EXTRACTING | DETECTING | COMPLETED | FAILED
    error_message = Column(Text, nullable=True)

    # File storage paths
    original_file_path = Column(String, nullable=True)
    json_path = Column(String, nullable=True)       # Canonical JSON
    ai_json_path = Column(String, nullable=True)    # AI-enhanced canonical JSON
    dxf_path = Column(String, nullable=True)
    dwg_path = Column(String, nullable=True)
    skp_script_path = Column(String, nullable=True) # Ruby reconstruction script

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
