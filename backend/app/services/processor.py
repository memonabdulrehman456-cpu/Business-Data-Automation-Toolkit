from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any
import pandas as pd

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".csv", ".json"}

class DataFileError(ValueError):
    """Raised when an uploaded data file cannot be safely processed."""

def load_dataframe(path: str | Path, filename: str) -> pd.DataFrame:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DataFileError("Unsupported file type. Please upload a CSV or JSON file.")

    try:
        if extension == ".csv":
            # utf-8-sig also handles CSV files exported with a BOM.
            df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        else:
            with open(path, "r", encoding="utf-8-sig") as file:
                raw = file.read()
            try:
                parsed: Any = json.loads(raw)
                if isinstance(parsed, dict):
                    # Accept either {"data": [...]} or a single object.
                    parsed = parsed.get("data", [parsed])
            except json.JSONDecodeError:
                # Also accept JSON Lines / NDJSON.
                parsed = [json.loads(line) for line in raw.splitlines() if line.strip()]
            if not isinstance(parsed, list):
                raise DataFileError("JSON must contain an array of objects or JSON Lines.")
            if parsed and not all(isinstance(row, dict) for row in parsed):
                raise DataFileError("Each JSON array item must be an object.")
            df = pd.DataFrame(parsed)
    except DataFileError:
        raise
    except UnicodeDecodeError as exc:
        raise DataFileError("Could not decode this file as UTF-8. Export it as UTF-8 and try again.") from exc
    except Exception as exc:
        logger.exception("Could not read uploaded file")
        raise DataFileError(f"Could not read this file: {exc}") from exc

    if len(df.columns) == 0:
        raise DataFileError("The uploaded file has no columns.")
    if len(df.columns) > 500:
        raise DataFileError("The file has more than 500 columns. Please reduce the column count.")
    return df

def _safe_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value

def profile_dataframe(df: pd.DataFrame) -> dict:
    missing_by_column = df.isna().sum()
    duplicate_count = int(df.duplicated().sum())
    columns = []
    for col in df.columns:
        series = df[col]
        samples = [_safe_value(v) for v in series.dropna().head(3).tolist()]
        columns.append({
            "name": str(col),
            "dtype": str(series.dtype),
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique(dropna=True)),
            "sample": samples,
        })
    total_cells = int(df.shape[0] * df.shape[1])
    missing_cells = int(missing_by_column.sum())
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_count,
        "completeness_percent": round(
            ((total_cells - missing_cells) / total_cells) * 100, 2
        ) if total_cells else 100.0,
        "column_profile": columns,
    }

def clean_and_report(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    cleaned = df.copy()
    original_rows = len(cleaned)

    # Normalize blank strings and trim whitespace in text columns.
    text_columns = cleaned.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        cleaned[col] = cleaned[col].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        cleaned[col] = cleaned[col].replace(r"^\s*$", pd.NA, regex=True)

    exceptions = []
    # Missing-value exceptions are row/column-specific.
    for row_index, row in cleaned.iterrows():
        for column, value in row.items():
            if pd.isna(value):
                exceptions.append({
                    "row_number": int(row_index) + 2,
                    "column": str(column),
                    "issue": "missing_value",
                    "value": "",
                })

    # Email validation is intentionally conservative and only applies to
    # columns whose names contain "email".
    for col in cleaned.columns:
        if "email" in str(col).lower():
            for row_index, value in cleaned[col].items():
                if pd.notna(value) and value != "":
                    text_value = str(value).strip()
                    if "@" not in text_value or "." not in text_value.split("@")[-1]:
                        exceptions.append({
                            "row_number": int(row_index) + 2,
                            "column": str(col),
                            "issue": "invalid_email",
                            "value": text_value,
                        })

    before_dedup = len(cleaned)
    cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    removed_duplicates = before_dedup - len(cleaned)

    exception_df = pd.DataFrame(
        exceptions, columns=["row_number", "column", "issue", "value"]
    )
    summary = {
        "input_rows": int(original_rows),
        "output_rows": int(len(cleaned)),
        "removed_duplicates": int(removed_duplicates),
        "exception_count": int(len(exception_df)),
        "trimmed_text_columns": int(len(text_columns)),
    }
    return cleaned, exception_df, summary
