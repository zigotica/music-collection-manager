import csv
import io
from app.models import Album


def map_format(discogs_format: str) -> str:
    if not discogs_format:
        return None
    
    fmt_lower = discogs_format.lower()
    
    if any(x in fmt_lower for x in ['7"', 'ep', 'maxi', 'single']):
        return "EP - Single"
    if any(x in fmt_lower for x in ['12"', 'lp', 'vinyl']):
        return "Vinyl"
    if 'cd' in fmt_lower:
        return "CD"
    if 'dvd' in fmt_lower:
        return "DVD"
    if 'ray' in fmt_lower:
        return "Blu-ray"
    if 'cass' in fmt_lower:
        return "Tape"
    
    return None


def parse_discogs_csv(csv_content: bytes, is_wanted: bool = False) -> dict:
    results = {
        'imported': 0,
        'skipped_duplicates': [],
        'skipped_missing': [],
        'errors': []
    }
    
    try:
        content = csv_content.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            content = csv_content.decode('latin-1')
        except UnicodeDecodeError as e:
            results['errors'].append(f"Encoding error: {str(e)}")
            return results
    
    reader = csv.DictReader(io.StringIO(content))
    
    for row_num, row in enumerate(reader, start=2):
        try:
            artist = row.get('Artist', '').strip()
            title = row.get('Title', '').strip()
            
            if not artist or not title:
                missing = []
                if not artist:
                    missing.append('Artist')
                if not title:
                    missing.append('Title')
                results['skipped_missing'].append({
                    'row': row_num,
                    'artist': artist or '(empty)',
                    'title': title or '(empty)',
                    'missing': ', '.join(missing)
                })
                continue
            
            discogs_id = row.get('Release ID', '').strip() or None
            
            discogs_format = row.get('Format', '').strip()
            physical_format = map_format(discogs_format)
            
            existing = Album.select().where(
                (Album.artist == artist) & 
                (Album.title == title) &
                (Album.physical_format == physical_format) &
                (Album.is_wanted == is_wanted)
            ).first()
            
            if existing:
                results['skipped_duplicates'].append({
                    'row': row_num,
                    'artist': artist,
                    'title': title,
                    'format': physical_format or 'Unknown'
                })
                continue
            
            year_str = row.get('Released', '').strip()
            year = None
            if year_str:
                try:
                    year = int(year_str[:4])
                except ValueError:
                    pass
            
            notes = row.get('Notes', '').strip() or None
            
            Album.create(
                title=title,
                artist=artist,
                year=year,
                physical_format=physical_format,
                genres=[],
                cover_image_path=None,
                discogs_id=discogs_id,
                is_wanted=is_wanted,
                notes=notes
            )
            results['imported'] += 1
            
        except Exception as e:
            results['errors'].append(f"Row {row_num}: {str(e)}")
    
    return results


def get_import_stats() -> dict:
    collection_count = Album.select().where(Album.is_wanted == False).count()
    wanted_count = Album.select().where(Album.is_wanted == True).count()
    
    missing_year = Album.select().where(
        (Album.year.is_null()) | (Album.year == 0)
    ).count()
    
    missing_cover = Album.select().where(
        (Album.cover_image_path.is_null()) | (Album.cover_image_path == '')
    ).count()
    
    all_albums = list(Album.select())
    missing_genres = sum(1 for a in all_albums if not a.genres or a.genres == [] or a.genres == '[]')
    
    return {
        'collection_count': collection_count,
        'wanted_count': wanted_count,
        'missing_year': missing_year,
        'missing_cover': missing_cover,
        'missing_genres': missing_genres
    }
