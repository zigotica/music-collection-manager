import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://musicuser:musicpass@music-collection-db:5432/musiclibrary")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "")
UPLOAD_DIR = "app/static/uploads"
