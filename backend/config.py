import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "127.0.0.1")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
ROUTE_API_KEY = os.getenv("ROUTE_API_KEY", os.getenv("OPENROUTESERVICE_API_KEY", ""))

DATASET_PATH = BASE_DIR / "ml" / "dataset" / "travel_dataset.csv"
MODEL_DIR = BASE_DIR / "ml" / "models"

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USERNAME", "")).strip()

