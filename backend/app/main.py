
from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path

from flask import Flask, request, jsonify, send_file, send_from_directory

from app.config import APP_NAME, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB
from app.logging_config import configure_logging
from app.services.processor import (
    DataFileError,
    clean_and_report,
    load_dataframe,
    profile_dataframe,
)

configure_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

ARTIFACT_DIR = Path(tempfile.gettempdir()) / "arrowstack_bdat_artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "app": APP_NAME,
        "max_upload_mb": MAX_UPLOAD_MB
    })


@app.post("/api/process")
def process_file():

    if "file" not in request.files:
        return jsonify({"detail": "No file uploaded."}), 400

    file = request.files["file"]

    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()

    if suffix not in {".csv", ".json"}:
        return jsonify({
            "detail": "Only .csv and .json files are supported."
        }), 400

    temp_path = ARTIFACT_DIR / f"upload_{uuid.uuid4().hex}{suffix}"

    try:
        file.save(temp_path)

        size = temp_path.stat().st_size

        if size == 0:
            return jsonify({"detail": "The uploaded file is empty."}), 400

        if size > MAX_UPLOAD_BYTES:
            return jsonify({
                "detail": f"File exceeds the configured {MAX_UPLOAD_MB} MB upload limit."
            }), 413

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

        return jsonify({
            "artifact_id": artifact_id,
            "filename": filename,
            "file_size_bytes": size,
            "profile": profile,
            "cleaning": cleaning_summary,
            "downloads": {
                "cleaned_csv": f"/api/download/{artifact_id}/cleaned",
                "exceptions_csv": f"/api/download/{artifact_id}/exceptions",
            }
        })

    except DataFileError as exc:
        logger.warning("Rejected file %s: %s", filename, exc)
        return jsonify({"detail": str(exc)}), 422

    except Exception:
        logger.exception("Unexpected processing error")
        return jsonify({
            "detail": "An unexpected processing error occurred."
        }), 500

    finally:
        temp_path.unlink(missing_ok=True)


@app.get("/api/download/<artifact_id>/<kind>")
def download_artifact(artifact_id, kind):

    if len(artifact_id) != 32 or not all(
        ch in "0123456789abcdef" for ch in artifact_id
    ):
        return jsonify({"detail": "Invalid download identifier."}), 400

    if kind == "cleaned":
        path = ARTIFACT_DIR / f"{artifact_id}_cleaned.csv"
        name = "cleaned_data.csv"

    elif kind == "exceptions":
        path = ARTIFACT_DIR / f"{artifact_id}_exceptions.csv"
        name = "exception_report.csv"

    else:
        return jsonify({"detail": "Unknown download type."}), 404

    if not path.exists():
        return jsonify({
            "detail": "Download expired or not found. Process the file again."
        }), 404

    return send_file(path, as_attachment=True, download_name=name)


@app.get("/")
def home():
    index = FRONTEND_DIR / "index.html"

    if index.exists():
        return send_from_directory(FRONTEND_DIR, "index.html")

    return "<h1>Business Data Automation Toolkit is running.</h1>"


@app.get("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "detail": f"File exceeds the configured {MAX_UPLOAD_MB} MB upload limit."
    }), 413
