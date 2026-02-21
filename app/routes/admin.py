from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.import_csv import parse_discogs_csv, get_import_stats

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
    
    message = f"Imported {results['imported']} items to wishlist"
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
