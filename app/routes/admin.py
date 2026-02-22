from fastapi import APIRouter, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from app.services.import_csv import parse_discogs_csv, get_import_stats, update_discogs_years
from app.services.lastfm import scrape_album, scrape_artist as scrape_artist_profile
from app.models import Album, Artist
from app.auth import require_admin
from app.templates_globals import templates
from app.config import COVERS_DIR, ARTISTS_DIR, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
import os
import io
import zipfile
import subprocess
from datetime import datetime

router = APIRouter()

_last_import_results = None

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, message: str = None, error: str = None, _: bool = Depends(require_admin)):
    global _last_import_results
    stats = get_import_stats()
    import_results = _last_import_results
    _last_import_results = None
    
    artist_names = list(Album.select(Album.artist).distinct())
    total_artists = len(artist_names)
    
    artists_missing_image = 0
    artists_missing_bio = 0
    artists_missing_genres = 0
    
    for name_tuple in artist_names:
        artist_name = name_tuple.artist
        artist = Artist.select().where(Artist.name == artist_name).first()
        
        if not artist:
            artists_missing_image += 1
            artists_missing_bio += 1
            artists_missing_genres += 1
        else:
            if not artist.image_url:
                artists_missing_image += 1
            if not artist.bio:
                artists_missing_bio += 1
            if not artist.genres or artist.genres == [] or artist.genres == '[]':
                artists_missing_genres += 1
    
    artist_stats = {
        'total': total_artists,
        'missing_image': artists_missing_image,
        'missing_bio': artists_missing_bio,
        'missing_genres': artists_missing_genres
    }
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "stats": stats,
        "artist_stats": artist_stats,
        "message": message,
        "error": error,
        "import_results": import_results
    })

@router.post("/admin/import/collection")
async def import_collection(request: Request, file: UploadFile = File(...), _: bool = Depends(require_admin)):
    global _last_import_results
    
    if not file.filename.endswith('.csv'):
        return RedirectResponse(
            url="/admin?error=Please+upload+a+CSV+file", 
            status_code=303
        )
    
    content = await file.read()
    results = parse_discogs_csv(content, is_wanted=False)
    
    _last_import_results = {
        'type': 'collection',
        'imported': results['imported'],
        'skipped_duplicates': results['skipped_duplicates'],
        'skipped_missing': results['skipped_missing'],
        'errors': results['errors']
    }
    
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/admin/import/wishlist")
async def import_wishlist(request: Request, file: UploadFile = File(...), _: bool = Depends(require_admin)):
    global _last_import_results
    
    if not file.filename.endswith('.csv'):
        return RedirectResponse(
            url="/admin?error=Please+upload+a+CSV+file", 
            status_code=303
        )
    
    content = await file.read()
    results = parse_discogs_csv(content, is_wanted=True)
    
    _last_import_results = {
        'type': 'wishlist',
        'imported': results['imported'],
        'skipped_duplicates': results['skipped_duplicates'],
        'skipped_missing': results['skipped_missing'],
        'errors': results['errors']
    }
    
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/admin/import/discogs-years")
async def import_discogs_years(request: Request, file: UploadFile = File(...), _: bool = Depends(require_admin)):
    from app.services.import_csv import update_discogs_years
    
    if not file.filename.endswith('.csv'):
        return RedirectResponse(
            url="/admin?error=Please+upload+a+CSV+file", 
            status_code=303
        )
    
    content = await file.read()
    results = update_discogs_years(content)
    
    return RedirectResponse(
        url=f"/admin?message=Updated+{results['updated']}+albums+with+Discogs+years", 
        status_code=303
    )

@router.post("/admin/scrape")
async def bulk_scrape(request: Request, _: bool = Depends(require_admin)):
    all_albums = list(Album.select())
    
    albums_to_scrape = [
        a for a in all_albums 
        if not a.cover_image_path or not a.year or not a.genres or a.genres == [] or a.genres == '[]'
    ]
    
    if not albums_to_scrape:
        return RedirectResponse(
            url="/admin?message=No+albums+need+scraping", 
            status_code=303
        )
    
    updated_count = 0
    for album in albums_to_scrape:
        result = await scrape_album(album)
        if result["updated"]:
            updated_count += 1
    
    message = f"Scraped {updated_count} of {len(albums_to_scrape)} albums"
    return RedirectResponse(
        url=f"/admin?message={message}", 
        status_code=303
    )

@router.get("/admin/missing-data", response_class=HTMLResponse)
async def missing_data_page(request: Request, _: bool = Depends(require_admin)):
    all_albums = list(Album.select())
    
    albums_with_missing = []
    for album in all_albums:
        missing = []
        if not album.year:
            missing.append('Year')
        if not album.cover_image_path:
            missing.append('Cover')
        if not album.genres or album.genres == [] or album.genres == '[]':
            missing.append('Genres')
        
        if missing:
            albums_with_missing.append({
                'album': album,
                'missing': missing
            })
    
    return templates.TemplateResponse("missing_data.html", {
        "request": request,
        "albums_with_missing": albums_with_missing
    })

@router.post("/admin/scrape-artists")
async def bulk_scrape_artists(request: Request, _: bool = Depends(require_admin)):
    artist_names = list(Album.select(Album.artist).distinct())
    
    artists_to_scrape = []
    for name_tuple in artist_names:
        artist_name = name_tuple.artist
        artist = Artist.select().where(Artist.name == artist_name).first()
        
        if not artist:
            artists_to_scrape.append(artist_name)
        elif not artist.image_url or not artist.bio or not artist.genres or artist.genres == [] or artist.genres == '[]':
            artists_to_scrape.append(artist_name)
    
    if not artists_to_scrape:
        return RedirectResponse(
            url="/admin?message=No+artists+need+scraping", 
            status_code=303
        )
    
    updated_count = 0
    for artist_name in artists_to_scrape:
        result = await scrape_artist_profile(artist_name)
        if result["updated"]:
            updated_count += 1
    
    message = f"Scraped {updated_count} of {len(artists_to_scrape)} artist profiles"
    return RedirectResponse(
        url=f"/admin?message={message}", 
        status_code=303
    )

@router.get("/admin/missing-artists", response_class=HTMLResponse)
async def missing_artists_page(request: Request, _: bool = Depends(require_admin)):
    artist_names = list(Album.select(Album.artist).distinct())
    
    artists_with_missing = []
    for name_tuple in artist_names:
        artist_name = name_tuple.artist
        artist = Artist.select().where(Artist.name == artist_name).first()
        album_count = Album.select().where(Album.artist == artist_name).count()
        
        missing = []
        if not artist:
            missing.extend(['Image', 'Bio', 'Genres'])
        else:
            if not artist.image_url:
                missing.append('Image')
            if not artist.bio:
                missing.append('Bio')
            if not artist.genres or artist.genres == [] or artist.genres == '[]':
                missing.append('Genres')
        
        if missing:
            artists_with_missing.append({
                'name': artist_name,
                'artist': artist,
                'album_count': album_count,
                'missing': missing
            })
    
    return templates.TemplateResponse("missing_artists.html", {
        "request": request,
        "artists_with_missing": artists_with_missing
    })

@router.get("/admin/backup", response_class=HTMLResponse)
async def backup_page(request: Request, _: bool = Depends(require_admin), message: str = None, error: str = None):
    stats = {
        'album_count': Album.select().count(),
        'artist_count': Artist.select().count(),
        'covers_count': len([f for f in os.listdir(COVERS_DIR) if os.path.isfile(os.path.join(COVERS_DIR, f))]) if os.path.exists(COVERS_DIR) else 0,
        'artist_images_count': len([f for f in os.listdir(ARTISTS_DIR) if os.path.isfile(os.path.join(ARTISTS_DIR, f))]) if os.path.exists(ARTISTS_DIR) else 0
    }
    return templates.TemplateResponse("backup.html", {
        "request": request,
        "stats": stats,
        "message": message,
        "error": error
    })

@router.get("/admin/backup/database")
async def backup_database(_: bool = Depends(require_admin)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"music_library_backup_{timestamp}.sql"
    
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    
    process = subprocess.Popen(
        ["pg_dump", "-U", DB_USER, "-h", DB_HOST, "-p", str(DB_PORT), "--no-owner", "--no-acl", "--clean", DB_NAME],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        return RedirectResponse(url="/admin/backup?error=Database+export+failed", status_code=303)
    
    lines = stdout.decode('utf-8').split('\n')
    clean_lines = [line for line in lines if not line.startswith('\\restrict')]
    clean_output = '\n'.join(clean_lines).encode('utf-8')
    
    return StreamingResponse(
        io.BytesIO(clean_output),
        media_type="application/sql",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/admin/backup/images")
async def backup_images(_: bool = Depends(require_admin)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"music_library_images_{timestamp}.zip"
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if os.path.exists(COVERS_DIR):
            for file in os.listdir(COVERS_DIR):
                filepath = os.path.join(COVERS_DIR, file)
                if os.path.isfile(filepath):
                    zipf.write(filepath, f"covers/{file}")
        
        if os.path.exists(ARTISTS_DIR):
            for file in os.listdir(ARTISTS_DIR):
                filepath = os.path.join(ARTISTS_DIR, file)
                if os.path.isfile(filepath):
                    zipf.write(filepath, f"artists/{file}")
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/admin/restore/database")
async def restore_database(file: UploadFile = File(...), _: bool = Depends(require_admin)):
    if not file.filename.endswith('.sql'):
        return RedirectResponse(url="/admin/backup?error=Please+upload+a+SQL+file", status_code=303)
    
    content = await file.read()
    
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    
    process = subprocess.Popen(
        ["psql", "-U", DB_USER, "-h", DB_HOST, "-p", str(DB_PORT), DB_NAME],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    stdout, stderr = process.communicate(input=content)
    
    if process.returncode != 0:
        error_msg = stderr.decode('utf-8', errors='replace')[:200]
        return RedirectResponse(url=f"/admin/backup?error=Database+restore+failed", status_code=303)
    
    return RedirectResponse(url="/admin/backup?message=Database+restored+successfully", status_code=303)

@router.post("/admin/restore/covers")
async def restore_covers(files: list[UploadFile] = File(...), _: bool = Depends(require_admin)):
    try:
        os.makedirs(COVERS_DIR, exist_ok=True)
        
        for file in files:
            if file.filename:
                content = await file.read()
                filepath = os.path.join(COVERS_DIR, file.filename)
                with open(filepath, 'wb') as f:
                    f.write(content)
        
        return RedirectResponse(url="/admin/backup?message=Covers+restored+successfully", status_code=303)
    except Exception as e:
        return RedirectResponse(url="/admin/backup?error=Failed+to+restore+covers", status_code=303)

@router.post("/admin/restore/artists")
async def restore_artists(files: list[UploadFile] = File(...), _: bool = Depends(require_admin)):
    try:
        os.makedirs(ARTISTS_DIR, exist_ok=True)
        
        for file in files:
            if file.filename:
                content = await file.read()
                filepath = os.path.join(ARTISTS_DIR, file.filename)
                with open(filepath, 'wb') as f:
                    f.write(content)
        
        return RedirectResponse(url="/admin/backup?message=Artist+images+restored+successfully", status_code=303)
    except Exception as e:
        return RedirectResponse(url="/admin/backup?error=Failed+to+restore+artist+images", status_code=303)
