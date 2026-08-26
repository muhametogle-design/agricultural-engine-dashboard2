"""Root ASGI entrypoint so the portal runs exactly as specified:

    uvicorn main:app --reload --port 8000

(no separate static server; proxies, pages and the dashboard are all
served by this single FastAPI application)."""
from __future__ import annotations

from app.main import app  # noqa: F401  (re-exported for uvicorn / tests)
