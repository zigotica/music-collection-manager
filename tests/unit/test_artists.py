import pytest
import sys
sys.path.insert(0, '/Users/hanzonian/Documents/personal/music-library')

from app.utils.artists import split_artists, strip_discogs_suffix, join_artists, sanitize_filename


class TestSanitizeFilename:
    def test_normal_name(self):
        assert sanitize_filename("Tool") == "Tool"
    
    def test_question_mark(self):
        assert sanitize_filename("Is That You?") == "Is That You"
    
    def test_parentheses(self):
        assert sanitize_filename("Album (2023)") == "Album 2023"
    
    def test_ellipsis(self):
        assert sanitize_filename("Album...") == "Album"
    
    def test_accents_converted(self):
        assert sanitize_filename("João Gilberto") == "Joao Gilberto"
    
    def test_spanish_accents(self):
        assert sanitize_filename("El Camarón De La Isla con la colaboración") == "El Camaron De La Isla con la colaboracion"
    
    def test_special_chars_removed(self):
        assert sanitize_filename("Album (2023) - Special!") == "Album 2023 - Special"


class TestSplitArtists:
    def test_single_artist(self):
        assert split_artists("Tool") == ["Tool"]
    
    def test_slash_separator(self):
        assert split_artists("John Lennon / The Plastic Ono Band") == ["John Lennon", "The Plastic Ono Band"]
    
    def test_plus_separator(self):
        assert split_artists("Artist + Another Artist") == ["Artist", "Another Artist"]
    
    def test_middle_dot_separator(self):
        assert split_artists("Artist · Another Artist") == ["Artist", "Another Artist"]
    
    def test_bullet_separator(self):
        assert split_artists("Artist ∙ Another Artist") == ["Artist", "Another Artist"]
    
    def test_dash_separator(self):
        assert split_artists("John McLaughlin - Al Di Meola - Paco De Lucía") == ["John McLaughlin", "Al Di Meola", "Paco De Lucía"]
    
    def test_comma_space_separator(self):
        assert split_artists("Coleman Hawkins, Ben Webster") == ["Coleman Hawkins", "Ben Webster"]
    
    def test_comma_space_multiple_artists(self):
        assert split_artists("John Lennon, Paul McCartney, George Harrison") == ["John Lennon", "Paul McCartney", "George Harrison"]
    
    def test_jr_suffix_single_artist(self):
        assert split_artists("Grover Washington, Jr.") == ["Grover Washington Jr."]
    
    def test_sr_suffix_single_artist(self):
        assert split_artists("Mickey Rooney, Sr.") == ["Mickey Rooney Sr."]
    
    def test_jr_suffix_lowercase(self):
        assert split_artists("Artist, jr.") == ["Artist jr."]
    
    def test_jr_suffix_mixed_case(self):
        assert split_artists("Artist, JR.") == ["Artist JR."]
    
    def test_jr_suffix_with_other_artists(self):
        assert split_artists("John Lennon, Grover Washington, Jr.") == ["John Lennon", "Grover Washington Jr."]
    
    def test_jr_suffix_first_position(self):
        assert split_artists("Grover Washington, Jr., John Lennon") == ["Grover Washington Jr.", "John Lennon"]
    
    def test_comma_then_featuring_split(self):
        assert split_artists("Stan Getz / João Gilberto Featuring Antonio Carlos Jobim") == ["Stan Getz", "João Gilberto", "Antonio Carlos Jobim"]
    
    def test_comma_then_featuring_with_slash(self):
        assert split_artists("Artist A, Artist B Featuring Artist C") == ["Artist A", "Artist B", "Artist C"]
    
    def test_feat_period(self):
        assert split_artists("Artist feat. Another Artist") == ["Artist", "Another Artist"]
    
    def test_feat_without_period(self):
        assert split_artists("Artist feat Another Artist") == ["Artist", "Another Artist"]
    
    def test_featuring(self):
        assert split_artists("Artist Featuring Another Artist") == ["Artist", "Another Artist"]
    
    def test_ft_period(self):
        assert split_artists("Artist ft. Another Artist") == ["Artist", "Another Artist"]
    
    def test_ft_without_period(self):
        assert split_artists("Artist ft Another Artist") == ["Artist", "Another Artist"]
    
    def test_with_preserved(self):
        assert split_artists("The Beatles With Tony Sheridan") == ["The Beatles With Tony Sheridan"]
    
    def test_empty_string(self):
        assert split_artists("") == []
    
    def test_none_input(self):
        assert split_artists(None) == []
    
    def test_whitespace_only(self):
        assert split_artists("   ") == []


class TestStripDiscogsSuffix:
    def test_single_digit(self):
        assert strip_discogs_suffix("Tool (2)") == "Tool"
    
    def test_double_digit(self):
        assert strip_discogs_suffix("Geese (11)") == "Geese"
    
    def test_triple_digit(self):
        assert strip_discogs_suffix("Artist (111)") == "Artist"
    
    def test_no_suffix(self):
        assert strip_discogs_suffix("Tool") == "Tool"
    
    def test_suffix_with_spaces(self):
        assert strip_discogs_suffix("Artist (2) ") == "Artist"
    
    def test_multiple_parens_at_end(self):
        assert strip_discogs_suffix("Artist (2) (3)") == "Artist (2)"
    
    def test_year_pattern(self):
        assert strip_discogs_suffix("Album (2023)") == "Album"
        assert strip_discogs_suffix("Album (1999)") == "Album"
        assert strip_discogs_suffix("Artist (1985)") == "Artist"
    
    def test_year_pattern_preserves_other_dashes(self):
        assert strip_discogs_suffix("Artist - Album (2023)") == "Artist - Album"


class TestJoinArtists:
    def test_two_artists(self):
        assert join_artists(["John Lennon", "The Plastic Ono Band"]) == "John Lennon, The Plastic Ono Band"
    
    def test_single_artist(self):
        assert join_artists(["Tool"]) == "Tool"
    
    def test_empty_list(self):
        assert join_artists([]) == ""
    
    def test_multiple_artists(self):
        assert join_artists(["A", "B", "C"]) == "A, B, C"


class TestApplyArtistMapping:
    def test_single_artist_no_mapping(self, mocker):
        from app.utils.artists import apply_artist_mapping
        
        mock_select = mocker.patch('app.models.ArtistMapping.select')
        mock_select.return_value.where.return_value.first.return_value = None
        
        result = apply_artist_mapping("Tool")
        assert result == "Tool"
    
    def test_artist_with_discogs_suffix_creates_mapping(self, mocker):
        from app.utils.artists import apply_artist_mapping
        
        mock_select = mocker.patch('app.models.ArtistMapping.select')
        mock_select.return_value.where.return_value.first.return_value = None
        mock_create = mocker.patch('app.models.ArtistMapping.create')
        
        result = apply_artist_mapping("Tool (2)")
        assert result == "Tool"
        mock_create.assert_called_once_with(original_name="Tool (2)", new_name="Tool")
    
    def test_artist_mapping_from_db(self, mocker):
        from app.utils.artists import apply_artist_mapping
        
        mock_mapping = mocker.MagicMock()
        mock_mapping.new_name = "The Tool"
        
        mock_select = mocker.patch('app.models.ArtistMapping.select')
        mock_select.return_value.where.return_value.first.return_value = mock_mapping
        
        result = apply_artist_mapping("Tool")
        assert result == "The Tool"
    
    def test_multiple_artists_split_and_map(self, mocker):
        from app.utils.artists import apply_artist_mapping
        
        mock_select = mocker.patch('app.models.ArtistMapping.select')
        mock_select.return_value.where.return_value.first.return_value = None
        
        result = apply_artist_mapping("John Lennon, Paul McCartney")
        assert result == "John Lennon, Paul McCartney"
    
    def test_combined_suffix_and_db_mapping(self, mocker):
        from app.utils.artists import apply_artist_mapping
        
        mock_mapping = mocker.MagicMock()
        mock_mapping.new_name = "The Beatles"
        
        mock_select = mocker.patch('app.models.ArtistMapping.select')
        mock_select.return_value.where.return_value.first.return_value = mock_mapping
        
        result = apply_artist_mapping("The Beatles (2)")
        assert result == "The Beatles"
    
    def test_slash_separated_artists(self, mocker):
        from app.utils.artists import apply_artist_mapping
        
        mock_select = mocker.patch('app.models.ArtistMapping.select')
        mock_select.return_value.where.return_value.first.return_value = None
        
        result = apply_artist_mapping("John Lennon / Paul McCartney")
        assert result == "John Lennon, Paul McCartney"
