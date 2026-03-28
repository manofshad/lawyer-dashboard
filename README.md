# Hackathon Starter

Minimal starter with:

- FastAPI backend
- React + Vite + TypeScript frontend
- Tailwind CSS
- Supabase Auth with Google OAuth
- Supabase as the database platform

## Structure

- `backend/`: FastAPI app
- `frontend/`: Vite React app

## Backend setup

1. Create a virtual environment:

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create `backend/.env`:

   ```env
   BACKEND_FRONTEND_ORIGIN=http://localhost:5173
   BACKEND_SUPABASE_URL=https://your-project-ref.supabase.co
   ```

3. Start the API:

   ```bash
   uvicorn app.main:app --reload
   ```

Backend endpoints:

- `GET /health`
- `POST /api/echo`
- `GET /api/me`

## Sample incident import

The repo includes a 10-row demo pothole dataset and a deterministic import path:

- Source CSV: `backend/street-pothole-sample-10.csv`
- Normalized JSON artifact: `backend/sample_incidents.json`
- CSV to JSON transform: `backend/scripts/build_sample_incidents_json.py`
- JSON to Postgres import: `backend/scripts/import_sample_incidents.py`

Install backend dependencies, then:

```bash
cd backend
python scripts/build_sample_incidents_json.py
BACKEND_DATABASE_URL=postgresql://... python scripts/import_sample_incidents.py
```

The importer writes:

- one `locations` row per normalized address/street segment
- one `incidents` row per sample work order
- two `incident_events` rows per incident: `reported` and `closed`

## Frontend setup

1. Install dependencies:

   ```bash
   cd frontend
   npm install
   ```

2. Create `frontend/.env`:

   ```env
   VITE_API_BASE_URL=http://localhost:8000
   VITE_SUPABASE_URL=https://your-project-ref.supabase.co
   VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
   ```

3. Start the app:

   ```bash
   npm run dev
   ```

## Google OAuth with Supabase

1. Create a Supabase project.
2. In Supabase, open `Authentication > Providers` and enable Google.
3. In Google Cloud, create OAuth credentials for a web application.
4. Add the redirect URL shown by Supabase to the Google OAuth client.
5. In Supabase, add your local frontend URL to the allowed redirect URLs.
6. Copy the Supabase project URL and anon key into `frontend/.env`.
7. Copy the Supabase project URL into `backend/.env`.

## Auth architecture

- The frontend starts Google sign-in using Supabase Auth.
- Supabase returns a user session and access token to the frontend.
- The frontend sends the access token to FastAPI as a bearer token.
- FastAPI verifies the token against Supabase JWKS and returns user claims from `GET /api/me`.

## Notes

- This starter keeps the database layer intentionally minimal so you can add product-specific schema later.
- `GET /health` is included for quick smoke checks during development and deployment.
