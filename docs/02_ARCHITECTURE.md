# Architecture

Browser UI (HTML/CSS/JavaScript)
        |
        | multipart upload (direct to API)
        v
FastAPI endpoint
        |
        +--> upload size/type checks
        +--> CSV/JSON loader (Pandas)
        +--> profiler
        +--> cleaner + exception collector
        +--> CSV artifact writer
        |
        v
Download endpoints

## Design decisions
- UI and API are separated so the UI can be hosted on Vercel and the Python API on Render.
- Upload is copied to disk in chunks to avoid buffering the complete request in application memory.
- DataFrame processing still requires RAM proportional to the dataset size.
- Temporary artifacts are stored in the system temp directory; they are not permanent storage.
