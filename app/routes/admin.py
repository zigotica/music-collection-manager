from fastapi import APIRouter, Request, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app.services.import_csv import parse_discogs_csv, get_import_stats
from app.services.lastfm import scrape_album, scrape_artist as scrape_artist_profile
from app.models import Album, Artist
from app.auth import require_admin
from app.templates_globals import templates

router = APIRouter()

_last_import_results = None

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, message: str = None, error: str = None, _: bool = Depends(require_admin)):
    global _last_import_results
    stats = get_import_stats()
    import_results = _last_import_results
    _last_import_results = None
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "stats": stats,
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
    
    updated_count = 0
    for name_tuple in artist_names:
        artist_name = name_tuple.artist
        result = await scrape_artist_profile(artist_name)
        if result["updated"]:
            updated_count += 1
    
    message = f"Scraped {updated_count} artist profiles"
    return RedirectResponse(
        url=f"/admin?message={message}", 
        status_code=303
    )
