from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.main import app as backend_app

# Find the frontend folder.
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Create one application for the website and backend.
app = FastAPI()

# Keep all existing backend API endpoints.
app.mount("/api", backend_app)

# Serve the existing HTML, CSS, JavaScript and images.
app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend"
)
