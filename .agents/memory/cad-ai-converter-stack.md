---
name: CAD AI Converter stack
description: Key runtime quirks for the CAD AI Converter project (FastAPI + React + Three.js on Replit)
---

# CAD AI Converter — Stack Notes

## Two-workflow setup
- Backend: `cd backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload` (console, port 8000)
- Frontend: `cd frontend && npm run dev` (webview, port 5000)
- Vite proxies `/api → localhost:8000` — never hardcode the backend URL in frontend code

## Three.js install
- `@react-three/fiber` v9 pulls in Expo peer deps and fails with plain npm install
- **Fix:** pin to v8 and use `--legacy-peer-deps`: `npm install three@0.169 @react-three/fiber@8.17 @react-three/drei@9.122 @types/three@0.169 --legacy-peer-deps`
- Must run inside `frontend/` directory (not the root)

## Permission issue on fresh workflow start
- After `npm install` in frontend, `.bin/` executables sometimes lose execute bit
- **Fix:** `chmod -R +x frontend/node_modules/.bin/` before restarting the workflow

## AI detection engine
- Lives in `backend/ai/detector.py`; uses `HeuristicAIModel` by default
- Plug-and-play: implement `detect(canonical_json, features, threshold)` on any class and pass it to `run_ai_detection()`
- `openskp` is not available on Replit — binary SKP falls back to procedural mock generator in `backend/parser/skp_parser.py`

## ODA File Converter
- Not available on Replit — DWG export silently falls back to DXF (graceful, logged as warning)

## Database
- SQLite at `backend/projects.db`; `DATABASE_URL` env var switches to PostgreSQL transparently

**Why:** These were discovered during initial setup and are not derivable from reading the code alone.
