# Courtroom Trading System

A split frontend/backend trading decision system where:

- Groq-powered bull and bear agents argue from structured signals
- a deterministic judge scores the case
- Google-authenticated users run decisions and track outcomes
- MongoDB stores user history and memory bias

## Architecture

- `backend/` contains the FastAPI entrypoint
- `frontend/` contains the standalone browser client
- `src/courtroom_trading/` contains the domain logic, auth, repository, prompts, and LLM runners

The frontend and backend are intentionally separated now:

- frontend deploy target: Vercel or any static host
- backend deploy target: Render or Railway

## Features

- Courtroom-style bull and bear prompts
- Groq chat integration with JSON-object parsing
- Optional OpenAI fallback and stub fallback
- **Google OAuth authentication** - with demo mode fallback
- 4 real-time charts (Price, RSI, Moving Averages, Volume)
- Bull vs Bear arguments display (up to 10 each)
- Session-based protected API routes
- MongoDB-backed trade memory and history
- Outcome tracking: `PROFIT`, `LOSS`, `BREAKEVEN`, `CANCELLED`, `PENDING`
- Multi-page responsive UI with dark/light themes
- Agent reasoning details toggle

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py"
```

### Backend

Create `.env` from `.env.example`, then set at minimum:

- `GROQ_API_KEY`
- `JWT_SECRET`
- `MONGODB_URI`
- `USE_GROQ=true`
- `USE_MONGODB=true`
- `AUTH_MODE=google` (Google auth is now enabled by default)
- `GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID_HERE`

Optional: To use demo mode instead:

- Set `AUTH_MODE=demo` to skip Google OAuth and use demo login only

Run the API:

```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Local MongoDB with Docker

This repo now includes a local MongoDB container setup.

Start MongoDB:

```powershell
docker compose up -d mongodb
```

Default local connection values:

- `MONGODB_URI=mongodb://127.0.0.1:27017`
- `MONGODB_DATABASE=courtroom_trading`

Stop MongoDB:

```powershell
docker compose down
```

The database data is persisted in the Docker volume `mongodb_data`.

### Frontend

The frontend is now fully configured with Google OAuth. Copy [frontend/config.example.js](</d:/projects/ai agent project/frontend/config.example.js>) to `frontend/config.js`:

```javascript
window.COURTROOM_CONFIG = {
  API_BASE_URL: "http://127.0.0.1:8000",
   GOOGLE_CLIENT_ID: "YOUR_GOOGLE_CLIENT_ID_HERE",
  DEFAULT_THEME: "aurora-day"
};
```

The Google sign-in button will appear automatically on the auth page. Users can also use demo mode by clicking "Continue as Demo User".

Serve the frontend with any static server. For a quick local option:

```powershell
cd frontend
python -m http.server 3000
```

Then open `http://127.0.0.1:3000`.

## Recommended Local Flow

1. Start MongoDB with `docker compose up -d mongodb`
2. Put your Groq key in `.env` as `GROQ_API_KEY=...`
3. Keep `AUTH_MODE=google` (Google OAuth is now configured)
   - Or set `AUTH_MODE=demo` if you prefer demo login only
4. Start backend with `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
5. Start frontend with `cd frontend` and `python -m http.server 3000`
6. Open `http://127.0.0.1:3000`
7. Click "Sign In" and you'll see the Google OAuth button on the auth page
   - Or use "Continue as Demo User" for testing without OAuth

## Environment variables

### LLM

- `USE_GROQ=true`
- `GROQ_API_KEY=...`
- `GROQ_MODEL=llama3-70b-8192`
- `GROQ_TEMPERATURE=0.3`
- `USE_OPENAI=false`

### Auth

- `AUTH_MODE=demo` or `AUTH_MODE=google`
- `GOOGLE_CLIENT_ID=...`
- `GOOGLE_CLIENT_SECRET=...`
- `JWT_SECRET=...`
- `JWT_EXPIRATION_MINUTES=720`

Note:

- the current Google Sign-In flow only requires `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET` is included so your env is ready if you later move to an OAuth code flow
- the app now works completely in `AUTH_MODE=demo` before Google is configured

## Google OAuth Setup

Use Google Cloud Console and Google Identity Services for a `Web application` client.

Exact local-dev setup:

1. Open the Google Cloud project you want to use.
2. Go to Google Auth Platform and complete the Branding page.
3. Set your application name, support email, homepage, and privacy policy.
4. Go to Clients and create an OAuth client.
5. Choose `Web application`.
6. Add these Authorized JavaScript origins:
   - `http://localhost`
   - `http://localhost:3000`
   - `http://127.0.0.1:3000`
7. You do not need redirect URIs for the current frontend callback-based sign-in flow.
8. Copy the generated Client ID into:
   - backend `.env`: `GOOGLE_CLIENT_ID=...`
   - frontend `frontend/config.js`: `GOOGLE_CLIENT_ID: "..."`
9. When ready, switch backend auth mode to:
   - `AUTH_MODE=google`

What to put in the Google pages:

- Branding page:
  - App name: `Courtroom Trading System`
  - Support email: your email
  - Authorized domains: add your real domain in production
  - Homepage: your frontend URL
  - Privacy policy: your policy URL
- Data Access page:
  - default identity scopes are enough for this app
  - you do not need extra sensitive scopes for basic sign-in

Important local note:

- this project currently uses the Google Identity Services browser credential flow, so `GOOGLE_CLIENT_ID` is the field you need now
- `GOOGLE_CLIENT_SECRET` is kept in `.env` only so the project is ready if you later move to a server-side OAuth code flow

### Storage

- `USE_MONGODB=true`
- `MONGODB_URI=...`
- `MONGODB_DATABASE=courtroom_trading`

### Cross-origin setup

- `FRONTEND_ORIGIN=http://127.0.0.1:3000`
- `ALLOWED_ORIGINS=http://127.0.0.1:3000`

## API routes

Public:

- `GET /api/health`
- `GET /api/config`
- `POST /api/auth/demo`
- `POST /api/auth/google`

Protected:

- `GET /api/auth/me`
- `POST /api/auth/logout`
- `POST /api/decision`
- `POST /api/outcomes`
- `GET /api/history`

## Deployment

### Backend on Render or Railway

The root `Dockerfile` starts the FastAPI backend with:

```powershell
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
```

Set these env vars in your backend deployment:

- `GROQ_API_KEY`
- `AUTH_MODE`
- `GOOGLE_CLIENT_ID`
- `JWT_SECRET`
- `MONGODB_URI`
- `MONGODB_DATABASE`
- `FRONTEND_ORIGIN`
- `ALLOWED_ORIGINS`

### Frontend on Vercel

Deploy the `frontend/` directory as a static site.

Make sure `frontend/config.js` points at the backend URL, for example:

```js
window.COURTROOM_CONFIG = {
  API_BASE_URL: "https://your-backend.onrender.com",
  GOOGLE_CLIENT_ID: "your-google-client-id",
  DEFAULT_THEME: "aurora-day"
};
```

## Prompting and provider notes

The Groq runner uses OpenAI-compatible chat completions and keeps the courtroom prompt structure strict. The system still keeps scoring logic outside the model, which is the right tradeoff here:

- prompts generate arguments
- deterministic code validates and scores them
- Mongo stores history and learning bias

Official sources used for provider/auth implementation details:

- Groq text generation docs: https://console.groq.com/docs/text-chat
- Google Sign-In button docs: https://developers.google.com/identity/gsi/web/guides/display-button
- Google ID token verification docs: https://developers.google.com/identity/gsi/web/guides/verify-google-id-token

## Verification

Verified locally in this workspace with:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_demo.py
python -c "import backend.main; print(backend.main.app.title)"
```
