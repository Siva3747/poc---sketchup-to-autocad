import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the repository root is on sys.path so 'backend' imports work when running
# this file directly as a script from the repo root.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.utils.config import settings
from backend.utils.logger import logger
from backend.models.database import init_db
from backend.api.routes import router as api_router

# Initialize database tables
logger.info("Initializing database...")
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-ready API to parse SketchUp models, detect floor plans, and generate AutoCAD DXF/DWG files.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Register API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {
        "app": settings.PROJECT_NAME,
        "status": "healthy",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    logger.info(f"Starting uvicorn server on {settings.HOST}:{settings.PORT}")
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
