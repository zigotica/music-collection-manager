import pytest
import sys
sys.path.insert(0, '/Users/hanzonian/Documents/personal/music-library')

from app.services.import_csv import parse_discogs_csv


class TestParseDiscogsCsv:
    def test_import_single_album(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        mock_album_create = mocker.patch('app.services.import_csv.Album.create')
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool,Undertow,CD,2023,123456"
        
        result = parse_discogs_csv(csv_content)
        
        assert result['imported'] == 1
        mock_album_create.assert_called_once()
        call_kwargs = mock_album_create.call_args[1]
        assert call_kwargs['title'] == 'Undertow'
        assert call_kwargs['artist'] == 'Tool'
        assert call_kwargs['discogs_id'] == '123456'
    
    def test_import_multiple_albums(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        mock_album_create = mocker.patch('app.services.import_csv.Album.create')
        
        csv_content = b"""Artist,Title,Format,Released,release_id
Tool,Undertow,CD,2023,123
Tool,Fear Inoculum,CD,2023,456"""
        
        result = parse_discogs_csv(csv_content)
        
        assert result['imported'] == 2
    
    def test_skip_duplicate_by_discogs_id(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_existing = mocker.MagicMock()
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = mock_existing
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool,Undertow,CD,2023,123"
        
        result = parse_discogs_csv(csv_content)
        
        assert result['imported'] == 0
        assert len(result['skipped_duplicates']) == 1
    
    def test_skip_missing_artist(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        
        csv_content = b"Artist,Title,Format,Released,release_id\n,Undertow,CD,2023,123"
        
        result = parse_discogs_csv(csv_content)
        
        assert result['imported'] == 0
        assert len(result['skipped_missing']) == 1
    
    def test_skip_missing_title(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool,,CD,2023,123"
        
        result = parse_discogs_csv(csv_content)
        
        assert result['imported'] == 0
        assert len(result['skipped_missing']) == 1
    
    def test_applies_artist_mapping(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        mock_album_create = mocker.patch('app.services.import_csv.Album.create')
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool (2),Undertow,CD,2023,123"
        
        result = parse_discogs_csv(csv_content)
        
        assert result['imported'] == 1
        call_kwargs = mock_album_create.call_args[1]
        assert call_kwargs['artist'] == 'Tool'
    
    def test_import_wanted_album(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        mock_album_create = mocker.patch('app.services.import_csv.Album.create')
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool,Undertow,CD,2023,123"
        
        result = parse_discogs_csv(csv_content, is_wanted=True)
        
        assert result['imported'] == 1
        call_kwargs = mock_album_create.call_args[1]
        assert call_kwargs['is_wanted'] == True
    
    def test_maps_format_cd(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        mock_album_create = mocker.patch('app.services.import_csv.Album.create')
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool,Undertow,CD,2023,123"
        
        result = parse_discogs_csv(csv_content)
        
        call_kwargs = mock_album_create.call_args[1]
        assert call_kwargs['physical_format'] == 'CD'
    
    def test_maps_format_vinyl(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        mock_album_create = mocker.patch('app.services.import_csv.Album.create')
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool,Undertow,12\" Vinyl,2023,123"
        
        result = parse_discogs_csv(csv_content)
        
        call_kwargs = mock_album_create.call_args[1]
        assert call_kwargs['physical_format'] == 'Vinyl'
    
    def test_stores_discogs_year(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        mock_album_create = mocker.patch('app.services.import_csv.Album.create')
        
        csv_content = b"Artist,Title,Format,Released,release_id\nTool,Undertow,CD,2023-11-15,123"
        
        result = parse_discogs_csv(csv_content)
        
        call_kwargs = mock_album_create.call_args[1]
        assert call_kwargs['year_discogs_release'] == 2023
        assert call_kwargs['year'] is None
    
    def test_stores_notes(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        mock_album_create = mocker.patch('app.services.import_csv.Album.create')
        
        csv_content = b"Artist,Title,Format,Released,release_id,Notes\nTool,Undertow,CD,2023,123,First pressing"
        
        result = parse_discogs_csv(csv_content)
        
        call_kwargs = mock_album_create.call_args[1]
        assert call_kwargs['notes'] == 'First pressing'
    
    def test_empty_notes_becomes_none(self, mocker):
        mocker.patch('app.services.import_csv.detect_artist_mappings')
        mock_album_select = mocker.patch('app.services.import_csv.Album.select')
        mock_album_select.return_value.where.return_value.first.return_value = None
        mock_album_create = mocker.patch('app.services.import_csv.Album.create')
        
        csv_content = b"Artist,Title,Format,Released,release_id,Notes\nTool,Undertow,CD,2023,123,"
        
        result = parse_discogs_csv(csv_content)
        
        call_kwargs = mock_album_create.call_args[1]
        assert call_kwargs['notes'] is None
