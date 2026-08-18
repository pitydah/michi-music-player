"""LOCAL-META-02.2c canonical album/artist identity keys — Phase-1 RED tests.

On the current baseline the module-level imports of the new public key
functions fail at collection (ImportError) — that IS the expected Phase-1
red evidence. The tests encode the target contract and must pass once
michi/domain/library.py exposes ``make_album_key`` / ``make_artist_key``
(canonical identity API) and ``build_music_model`` groups albums by
``make_album_key(track.album, resolved_album_artist)``.

Coverage:
- make_album_key: casefold, inner-whitespace collapse, unicode determinism
- make_artist_key: whitespace/case normalization, deterministic
- The :: separator is part of the canonical format and survives normalization
  (collision resistance: distinct (album, artist) pairs stay distinct)

M6.1 additions (canonical music model v2 identity API): make_track_id (the
path IS the local track identity — plain str(Path(file_path)), NO casefold:
paths are case-sensitive), make_genre_key / make_composer_key (both
``_normalize_key`` semantics: casefold + whitespace collapse + strip). On the
current baseline the extended module-level import fails at collection
(ImportError) — that IS the expected Phase-1 red evidence.

Coverage (M6.1):
- make_track_id: deterministic per path, distinct paths -> distinct ids,
  path case matters (no casefold)
- make_genre_key / make_composer_key: normalization == equivalence
"""

from michi.domain.library import (
    make_album_key,
    make_artist_key,
    make_composer_key,
    make_genre_key,
    make_track_id,
)


class TestAlbumKeyIdentity:
    def test_make_album_key_normalized(self):
        assert make_album_key("Album One", "Artist A") == make_album_key(
            "album one", "artist a"
        )
        assert make_album_key("A  B", "X") == make_album_key("A B", "X")
        accent_key = make_album_key("Álbum", "Artista")
        assert accent_key == make_album_key("Álbum", "Artista")
        assert accent_key != make_album_key("Album", "Artista")

    def test_album_key_separator_collision_resistant(self):
        assert make_album_key("a::b", "c") != make_album_key("a", "b::c")


class TestArtistKeyIdentity:
    def test_make_artist_key(self):
        assert make_artist_key("  The  Band  ") == make_artist_key("the band")
        assert make_artist_key("the band") == make_artist_key("the band")


class TestTrackIdIdentity:
    """M6.1 — track identity: the path IS the local identity (plain string,
    deterministic, case-sensitive — no casefold)."""

    def test_make_track_id_deterministic(self):
        assert make_track_id("/m/a.flac") == make_track_id("/m/a.flac")
        assert make_track_id("/m/a.flac") != make_track_id("/m/b.flac")
        # Paths are case-sensitive: no casefold on the identity.
        assert make_track_id("/M/A.FLAC") != make_track_id("/m/a.flac")

    def test_make_track_id_is_plain_path_string(self):
        # str(Path(file_path)): the serialized identity IS the path itself.
        assert make_track_id("/m/a.flac") == "/m/a.flac"


class TestGenreAndComposerKeyIdentity:
    """M6.1 — genre/composer keys use ``_normalize_key`` semantics."""

    def test_make_genre_key_and_composer_key(self):
        assert make_genre_key(" Rock ") == make_genre_key("rock") == "rock"
        assert make_composer_key("John  Williams") == make_composer_key("john williams")
