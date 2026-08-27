# RoadBuddy
## Iteration 1 - Know the trip before you take it
- Epic 1 Pre-Journey Risk Check
- Epic 2 Risk Radar

## Local Run (Windows PowerShell)

### 1. Prerequisites and environment files

- Install Python 3.12 and Node.js 20.19 or later.
- Put the shared backend environment file at `RoadBuddy/.env`.
- Do not commit `.env` or `frontend/.env.local`.
- To enable the Risk Radar map, create `frontend/.env.local`:

```env
VITE_API_BASE_URL=/api
VITE_MAPBOX_TOKEN=replace_with_the_public_mapbox_token
```

### 2. Start the backend

Open PowerShell in the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Verify the backend at <http://localhost:8000/api/health>.

If the configured PostgreSQL/PostGIS database is not reachable, set `USE_MOCK_DATA=true` in the root `.env` for local testing, then restart the backend.

### 3. Start the frontend

Open a second PowerShell in the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Keep both terminals running. Press `Ctrl+C` in each terminal to stop the services.
