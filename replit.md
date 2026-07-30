# CAD AI Converter

A production-ready full-stack web application that converts SketchUp (.skp), AutoCAD DXF/DWG, and structured 3D JSON into interchangeable formats while providing an AI-powered interactive 2D/3D browser viewer.

## Architecture

- **Frontend**: React 18 + TypeScript + Vite (port 5000), Tailwind CSS, Konva.js (2D), Three.js + React Three Fiber (3D), Zustand
- **Backend**: Python 3.13 + FastAPI (port 8000), SQLAlchemy + SQLite, ezdxf, Shapely, NumPy

## Running the App

Two workflows must both be running:

### Backend API (port 8000)
```
cd backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (port 5000 → webview)
```
cd frontend && npm run dev
```

The Vite dev server proxies all `/api` requests to the backend at `localhost:8000`.

## Key Features

- **Multi-format upload**: SKP, DXF, DWG, JSON
- **AI Architectural Detection**: Confidence-scored classification of walls, doors, windows, rooms — modular design allows swapping in PyTorch/ONNX models
- **2D Floor Plan Viewer**: Konva.js canvas with snap-to-grid, wall drawing, door/window placement
- **3D Viewer**: Three.js + React Three Fiber with orbit controls
- **AI Review Mode**: Accept/reject/reclassify AI detections with corrections saved back to canonical JSON
- **Export**: DXF, DWG (via ODA converter if installed), Canonical JSON, SKP Ruby reconstruction script

## Conversion Matrix

| Input → | JSON | DXF | DWG | SKP Script |
|---------|------|-----|-----|------------|
| SKP     | ✓    | ✓   | ✓*  | ✓          |
| DXF     | ✓    | ✓   | ✓*  | ✓          |
| DWG     | ✓    | ✓   | ✓*  | ✓          |
| JSON    | ✓    | ✓   | ✓*  | ✓          |

\* DWG requires the ODA File Converter installed at `/usr/bin/ODAFileConverter` (graceful fallback to DXF if absent)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/upload` | Upload SKP/DXF/DWG/JSON, run full pipeline |
| POST | `/api/v1/convert` | Upload + get specific output format |
| POST | `/api/v1/detect` | Run/re-run AI detection on a project |
| POST | `/api/v1/detect/correct` | Apply user corrections to AI detections |
| GET | `/api/v1/viewer/{id}` | Get canonical + AI JSON for viewer |
| PUT | `/api/v1/viewer/{id}` | Save edits, regenerate CAD files |
| GET | `/api/v1/download/{id}?format=json\|dxf\|dwg\|skp` | Download output file |
| POST | `/api/v1/export/dxf\|dwg\|skp` | Explicit re-export |
| GET | `/api/v1/projects` | List all projects |

## Folder Structure

```
backend/
  ai/          # AI detection engine (modular, swap in PyTorch/ONNX)
  api/         # FastAPI routes + Pydantic schemas
  dwg_converter/  # ODA CLI adapter
  dxf_generator/  # ezdxf CAD generator
  exporters/   # SKP Ruby script exporter
  geometry/    # Shapely/NumPy element detection
  json_builder/   # Canonical JSON validator
  models/      # SQLAlchemy DB models
  parser/      # SKP parser (openskp + mock)
  parsers/     # DXF input parser
  services/    # Pipeline orchestration
  utils/       # Config + logger
  uploads/     # Generated files (DB, DXF, DWG, JSON, .rb scripts)

frontend/
  src/
    components/  # Toolbar, LayerPanel, EditorSidebar, AIReviewPanel, ViewToggle
    services/    # API client
    store/       # Zustand viewer store
    viewer/      # FloorPlanViewer (2D Konva), Viewer3D (Three.js)
```

## Notes

- `openskp` is not available on Replit; binary SKP files fall back to a procedural mock floor plan generator. Use the SketchUp Ruby Plugin Exporter (downloadable from the editor sidebar) for real SKP geometry.
- ODA File Converter is not available on Replit; DWG export falls back to DXF gracefully.
- The AI detection engine (`backend/ai/detector.py`) uses geometry heuristics by default. The architecture is plug-and-play: replace `HeuristicAIModel` with a PyTorch/ONNX model by implementing the same `detect()` interface.

## User Preferences

- Incremental, production-ready builds — each feature functional before moving to the next
- Modular architecture following SOLID principles
