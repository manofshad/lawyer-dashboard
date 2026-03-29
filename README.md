<p align="center">
  <img width="301" height="72" alt="nyclegal_50" src="https://github.com/user-attachments/assets/5f14da75-11e0-467f-8aa5-cfd55cedf443" />
</p>

NYCLegal helps lawyers quickly review possible cases against New York City by turning messy city incident records into clear timelines and short case summaries for faster intake.

The platform is built for municipal liability intake and early case review. A user can search an address, review incident history tied to that location, place a client's incident date into that history, and generate a concise AI-assisted screening summary to support early evaluation.

## What NYCLegal Does

- Address-based search for NYC incident records
- Normalized location results so inconsistent public records are easier to review
- Map view for geographic context
- Chronological timeline of reported and closed incidents
- Client incident date comparison against prior incident history
- AI-assisted preliminary case-screening summary based on the timeline

NYCLegal is not a substitute for legal judgment. It is designed to give lawyers and intake teams a faster, clearer starting point.

## Stack

- Frontend: React, Vite, TypeScript, Tailwind CSS
- Backend: FastAPI, Python
- Auth: Supabase Auth with Google OAuth
- Data: PostgreSQL-compatible database plus normalized incident records
- AI: OpenAI for preliminary liability summaries
- Maps: MapTiler / MapLibre

## Project Structure

- `frontend/`: React dashboard
- `backend/`: FastAPI API and data import scripts
- `.env.example`: combined local environment reference
- `frontend/.env.example`: frontend-only environment template
- `backend/.env.example`: backend-only environment template

## Local Setup

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend runs on `http://localhost:5173`.

## Environment Variables

### Frontend

Required for the full app experience:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_MAPTILER_API_KEY=
```

Optional:

```env
VITE_MAP_STYLE_URL=
```

Notes:

- `VITE_API_BASE_URL` should point to the FastAPI backend.
- `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are required for authentication.
- `VITE_MAPTILER_API_KEY` enables the map.
- `VITE_MAP_STYLE_URL` can override the default MapTiler style URL if needed.

### Backend

```env
BACKEND_FRONTEND_ORIGIN=http://localhost:5173
BACKEND_SUPABASE_URL=
BACKEND_SUPABASE_SERVICE_ROLE_KEY=
BACKEND_DATABASE_URL=
BACKEND_OPENAI_API_KEY=
BACKEND_OPENAI_MODEL=gpt-5-mini
```

Notes:

- `BACKEND_FRONTEND_ORIGIN` should match the frontend dev URL.
- `BACKEND_SUPABASE_URL` is required for token verification.
- `BACKEND_SUPABASE_SERVICE_ROLE_KEY` is included for deployments or future backend Supabase operations.
- `BACKEND_DATABASE_URL` is required for incident lookup and timeline queries.
- `BACKEND_OPENAI_API_KEY` and `BACKEND_OPENAI_MODEL` power the AI liability summary.

## Authentication

NYCLegal uses Supabase Auth with Google OAuth:

1. Create a Supabase project.
2. Enable Google under `Authentication > Providers`.
3. Add your frontend URL to Supabase redirect URLs.
4. Put the Supabase project URL and anon key in `frontend/.env`.
5. Put the Supabase project URL in `backend/.env`.

The frontend authenticates users with Supabase, then sends the bearer token to FastAPI. The backend verifies the token against Supabase JWKS before serving protected endpoints.
