"""Configuration de l'application (lue depuis le fichier .env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

PROFIL_FILE = DATA_DIR / "profil.json"
CV_ORIGINAL_FILE = DATA_DIR / "cv_original.pdf"
CV_GENERE_FILE = DATA_DIR / "cv_genere.pdf"
DB_FILE = DATA_DIR / "envoiecv.db"

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-a-changer")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

FRANCE_TRAVAIL_CLIENT_ID = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "")
FRANCE_TRAVAIL_CLIENT_SECRET = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "")
