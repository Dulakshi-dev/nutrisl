import os
import sys

# Make the "app" package (backend/app) importable from this serverless function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app  # noqa: E402  (Vercel's Python runtime auto-detects this ASGI app)
