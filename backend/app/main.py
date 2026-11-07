from __future__ import annotations
import logging
import os
import tempfile
import uuid
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.config import APP_NAME, CORS_ORIGINS, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB
from app.logging_config import configure_logging
from app.services.processor import (
    DataFileError, clean_and_report, load_dataframe, profile_dataframe
)

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=APP_NAME,
    description="Upload, profile, clean and validate CSV/JSON business data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Temporary artifacts are stored outside the source tree.
ARTIFACT_DIR = Path(tempfile.gettempdir()) / "arrowstack_bdat_artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/api/health")
def health():
    return {"status": "ok", "app": APP_NAME, "max_upload_mb": MAX_UPLOAD_MB}

@app.post("/api/process")
async def process_file(file: UploadFile = File(...)):
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".json"}:
        raise HTTPException(status_code=400, detail="Only .csv and .json files are supported.")

    temp_path = ARTIFACT_DIR / f"upload_{uuid.uuid4().hex}{suffix}"
    size = 0
    try:
        # Chunked upload-to-disk avoids reading the whole upload into RAM.
        with temp_path.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the configured {MAX_UPLOAD_MB} MB upload limit."
                    )
                output.write(chunk)

        if size == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        df = load_dataframe(temp_path, filename)
        profile = profile_dataframe(df)
        cleaned, exceptions, cleaning_summary = clean_and_report(df)

        artifact_id = uuid.uuid4().hex
        clean_path = ARTIFACT_DIR / f"{artifact_id}_cleaned.csv"
        exception_path = ARTIFACT_DIR / f"{artifact_id}_exceptions.csv"
        cleaned.to_csv(clean_path, index=False, encoding="utf-8-sig")
        exceptions.to_csv(exception_path, index=False, encoding="utf-8-sig")

        logger.info(
            "Processed file=%s bytes=%s rows=%s columns=%s",
            filename, size, profile["rows"], profile["columns"]
        )
        return {
            "artifact_id": artifact_id,
            "filename": filename,
            "file_size_bytes": size,
            "profile": profile,
            "cleaning": cleaning_summary,
            "downloads": {
                "cleaned_csv": f"/api/download/{artifact_id}/cleaned",
                "exceptions_csv": f"/api/download/{artifact_id}/exceptions",
            },
        }
    except HTTPException:
        raise
    except DataFileError as exc:
        logger.warning("Rejected file %s: %s", filename, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected processing error")
        raise HTTPException(status_code=500, detail="An unexpected processing error occurred.") from exc
    finally:
        await file.close()
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            logger.warning("Could not remove temporary upload file %s", temp_path)

@app.get("/api/download/{artifact_id}/{kind}")
def download_artifact(artifact_id: str, kind: str):
    if not all(ch in "0123456789abcdef" for ch in artifact_id) or len(artifact_id) != 32:
        raise HTTPException(status_code=400, detail="Invalid download identifier.")
    if kind == "cleaned":
        path = ARTIFACT_DIR / f"{artifact_id}_cleaned.csv"
        name = "cleaned_data.csv"
    elif kind == "exceptions":
        path = ARTIFACT_DIR / f"{artifact_id}_exceptions.csv"
        name = "exception_report.csv"
    else:
        raise HTTPException(status_code=404, detail="Unknown download type.")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Download expired or not found. Process the file again.")
    return FileResponse(path, filename=name, media_type="text/csv")

# Serve the included interface when running the backend locally or on Render.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return index.read_text(encoding="utf-8")
    return "<h1>Business Data Automation Toolkit API is running.</h1><p>Visit /docs for API documentation.</p>"
