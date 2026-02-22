# Music Library

A personal music collection management web application built with FastAPI and PostgreSQL.

## Features

- Album collection management with cover images
- Wishlist tracking for albums you want to acquire
- Artist profiles with bios and images from Last.fm
- Browse by artist, year, decade, genre, or physical format
- Statistics and analytics for your collection
- Import from Discogs (collection and wishlist CSV exports)
- Last.fm integration for automatic metadata enrichment
- Admin panel with authentication
- Backup and restore functionality

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with Peewee ORM
- **Frontend**: Jinja2 templates
- **Containerization**: Docker & Docker Compose

## Prerequisites

- Docker and Docker Compose
- Last.fm API key (optional, for metadata enrichment)

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd music-library
```

### 2. Create environment file

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
DATABASE_URL=postgresql://musicuser:musicpass@music-collection-db:5432/musiclibrary
LASTFM_API_KEY=your_lastfm_api_key_here
ADMIN_PASSWORD=your_secure_password_here
SECRET_KEY=your_random_secret_key_here
COVERS_DIR=app/static/uploads/covers
ARTISTS_DIR=app/static/uploads/artists
```

To get a Last.fm API key:
1. Visit https://www.last.fm/api/account/create
2. Create an API account
3. Copy your API key

### 3. Start the application

```bash
docker compose build  # only needed the first time
docker compose up -d
```

The application will be available at http://localhost:8000

### Production with Traefik (Optional)

To deploy with a proper domain using Traefik, add labels to the web service in `docker-compose.yml`:

```yaml
services:
  music-collection-web:
    # ... existing config ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.music.rule=Host(`music.yourdomain.com`)"
      - "traefik.http.routers.music.tls=true"
      - "traefik.http.routers.music.tls.certresolver=letsencrypt"
```

## Usage

### Public Features (No Login Required)

- **Home**: Browse your collection, search albums
- **Artists**: View all artists with album counts
- **Artist Pages**: See albums by artist with Last.fm data
- **Browse**: Filter by year, decade, genre, or format
- **Wishlist**: View wanted albums
- **Statistics**: Collection analytics (decades, formats, top artists)

### Admin Features (Login Required)

1. Navigate to http://localhost:8000/login
2. Enter your `ADMIN_PASSWORD`

Admin capabilities:
- Add, edit, delete albums
- Import from Discogs CSV exports
- Bulk scrape missing metadata from Last.fm
- Manage artist profiles
- Backup/restore database and images

### Importing from Discogs

1. Export your collection or wishlist from Discogs (CSV format)
2. Go to Admin > Import Collection or Import Wishlist
3. Upload the CSV file

## Project Structure

```
music-library/
├── app/
│   ├── main.py           # FastAPI application entry point
│   ├── models.py         # Database models (Album, Artist)
│   ├── config.py         # Configuration settings
│   ├── auth.py           # Authentication logic
│   ├── routes/
│   │   ├── albums.py     # Album management routes
│   │   ├── browse.py     # Browsing routes
│   │   ├── stats.py      # Statistics routes
│   │   └── admin.py      # Admin panel routes
│   ├── services/
│   │   ├── lastfm.py     # Last.fm API integration
│   │   ├── import_csv.py # CSV import functionality
│   │   └── image_utils.py# Image processing
│   ├── templates/        # Jinja2 HTML templates
│   └── static/
│       ├── css/
│       └── uploads/      # Cover and artist images
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Home page with album list |
| `GET /wanted` | Wishlist albums |
| `GET /artists` | All artists |
| `GET /artist/{name}` | Albums by artist |
| `GET /year/{year}` | Albums by year |
| `GET /decade/{decade}` | Albums by decade |
| `GET /format/{format}` | Albums by format |
| `GET /genre/{tag}` | Albums by genre |
| `GET /stats` | Collection statistics |
| `GET /admin` | Admin panel |
| `GET /login` | Login page |
