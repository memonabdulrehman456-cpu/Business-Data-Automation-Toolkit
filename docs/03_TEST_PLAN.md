# Test Plan

| ID | Scenario | Expected result |
|---|---|---|
| T01 | Health endpoint | HTTP 200 and status `ok` |
| T02 | Unsupported TXT upload | HTTP 400 |
| T03 | CSV with duplicate rows | Duplicate count and removal reported |
| T04 | Missing cell | Exception row reported |
| T05 | Invalid email in email-named column | `invalid_email` exception |
| T06 | Whitespace around text | Text trimmed |
| T07 | Invalid/corrupt JSON | Clear validation error |
| T08 | File larger than configured cap | HTTP 413 |

Run automated checks with `pytest -q` from the backend folder.
