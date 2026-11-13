"""Vercel entrypoint for the existing FastAPI application."""

from pathlib import Path
import sys

backend_root = Path(__file__).resolve().parent / "backend"
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.main import app  # noqa: E402

__all__ = ["app"]
