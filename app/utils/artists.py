import re

def split_artists(artist_string: str) -> list:
    if not artist_string:
        return []
    
    artist_string = artist_string.strip()
    if not artist_string:
        return []
    
    artists = []
    lower = artist_string.lower()
    
    if ' / ' in artist_string:
        artists = artist_string.split(' / ')
    elif ' + ' in artist_string:
        artists = artist_string.split(' + ')
    elif ' · ' in artist_string:
        artists = artist_string.split(' · ')
    elif ' ∙ ' in artist_string:
        artists = artist_string.split(' ∙ ')
    elif ' feat. ' in lower:
        artists = [a.strip() for a in re.split(' feat\\. ', artist_string, flags=re.IGNORECASE) if a.strip()]
    elif ' feat ' in lower:
        artists = [a.strip() for a in re.split(' feat ', artist_string, flags=re.IGNORECASE) if a.strip()]
    elif ' featuring ' in lower:
        artists = [a.strip() for a in re.split(' featuring ', artist_string, flags=re.IGNORECASE) if a.strip()]
    elif ' ft. ' in lower:
        artists = [a.strip() for a in re.split(' ft\\. ', artist_string, flags=re.IGNORECASE) if a.strip()]
    elif ' ft ' in lower:
        artists = [a.strip() for a in re.split(' ft ', artist_string, flags=re.IGNORECASE) if a.strip()]
    elif ' - ' in artist_string:
        artists = [a.strip() for a in artist_string.split(' - ') if a.strip()]
    else:
        artists = [artist_string]
    
    return [a.strip() for a in artists if a.strip()]


def join_artists(artists: list) -> str:
    return ', '.join(artists)


def strip_discogs_suffix(artist_string: str) -> str:
    pattern = r'\s*\(\d{4}\)\s*$'
    result = re.sub(pattern, '', artist_string).strip()
    pattern2 = r'\s*\(\d+\)\s*$'
    result = re.sub(pattern2, '', result).strip()
    return result


def apply_artist_mapping(artist_string: str) -> str:
    from app.models import ArtistMapping
    
    artists = split_artists(artist_string)
    mapped_artists = []
    
    for artist in artists:
        mapped_name = strip_discogs_suffix(artist)
        
        if mapped_name != artist:
            existing_mapping = ArtistMapping.select().where(
                (ArtistMapping.original_name == artist) &
                (ArtistMapping.new_name == mapped_name)
            ).first()
            if not existing_mapping:
                ArtistMapping.create(original_name=artist, new_name=mapped_name)
            artist = mapped_name
        
        mapping = ArtistMapping.select().where(ArtistMapping.original_name == artist).first()
        if mapping:
            mapped_artists.append(mapping.new_name)
        else:
            mapped_artists.append(artist)
    
    return ', '.join(mapped_artists)
