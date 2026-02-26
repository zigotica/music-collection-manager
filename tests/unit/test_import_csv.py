import pytest
import sys
sys.path.insert(0, '/Users/hanzonian/Documents/personal/music-library')

from app.services.import_csv import map_format


class TestMapFormat:
    def test_cd_album(self):
        assert map_format("CD, Album") == "CD"
    
    def test_cd_single(self):
        assert map_format("CD, Single") == "CD"
    
    def test_lp_vinyl(self):
        assert map_format("LP, Vinyl") == "Vinyl"
    
    def test_12_vinyl(self):
        assert map_format('12" Vinyl') == "Vinyl"
    
    def test_cassette(self):
        assert map_format("Cassette") == "Tape"
    
    def test_cass_album(self):
        assert map_format("Cass, Album") == "Tape"
    
    def test_dvd(self):
        assert map_format("DVD, Album") == "DVD"
    
    def test_bluray(self):
        assert map_format("Blu-ray") == "Blu-ray"
    
    def test_7_inch_single(self):
        assert map_format('7"') == "EP - Single"
    
    def test_ep(self):
        assert map_format("EP") == "EP - Single"
    
    def test_maxi_single(self):
        assert map_format("Maxi-Single") == "EP - Single"
    
    def test_unknown_format(self):
        assert map_format("Unknown Format") == "Unknown Format"
    
    def test_empty_string(self):
        assert map_format("") is None
    
    def test_none_input(self):
        assert map_format(None) is None
    
    def test_vinyl_remix(self):
        assert map_format("Vinyl, Remix") == "Vinyl"
    
    def test_cd_reissue(self):
        assert map_format("CD, Reissue") == "CD"
    
    def test_2xcd_compilation(self):
        assert map_format("2xCD, Comp") == "CD"
    
    def test_3xlp_boxset(self):
        assert map_format("3xLP, Box Set") == "Vinyl"
