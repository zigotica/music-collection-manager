import re
import unicodedata


def sanitize_filename(name: str) -> str:
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^\w\s\-_]', '', name)


def split_artists(artist_string: str) -> list:
    if not artist_string:
        return []
    
    artist_string = artist_string.strip()
    if not artist_string:
        return []
    
    artists = []
    lower = artist_string.lower()
    
    if re.search(r', .* (feat\.?|featuring|ft\.?) ', lower):
        if ' feat. ' in lower:
            artists = [a.strip() for a in re.split(' feat\\. ', artist_string, flags=re.IGNORECASE) if a.strip()]
        elif ' feat ' in lower:
            artists = [a.strip() for a in re.split(' feat ', artist_string, flags=re.IGNORECASE) if a.strip()]
        elif ' featuring ' in lower:
            artists = [a.strip() for a in re.split(' featuring ', artist_string, flags=re.IGNORECASE) if a.strip()]
        elif ' ft. ' in lower:
            artists = [a.strip() for a in re.split(' ft\\. ', artist_string, flags=re.IGNORECASE) if a.strip()]
        elif ' ft ' in lower:
            artists = [a.strip() for a in re.split(' ft ', artist_string, flags=re.IGNORECASE) if a.strip()]
        
        if artists and any(', ' in a for a in artists):
            split_again = []
            for a in artists:
                if ', ' in a:
                    split_again.extend([s.strip() for s in a.split(', ') if s.strip()])
                else:
                    split_again.append(a)
            artists = split_again
    elif ' / ' in artist_string:
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
    
    if not artists:
        if ', ' in artist_string:
            artists = [a.strip() for a in artist_string.split(', ') if a.strip()]
        else:
            artists = [artist_string]
    
    final_artists = []
    for artist in artists:
        lower_artist = artist.lower()
        if ' feat. ' in lower_artist:
            sub_artists = [a.strip() for a in re.split(' feat\\. ', artist, flags=re.IGNORECASE) if a.strip()]
            final_artists.extend(sub_artists)
        elif ' feat ' in lower_artist:
            sub_artists = [a.strip() for a in re.split(' feat ', artist, flags=re.IGNORECASE) if a.strip()]
            final_artists.extend(sub_artists)
        elif ' featuring ' in lower_artist:
            sub_artists = [a.strip() for a in re.split(' featuring ', artist, flags=re.IGNORECASE) if a.strip()]
            final_artists.extend(sub_artists)
        elif ' ft. ' in lower_artist:
            sub_artists = [a.strip() for a in re.split(' ft\\. ', artist, flags=re.IGNORECASE) if a.strip()]
            final_artists.extend(sub_artists)
        elif ' ft ' in lower_artist:
            sub_artists = [a.strip() for a in re.split(' ft ', artist, flags=re.IGNORECASE) if a.strip()]
            final_artists.extend(sub_artists)
        else:
            final_artists.append(artist)
    
    merged_artists = []
    i = 0
    while i < len(final_artists):
        current = final_artists[i]
        if i > 0 and re.search(r'^,? ?(jr\.?|sr\.?)$', current, re.IGNORECASE):
            merged = merged_artists[-1] + ' ' + current.replace(',', '').strip()
            merged_artists[-1] = merged.strip()
        else:
            merged_artists.append(current)
        i += 1
    
    return [a.strip() for a in merged_artists if a.strip()]


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
