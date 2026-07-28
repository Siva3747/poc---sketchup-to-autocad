import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SketchUp CAD Converter API"
    API_V1_STR: str = "/api/v1"
    
    # Storage
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    
    # Database
    # Standard DB URL (supports SQLite locally, but can be overridden with Postgres URL in production)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./projects.db")
    
    # ODA File Converter CLI path (configured via environment or searched automatically)
    ODA_CONVERTER_PATH: str = os.getenv(
        "ODA_CONVERTER_PATH", 
        r"C:\Program Files\ODA\ODAFileConverter.exe" if os.name == "nt" else "/usr/bin/ODAFileConverter"
    )
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    class Config:
        case_sensitive = True

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
