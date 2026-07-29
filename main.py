"""Getszy — AI-Powered Business Builder Platform

This is the main entry point for the application.
The real FastAPI application lives in legacy-getszy/backend/server.py
"""

import sys
import os

# Add legacy backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "legacy-getszy", "backend"))

from server import app  # noqa: E402

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
