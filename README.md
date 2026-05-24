# driver-map-app

Driving enthusiast route sharing — create scenic and fun routes on a map, share them, and discover routes from the community.

**Product plan:** [docs/PLAN.md](docs/PLAN.md)  
**Phase 2 (recording):** [docs/PHASE2_RECORDING.md](docs/PHASE2_RECORDING.md)

## Stack

- **Backend:** Python, FastAPI, PostgreSQL + PostGIS
- **Frontend:** React, TypeScript, Vite, Google Maps JavaScript API
- **Maps proxy:** Directions, Places, Geocoding via server (API key never exposed for Directions)

## Quick start

### 1. Environment

```bash
cp .env.example .env
```

Edit `.env` at the **repo root** (one file for backend + frontend):

- `GOOGLE_MAPS_API_KEY` — server key (Directions, Places, Geocoding)
- `VITE_GOOGLE_MAPS_API_KEY` — browser key (Maps JavaScript API), HTTP referrer–restricted

Restart **both** `npm run dev` and the API after changing `.env` — env vars are only read at startup.

The single repo-root `.env` is used by the frontend (Vite), backend (FastAPI), and Docker Compose.

### 2. Database

```bash
docker compose up -d db
```

### 3. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Optional demo data:

```bash
python -m scripts.seed_demo
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

Or use Docker for API + DB:

```bash
docker compose up
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT |
| GET | `/api/routes/feed` | Public routes |
| POST | `/api/routes/generate` | Generate route from OSM (scenic/twisty/relaxed) |
| POST | `/api/routes` | Create draft |
| PATCH | `/api/routes/{id}` | Update metadata & stops |
| POST | `/api/routes/{id}/build` | Build geometry via Directions |
| POST | `/api/routes/{id}/publish` | Publish route |
| POST | `/api/routes/{id}/fork` | Copy public route |
| POST | `/api/routes/{id}/ratings` | Rate route |
| POST | `/api/routes/{id}/comments` | Comment |
| POST | `/api/routes/{id}/save` | Bookmark |
| GET | `/api/maps/places` | Places search (proxied) |
| GET | `/api/maps/config` | Quota / config status |

Interactive docs: http://localhost:8000/docs

## Google Maps setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable: **Maps JavaScript API**, **Directions API**, **Places API**, **Geocoding API**.
3. Create two keys:
   - **Server key** → `GOOGLE_MAPS_API_KEY` (IP-restrict or use only server-side)
   - **Browser key** → `VITE_GOOGLE_MAPS_API_KEY` (HTTP referrer: `http://localhost:5173/*`)
4. Set billing alerts and daily quotas (`directions_daily_quota`, `places_daily_quota` in config).

## Route generator spike (Phase 3)

```bash
cd backend
python -m app.workers.route_generator
```

Uses OpenStreetMap via `osmnx` to score and walk road edges. Requires network on first run.

**OSM cache (“dump”):** OSMnx downloads road data from the Overpass API and caches raw responses on disk (not a single dump file you import). Default folder is `./cache` relative to the API process working directory (usually `backend/cache/` if you run uvicorn from `backend/`). Configure with `ox.settings.cache_folder` in code or delete that folder to force a re-download.

## Project layout

```
backend/app/          FastAPI application
backend/alembic/      Database migrations
backend/scripts/      Seed & utilities
frontend/src/         React UI
docs/                 Planning & phase designs
```

## License

MIT (add license file if needed)
