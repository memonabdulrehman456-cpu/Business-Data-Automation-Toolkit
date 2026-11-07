import pandas as pd
from app.services.processor import clean_and_report, profile_dataframe

def test_profile_counts_missing_and_duplicates():
    df = pd.DataFrame({
        "name": ["Ali", "Ali", "Sara"],
        "email": ["ali@example.com", "ali@example.com", None],
    })
    profile = profile_dataframe(df)
    assert profile["rows"] == 3
    assert profile["columns"] == 2
    assert profile["duplicate_rows"] == 1
    assert profile["missing_cells"] == 1

def test_clean_removes_duplicates_and_reports_invalid_email():
    df = pd.DataFrame({
        "name": [" Ali ", "Ali", "Sara"],
        "email": ["ali@example.com", "ali@example.com", "wrong-email"],
    })
    cleaned, exceptions, summary = clean_and_report(df)
    assert len(cleaned) == 2
    assert cleaned.iloc[0]["name"] == "Ali"
    assert summary["removed_duplicates"] == 1
    assert "invalid_email" in exceptions["issue"].tolist()

def test_blank_string_becomes_missing_exception():
    df = pd.DataFrame({"customer": ["A", "   "]})
    _, exceptions, summary = clean_and_report(df)
    assert summary["exception_count"] == 1
    assert exceptions.iloc[0]["issue"] == "missing_value"
