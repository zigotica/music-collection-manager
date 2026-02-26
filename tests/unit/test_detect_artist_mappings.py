import pytest
import sys
sys.path.insert(0, '/Users/hanzonian/Documents/personal/music-library')

from app.services.import_csv import detect_artist_mappings


class TestDetectArtistMappings:
    def test_no_existing_albums_returns_empty(self, mocker):
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool,Undertow,CD,2023,123"
        
        result = detect_artist_mappings(csv_content)
        
        assert result['mappings_found'] == 0
        assert result['mappings_created'] == 0
    
    def test_matching_artists_no_mapping_created(self, mocker):
        mock_album = mocker.MagicMock()
        mock_album.artist = "Tool"
        
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = mock_album
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool,Undertow,CD,2023,123"
        
        result = detect_artist_mappings(csv_content)
        
        assert result['mappings_found'] == 0
        assert result['mappings_created'] == 0
    
    def test_different_artists_mapping_created(self, mocker):
        mock_album = mocker.MagicMock()
        mock_album.artist = "Tool"
        
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = mock_album
        
        mock_mapping_select = mocker.patch('app.services.import_csv.ArtistMapping.select')
        mock_mapping_select.return_value.where.return_value.first.return_value = None
        mock_mapping_create = mocker.patch('app.services.import_csv.ArtistMapping.create')
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool (2),Undertow,CD,2023,123"
        
        result = detect_artist_mappings(csv_content)
        
        assert result['mappings_found'] == 1
        assert result['mappings_created'] == 1
    
    def test_existing_mapping_not_duplicated(self, mocker):
        mock_album = mocker.MagicMock()
        mock_album.artist = "Tool"
        
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = mock_album
        
        mock_mapping = mocker.MagicMock()
        mock_mapping_select = mocker.patch('app.services.import_csv.ArtistMapping.select')
        mock_mapping_select.return_value.where.return_value.first.return_value = mock_mapping
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool (2),Undertow,CD,2023,123"
        
        result = detect_artist_mappings(csv_content)
        
        assert result['mappings_found'] == 1
        assert result['mappings_created'] == 0
    
    def test_multi_artist_csv_to_single_db(self, mocker):
        mock_album = mocker.MagicMock()
        mock_album.artist = "The Beatles"
        
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = mock_album
        
        mock_mapping_select = mocker.patch('app.services.import_csv.ArtistMapping.select')
        mock_mapping_select.return_value.where.return_value.first.return_value = None
        
        csv_content = b"Artist,Title,Format,Released,release_id\nJohn Lennon / Paul McCartney,Abbey Road,CD,2023,456"
        
        result = detect_artist_mappings(csv_content)
        
        assert result['mappings_found'] == 2
    
    def test_encoding_utf8_sig(self, mocker):
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        
        csv_content = "\ufeffArtist,Title,Format,Released,release_id\nTool,Undertow,CD,2023,123".encode('utf-8-sig')
        
        result = detect_artist_mappings(csv_content)
        
        assert 'errors' not in result or len(result.get('errors', [])) == 0
    
    def test_encoding_latin1_fallback(self, mocker):
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        
        csv_content = "Artist,Title,Format,Released,release_id\nTool,Undertow,CD,2023,123".encode('latin-1')
        
        result = detect_artist_mappings(csv_content)
        
        assert 'errors' not in result or len(result.get('errors', [])) == 0
    
    def test_missing_artist_skipped(self, mocker):
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        
        csv_content = b"Artist,Title,Format,Released,release_id\n,Undertow,CD,2023,123"
        
        result = detect_artist_mappings(csv_content)
        
        assert result['mappings_found'] == 0
    
    def test_missing_discogs_id_skipped(self, mocker):
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        
        csv_content = b"Artist,Title,Format,Released\nTool,Undertow,CD,2023"
        
        result = detect_artist_mappings(csv_content)
        
        assert result['mappings_found'] == 0
