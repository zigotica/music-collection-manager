import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://musicuser:musicpass@music-collection-db:5432/musiclibrary")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "")
USER_AGENT = os.getenv("USER_AGENT", "music-collection-app/1.0")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")

parsed_db = urlparse(DATABASE_URL)
DB_HOST = parsed_db.hostname
DB_PORT = parsed_db.port or 5432
DB_USER = parsed_db.username
DB_PASSWORD = parsed_db.password
DB_NAME = parsed_db.path.lstrip('/')

basedir = os.getcwd()
UPLOAD_DIR = "app/static/uploads"
COVERS_DIR = os.path.join(basedir, os.getenv("COVERS_DIR"))
ARTISTS_DIR = os.path.join(basedir, os.getenv("ARTISTS_DIR"))

covers_env = os.getenv("COVERS_DIR")
artists_env = os.getenv("ARTISTS_DIR")
if covers_env.startswith("app/"):
    covers_env = covers_env[4:]
if artists_env.startswith("app/"):
    artists_env = artists_env[4:]
COVERS_URL = "/" + covers_env + "/"
ARTISTS_URL = "/" + artists_env + "/"
