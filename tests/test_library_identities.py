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
"""

from michi.domain.library import make_album_key, make_artist_key


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
