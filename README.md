# Business Data Automation Toolkit
**Arrowstack Python Development Internship — Project 1**

A professional CSV/JSON data quality and automation application. Upload a dataset, inspect its quality, clean common issues, and download clean data plus an exception report.

## Features
- CSV and JSON ingestion (JSON array of objects or JSON Lines)
- Configurable upload limit (default 250 MB)
- Data profiling: rows, columns, missing values, duplicate rows, column types
- Data cleaning: trim text, normalize blank cells to null, remove exact duplicate rows
- Exception reporting: missing cells and invalid email values
- Download cleaned CSV, exception report and a full text analysis summary
- View a detailed in-app summary with column-level profiling
- Three auto-generated charts: completeness, missing values by column and cleaning impact
- FastAPI backend, modular Python package, structured logging, environment configuration
- Pytest automated tests
- Responsive browser UI with sample-data generator

## Architecture
- `backend/`: Python FastAPI processing API (deploy to Render or another Python host)
- `frontend/`: static UI (deploy to Vercel)
- The browser uploads directly to the Python API. Vercel hosts only the static interface, so the file does not pass through a Vercel Function request body.
- `docs/`: requirements, architecture, test plan and work log template

## Important hosting note for large files
The application default upload cap is **250 MB**, configurable with `MAX_UPLOAD_MB`. Actual practical capacity also depends on the backend host's request limits, RAM, CPU and available disk. The JSON parser loads records into memory, so very large JSON files may require more RAM. For production-scale files, use object storage and background workers. Do not claim unlimited uploads.

## Run locally (Windows / VS Code)
1. Install Python 3.10 or newer.
2. Open a terminal in `backend`.
3. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and review settings.
6. Start the API and web app using either command:
   ```powershell
   python app.py
   ```
   or
   ```powershell
   uvicorn app.main:app --reload
   ```
7. Open `http://127.0.0.1:8000`.
8. API documentation: `http://127.0.0.1:8000/docs`.

## Analysis summary and charts
After processing a CSV/JSON file, use **View full summary** to inspect the dataset and column profile, or **Download summary** to save a timestamped TXT report. The dashboard renders three lightweight SVG charts directly in the browser: data completeness, missing values by column, and cleaning impact. The charts do not depend on Chart.js or an external chart CDN, so they can render without an internet connection.

## Run tests
From `backend`:
```powershell
pytest -q
```

## Deploy
### 1) Backend — Render
1. Push this project to GitHub.
2. In Render, create a **Web Service** and connect the repository.
3. Set **Root Directory** to `backend`.
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables:
   - `MAX_UPLOAD_MB=250`
   - `CORS_ORIGINS=https://YOUR-VERCEL-DOMAIN.vercel.app`
   - `LOG_LEVEL=INFO`
7. Deploy and copy the backend URL, e.g. `https://your-service.onrender.com`.

### 2) Frontend — Vercel
1. Import the same GitHub repository into Vercel.
2. Set Root Directory to `frontend`.
3. Framework preset: **Other**.
4. Add environment variable `API_BASE_URL` with your Render backend URL, without a trailing slash.
5. Deploy. The static `vercel.json` rewrites `/config.js` to a small config endpoint only if configured by the build environment? For a simple deployment, edit `config.js` and set `API_BASE_URL` to your Render URL before deploying.
6. Redeploy after changing the backend URL.

**Alternative:** Deploy the entire FastAPI app to Render and use its built-in UI at the same URL. This is the easiest first deployment and avoids configuring Vercel.

## Security and data handling
- Uploaded files are processed on the backend and temporary artifacts are stored under the system temp directory.
- The demo does not use authentication. Do not upload confidential, personal, medical or regulated data.
- Temporary artifact cleanup is basic; add scheduled cleanup and authentication before production use.
- Configure CORS to your exact frontend domain for deployment.
- Never commit `.env`, secrets, or real customer datasets.

## Project workflow
See `docs/` for requirements, architecture, acceptance criteria, test plan and work log template.

## Limitations / future improvements
- Data is processed in memory after upload; large files need adequate backend RAM.
- JSON arrays are loaded as records; very large JSON should be processed with streaming or a background job.
- No database or user accounts in this internship version.
- Future: cloud object storage, job queue, role-based access, schema templates, Excel support and audit history.
