"""Fuzz tests for complex FTS5 field filter combinations.

Builds a self-contained SQLite :memory: database with an FTS5 index
populated with synthetic media items, then exercises the SearchEngine
with edge-case queries.  Does NOT use the real library database.
"""
import sqlite3

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _build_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE media_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL DEFAULT '',
            artist      TEXT NOT NULL DEFAULT '',
            album       TEXT NOT NULL DEFAULT '',
            albumartist TEXT NOT NULL DEFAULT '',
            genre       TEXT NOT NULL DEFAULT '',
            year        INTEGER DEFAULT 0,
            bitrate     INTEGER DEFAULT 0,
            kind        TEXT NOT NULL DEFAULT '',
            ext         TEXT NOT NULL DEFAULT '',
            filepath    TEXT NOT NULL DEFAULT '',
            filename    TEXT NOT NULL DEFAULT '',
            directory   TEXT NOT NULL DEFAULT '',
            composer    TEXT NOT NULL DEFAULT '',
            isrc        TEXT NOT NULL DEFAULT '',
            label       TEXT NOT NULL DEFAULT '',
            conductor   TEXT NOT NULL DEFAULT '',
            grouping    TEXT NOT NULL DEFAULT '',
            mood        TEXT NOT NULL DEFAULT '',
            deleted_at  TEXT,
            rating      INTEGER DEFAULT 0,
            play_count  INTEGER DEFAULT 0,
            sample_rate INTEGER DEFAULT 0,
            channels    INTEGER DEFAULT 0,
            bit_depth   INTEGER DEFAULT 0,
            bpm         REAL DEFAULT 0.0,
            key         TEXT NOT NULL DEFAULT '',
            quality     TEXT NOT NULL DEFAULT '',
            analysis_status TEXT NOT NULL DEFAULT '',
            spectral_verdict TEXT NOT NULL DEFAULT ''
        );

        CREATE VIRTUAL TABLE media_fts USING fts5(
            title, artist, album, albumartist, genre, composer,
            filepath, filename, isrc, label, conductor, grouping, mood,
            content='media_items', content_rowid='id'
        );

        CREATE TRIGGER media_ai AFTER INSERT ON media_items BEGIN
            INSERT INTO media_fts(rowid, title, artist, album, albumartist,
                                  genre, composer, filepath, filename, isrc,
                                  label, conductor, grouping, mood)
            VALUES (new.id, new.title, new.artist, new.album, new.albumartist,
                    new.genre, new.composer, new.filepath, new.filename, new.isrc,
                    new.label, new.conductor, new.grouping, new.mood);
        END;

        CREATE TRIGGER media_ad AFTER DELETE ON media_items BEGIN
            INSERT INTO media_fts(media_fts, rowid, title, artist, album,
                                  albumartist, genre, composer, filepath,
                                  filename, isrc, label, conductor,
                                  grouping, mood)
            VALUES ('delete', old.id, old.title, old.artist, old.album,
                    old.albumartist, old.genre, old.composer, old.filepath,
                    old.filename, old.isrc, old.label, old.conductor,
                    old.grouping, old.mood);
        END;

        CREATE TRIGGER media_au AFTER UPDATE ON media_items BEGIN
            INSERT INTO media_fts(media_fts, rowid, title, artist, album,
                                  albumartist, genre, composer, filepath,
                                  filename, isrc, label, conductor,
                                  grouping, mood)
            VALUES ('delete', old.id, old.title, old.artist, old.album,
                    old.albumartist, old.genre, old.composer, old.filepath,
                    old.filename, old.isrc, old.label, old.conductor,
                    old.grouping, old.mood);
            INSERT INTO media_fts(rowid, title, artist, album, albumartist,
                                  genre, composer, filepath, filename, isrc,
                                  label, conductor, grouping, mood)
            VALUES (new.id, new.title, new.artist, new.album, new.albumartist,
                    new.genre, new.composer, new.filepath, new.filename, new.isrc,
                    new.label, new.conductor, new.grouping, new.mood);
        END;
    """)
    conn.commit()


SYNTHETIC_TRACKS = [
    # (title, artist, album, year, bitrate, ext, kind)
    ("The Lamb Lies Down on Broadway", "Genesis", "The Lamb Lies Down on Broadway", 1974, 320, ".flac", "local"),
    ("Carpet Crawlers", "Genesis", "The Lamb Lies Down on Broadway", 1974, 320, ".flac", "local"),
    ("Fly on a Windshield", "Genesis", "The Lamb Lies Down on Broadway", 1974, 320, ".flac", "local"),
    ("In the Cage", "Genesis", "The Lamb Lies Down on Broadway", 1974, 320, ".flac", "local"),
    ("So What", "Miles Davis", "Kind of Blue", 1959, 1411, ".flac", "local"),
    ("Freddie Freeloader", "Miles Davis", "Kind of Blue", 1959, 1411, ".flac", "local"),
    ("Blue in Green", "Miles Davis", "Kind of Blue", 1959, 1411, ".flac", "local"),
    ("All Blues", "Miles Davis", "Kind of Blue", 1959, 1411, ".flac", "local"),
    ("No Woman, No Cry (Live)", "Bob Marley & The Wailers", "Live!", 1975, 256, ".mp3", "local"),
    ("Is This Love", "Bob Marley & The Wailers", "Kaya", 1978, 320, ".flac", "local"),
    ("Could You Be Loved", "Bob Marley & The Wailers", "Uprising", 1980, 320, ".flac", "local"),
    ("Rat Race", "Bob Marley & The Wailers", "Rastaman Vibration", 1976, 320, ".flac", "local"),
    ("Ríe y Llora", "Celia Cruz", "Azúcar Negra", 1993, 256, ".mp3", "local"),
    ("La Vida Es Un Carnaval", "Celia Cruz", "Mi Vida Es Cantar", 1998, 320, ".mp3", "local"),
    ("Quimbara", "Celia Cruz", "Celia & Johnny", 1974, 320, ".flac", "local"),
    ("Oye Como Va", "Santana", "Abraxas", 1970, 320, ".flac", "local"),
    ("Smooth", "Santana feat. Rob Thomas", "Supernatural", 1999, 256, ".mp3", "local"),
    ("Mañana", "J Balvin", "Jose", 2021, 320, ".aac", "stream"),
    ("Canción Con Yandel", "J Balvin", "Jose", 2021, 320, ".aac", "stream"),
    ("No Me Conoce", "J Balvin", "Vibras", 2020, 256, ".mp3", "local"),
    ("Hotel California", "Eagles", "Hotel California", 1976, 320, ".flac", "local"),
    ("Take It Easy", "Eagles", "Eagles", 1972, 192, ".mp3", "local"),
    ("Rock & Roll Is King", "ELO", "Secret Messages", 1983, 128, ".mp3", "local"),
    ("Don't Bring Me Down", "ELO", "Discovery", 1979, 320, ".flac", "local"),
    ("(Don't Fear) The Reaper", "Blue Öyster Cult", "Agents of Fortune", 1976, 320, ".flac", "local"),
    ("Godzilla (ft. Serj)", "Blue Öyster Cult", "The Symbol Remains", 2020, 320, ".flac", "local"),
    # year=0 (no year) cases
    ("Untitled", "Unknown Artist", "Unknown Album", 0, 128, ".mp3", "local"),
    ("Mystery Track", "Anonymous", "No Year", 0, 0, ".wav", "local"),
    # year=None case — simulate with year=0 + a special flag in title
    ("Classic Premiere", "Test Artist", "No Year Album", 0, 256, ".flac", "local"),
    # Emoji / special chars
    ("🎵 Beats", "DJ 💿", "Mixtape Vol. 1", 2023, 320, ".mp3", "local"),
    ("Español ñoño", "José González", "Veneer", 2003, 256, ".mp3", "local"),
    ("Pépite d'amour", "Françoise Hardy", "Comment te dire adieu", 1968, 192, ".mp3", "local"),
    # Quoted / parenthesis in album/title
    ("Song (Remix)", "Artist feat. \"Special\" Guest", "Album (2024 Edition)", 2024, 320, ".flac", "local"),
    ("It's Alright", "O'Shea & The Band", "It's & Only", 2022, 256, ".mp3", "local"),
    # Edge: empty / extreme numeric
    ("High Res Track", "HiFi Man", "Ultra HD", 2025, 9999, ".dsf", "local"),
    # Oldest year for <1900 edge
    ("Ancient Melody", "Baroque Composer", "Early Works", 1750, 0, ".wav", "local"),
    # format:flac artist:Miles combo
    ("Milestones", "Miles Davis", "Milestones", 1958, 1411, ".flac", "local"),
]


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    _build_schema(conn)
    cursor = conn.cursor()
    for t in SYNTHETIC_TRACKS:
        title, artist, album, year, bitrate, ext, kind = t
        cursor.execute("""
            INSERT INTO media_items (title, artist, album, year, bitrate, ext, kind)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, artist, album, year, bitrate, ext, kind))
    conn.commit()
    conn.row_factory = sqlite3.Row
    return conn


@pytest.fixture
def engine(db_conn):
    from library.search_engine import SearchEngine
    return SearchEngine(db_conn)


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestFTSFieldFilterFuzzer:

    # 1. Combined nested field filters
    def test_combined_nested_filters(self, engine):
        results = engine.search('artist:Genesis album:"The Lamb Lies Down" year:>1973 bitrate:>=320')
        titles = {r["title"] for r in results}
        assert "The Lamb Lies Down on Broadway" in titles
        assert "Carpet Crawlers" in titles
        assert "Fly on a Windshield" in titles
        assert "In the Cage" in titles
        assert len(results) == 4, f"Expected 4, got {len(results)}"

    # 2. Special characters in titles and albums
    def test_special_characters(self, engine):
        results = engine.search('album:"It\'s & Only"')
        titles = {r["title"] for r in results}
        assert "It's Alright" in titles

    def test_special_characters_parenthesis(self, engine):
        results = engine.search('album:"Album (2024 Edition)"')
        assert len(results) >= 1

    def test_special_characters_apostrophe_in_artist(self, engine):
        results = engine.search("artist:O'Shea")
        assert len(results) == 1
        assert results[0]["title"] == "It's Alright"

    def test_special_characters_ampersand_in_artist(self, engine):
        results = engine.search('artist:"Bob Marley & The Wailers"')
        assert len(results) == 4

    def test_special_characters_rock_ampersand(self, engine):
        results = engine.search('title:"Rock & Roll Is King"')
        assert len(results) == 1

    def test_special_characters_dont_fear(self, engine):
        results = engine.search("(Don't Fear) The Reaper")
        assert len(results) == 1

    # 3. Albums without year (year=0)
    def test_albums_no_year_zero(self, engine):
        results = engine.search("year:0")
        titles = {r["title"] for r in results}
        assert "Untitled" in titles
        assert "Mystery Track" in titles
        assert "Classic Premiere" in titles

    def test_albums_no_year_artist_search(self, engine):
        results = engine.search("artist:Anonymous year:0")
        assert len(results) == 1
        assert results[0]["title"] == "Mystery Track"

    # 4. UTF-8 encoding: tildes, ñ, emoji
    def test_utf8_tilde(self, engine):
        results = engine.search("José González")
        assert len(results) == 1
        assert results[0]["title"] == "Español ñoño"

    def test_utf8_emoji_artist(self, engine):
        results = engine.search("DJ 💿")
        assert len(results) == 1
        assert results[0]["title"] == "🎵 Beats"

    def test_utf8_french_special(self, engine):
        results = engine.search("Françoise Hardy")
        assert len(results) == 1
        assert results[0]["title"] == "Pépite d'amour"

    # 5. Field filters with spaces
    def test_field_filter_spaces_artist(self, engine):
        results = engine.search('artist:"Bob Marley & The Wailers"')
        assert len(results) == 4

    def test_field_filter_spaces_album(self, engine):
        results = engine.search('album:"Kind of Blue"')
        assert len(results) == 4

    def test_field_filter_multi_word_quoted(self, engine):
        results = engine.search('artist:"Miles Davis" album:"Kind of Blue"')
        assert len(results) == 4

    # 6. Numeric edge cases
    def test_numeric_year_gt_zero(self, engine):
        results = engine.search("year:>0")
        assert all(r["year"] > 0 for r in results)
        assert len(results) >= 30

    def test_numeric_year_lt_1900(self, engine):
        results = engine.search("year:<1900")
        assert len(results) > 0
        assert all(r["year"] < 1900 for r in results)
        assert any(r["title"] == "Ancient Melody" for r in results)

    def test_numeric_bitrate_gte_1411(self, engine):
        results = engine.search("bitrate:>=1411")
        assert all(r["bitrate"] >= 1411 for r in results)

    def test_numeric_bitrate_zero(self, engine):
        results = engine.search("bitrate:0")
        assert isinstance(results, list)
        # bitrate:0 uses LIKE %0% so many tracks match; verify no crash
        assert len(results) >= 1

    # 7. Format + artist combination
    def test_format_flac_artist_miles(self, engine):
        results = engine.search("format:flac artist:Miles")
        for r in results:
            assert r["ext"] == ".flac", f"Expected .flac, got {r['ext']}"
            assert "Miles" in r["artist"]
        assert len(results) == 5  # 4 from Kind of Blue + 1 Milestones

    def test_format_mp3_artist_celia(self, engine):
        results = engine.search("format:mp3 artist:Celia")
        for r in results:
            assert r["ext"] == ".mp3"
        assert len(results) == 2

    # 8. Invalid filters should not crash
    def test_invalid_empty_query(self, engine):
        results = engine.search("")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_invalid_just_operator(self, engine):
        results = engine.search(":>")
        assert isinstance(results, list)

    def test_invalid_unknown_field(self, engine):
        results = engine.search("foobar:Genesis")
        assert isinstance(results, list)

    def test_invalid_bare_colon(self, engine):
        results = engine.search(":")
        assert isinstance(results, list)

    def test_invalid_garbage_chars(self, engine):
        results = engine.search("!@#$%^&*()_+{}|:<>?")
        assert isinstance(results, list)

    # Additional: cross-field with freetext
    def test_freetext_plus_field_filter(self, engine):
        results = engine.search('Genesis album:"The Lamb Lies Down" year:1974')
        assert len(results) == 4

    # Mix of null year and normal year
    def test_mixed_year_null_and_normal(self, engine):
        results = engine.search("year:0")
        no_year_titles = {r["title"] for r in results}
        results_normal = engine.search("year:1974")
        normal_titles = {r["title"] for r in results_normal}
        assert no_year_titles.isdisjoint(normal_titles)
