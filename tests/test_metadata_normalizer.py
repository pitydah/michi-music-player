"""Tests for infer_metadata_from_filename."""
from library.metadata_normalizer import infer_metadata_from_filename


class TestInferMetadataFromFilename:
    def test_simple_artist_title(self):
        r = infer_metadata_from_filename("/music/Depeche Mode - Shake the Disease.mp3")
        assert r["artist"] == "Depeche Mode"
        assert r["title"] == "Shake the Disease"

    def test_simple_artist_title_2(self):
        r = infer_metadata_from_filename("/music/Toto - Straight for the Heart.mp3")
        assert r["artist"] == "Toto"
        assert r["title"] == "Straight for the Heart"

    def test_simple_artist_title_3(self):
        r = infer_metadata_from_filename("/music/Duran Duran - The Reflex.mp3")
        assert r["artist"] == "Duran Duran"
        assert r["title"] == "The Reflex"

    def test_track_number_prefix_hyphen(self):
        r = infer_metadata_from_filename("/music/01 - Depeche Mode - Shake the Disease.mp3")
        assert r["track_number"] == 1
        assert r["artist"] == "Depeche Mode"
        assert r["title"] == "Shake the Disease"

    def test_track_number_prefix_dot(self):
        r = infer_metadata_from_filename("/music/3. Toto - Africa.flac")
        assert r["track_number"] == 3
        assert r["artist"] == "Toto"
        assert r["title"] == "Africa"

    def test_no_separator(self):
        r = infer_metadata_from_filename("/music/Archivo sin separador.mp3")
        assert r["artist"] == ""
        assert r["title"] == "Archivo sin separador"

    def test_en_dash(self):
        r = infer_metadata_from_filename("/music/Artist\u2013Title.mp3")
        assert r["artist"] == "Artist"
        assert r["title"] == "Title"

    def test_em_dash(self):
        r = infer_metadata_from_filename("/music/Artist\u2014Title.mp3")
        assert r["artist"] == "Artist"
        assert r["title"] == "Title"

    def test_pipe_separator(self):
        r = infer_metadata_from_filename("/music/Artist | Title.ogg")
        assert r["artist"] == "Artist"
        assert r["title"] == "Title"

    def test_underscore(self):
        r = infer_metadata_from_filename("/music/Artist_Title.wav")
        assert r["artist"] == "Artist"
        assert r["title"] == "Title"

    def test_track_number_underscore(self):
        r = infer_metadata_from_filename("/music/01_Depeche Mode - Shake the Disease.mp3")
        assert r["track_number"] == 1
        assert r["artist"] == "Depeche Mode"
        assert r["title"] == "Shake the Disease"
