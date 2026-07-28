# SketchUp to AutoCAD DXF/DWG Pipeline & 2D Floor Plan Editor

A production-ready web application built to convert SketchUp (`.skp`) files into AutoCAD DXF/DWG formats while preserving architectural tag structures. Features an interactive 2D SVG/Canvas vector editor in-browser using React, TypeScript, and Konva.js.

---

## Technical Architecture

- **Frontend**: React, TypeScript, Tailwind CSS, Zustand, Konva.js (HTML5 Canvas rendering engine supporting coordinate grids, endpoint snapping, and transformations).
- **Backend**: Python 3, FastAPI, SQLAlchemy (SQLite/PostgreSQL database), Shapely, NumPy, ezdxf (CAD generator), openskp (direct binary model parsing).
- **DWG Conversion**: Integrated CLI adapter for the **ODA File Converter** (Open Design Alliance) wrapper.

---

## Project Structure

```
d:\poc3\
├── backend\
│   ├── api\                  # FastAPI routes, schemas and validators
│   ├── parser\               # openskp binary model parser & plugins
│   ├── geometry\             # Shapely/NumPy based room/wall detectors
│   ├── json_builder\         # Schema standardizer
│   ├── dxf_generator\        # CAD DXF generator using ezdxf
│   ├── dwg_converter\        # ODA File Converter CLI adapter
│   ├── services\             # Project coordination layer
│   ├── models\               # SQLAlchemy DB models
│   ├── tests\                # PyTest suite
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile            # Container definition
├── frontend\
│   ├── src\                  # React components, stores and styles
│   ├── package.json          # Node configurations
│   ├── tsconfig.json         # TypeScript configurations
│   ├── tailwind.config.js    # Tailwind layout overrides
│   ├── vite.config.ts        # Vite dev server configurations
│   └── Dockerfile            # Nginx deployment server
├── shared\
│   └── schemas\              # Target JSON Schema definitions
├── docker-compose.yml        # Multi-container conductor
├── sketchup_json_exporter.rb # Ruby extension script for SketchUp
├── sample_floorplan.skp      # Signature-compliant verification file
└── sample_floorplan.json     # Standardized JSON representation
```

---

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (v18 or higher)
- [Python](https://www.python.org/) (v3.10 or higher)
- [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) (Optional, required for converting DXF to DWG).

---

### Installation & Run (Local Development)

#### 1. Start Python Backend
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start FastAPI server:
   ```bash
   python main.py
   ```
   The backend API will run at `http://localhost:8000`. Swagger documentation is available at `http://localhost:8000/docs`.

#### 2. Start React Frontend
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install packages:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

---

### Docker Deployment

To launch the entire stack in containers (with PostgreSQL database support):

```bash
docker-compose up --build
```

- **Frontend**: Access at `http://localhost:3000`
- **Backend API**: Access at `http://localhost:8000`

---

### Render Cloud Deployment

The repository includes a [render.yaml](file:///d:/poc3/render.yaml) blueprint config that deploys the React frontend, FastAPI backend, and PostgreSQL database with a single click:

1. Push the project to your GitHub account (completed!).
2. Log into the **[Render Dashboard](https://dashboard.render.com)**.
3. Click **New +** and select **Blueprint**.
4. Link this GitHub repository.
5. Render will automatically detect the services in `render.yaml` and provision the frontend, backend, and database automatically.

---

## ODA File Converter Installation

To support **DWG generation**:
1. Download and install the **ODA File Converter** for your OS from [Open Design Alliance](https://www.opendesign.com/guestfiles/oda_file_converter).
2. Configure the location of the executable in your system environment variables or in the `backend/utils/config.py` file:
   - **Windows Default**: `C:\Program Files\ODA\ODAFileConverter.exe`
   - **Linux Default**: `/usr/bin/ODAFileConverter`
3. If not installed, the server will log a warning and return the standard DXF deliverable (graceful fallback).

---

## SketchUp Integration

While the python backend includes a **direct binary parser** (`openskp`) and a **Mock Generator** for generic file formats, SketchUp models containing complex component hierarchies can be exported with 100% geometry precision using our Ruby Plugin:

1. Copy the `sketchup_json_exporter.rb` script from the root of this project.
2. In SketchUp, open the **Ruby Console** (`Window` ➔ `Ruby Console`).
3. Paste the script or load it via `load 'path/to/sketchup_json_exporter.rb'`.
4. Run `SketchUpFloorPlanExporter.export_model` or select **Export Floor Plan JSON** from the Extensions/Plugins menu.
5. Upload the generated `_exported.json` file in our web console to visualize, inspect, edit, and export CAD drawings instantly!
