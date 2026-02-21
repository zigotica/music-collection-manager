from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.import_csv import parse_discogs_csv, get_import_stats
from app.services.lastfm import scrape_album
from app.models import Album

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, message: str = None, error: str = None):
    stats = get_import_stats()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "stats": stats,
        "message": message,
        "error": error
    })

@router.post("/admin/import/collection")
async def import_collection(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        return RedirectResponse(
            url="/admin?error=Please+upload+a+CSV+file", 
            status_code=303
        )
    
    content = await file.read()
    results = parse_discogs_csv(content, is_wanted=False)
    
    message = f"Imported {results['imported']} albums"
    if results['skipped'] > 0:
        message += f", skipped {results['skipped']} (duplicates or missing data)"
    
    if results['errors']:
        error = f"{len(results['errors'])} errors occurred"
        return RedirectResponse(
            url=f"/admin?message={message}&error={error}", 
            status_code=303
        )
    
    return RedirectResponse(
        url=f"/admin?message={message}", 
        status_code=303
    )

@router.post("/admin/import/wishlist")
async def import_wishlist(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        return RedirectResponse(
            url="/admin?error=Please+upload+a+CSV+file", 
            status_code=303
        )
    
    content = await file.read()
    results = parse_discogs_csv(content, is_wanted=True)
    
    return RedirectResponse(
        url=f"/admin?message={message}", 
        status_code=303
    )

@router.post("/admin/scrape")
async def bulk_scrape(request: Request):
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
