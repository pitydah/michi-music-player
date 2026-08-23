"""M6.9-BACKEND-R1.1 — real Mutagen identity-hint extraction coverage.

Uses REAL mutagen tag classes/objects (mutagen 1.47 semantics — no
fakes): Vorbis VComment, ID3 TXXX+UFID (real Picard representations),
MP4 freeform atoms (bytes), ASF keys. Every role keeps ALL distinct
observations; role separation is permanent.
"""

from mutagen.id3 import ID3, TXXX, UFID
from mutagen.mp4 import MP4, MP4FreeForm
from mutagen.oggvorbis import VCommentDict

from michi.domain.enrichment import (
    AlbumIdentityHints,
    ArtistIdentityHints,
    ExternalIdentityHints,
)
from michi.infrastructure.enrichment_identity_hints import (
    MutagenIdentityHintExtractor,
)

EXTRACTOR = MutagenIdentityHintExtractor()


class TestVorbisFamily:
    def test_full_role_set(self):
        tags = VCommentDict()
        for key in (
            "MUSICBRAINZ_ARTISTID",
            "MUSICBRAINZ_ALBUMARTISTID",
            "MUSICBRAINZ_RELEASEGROUPID",
            "MUSICBRAINZ_ALBUMID",
            "MUSICBRAINZ_RECORDINGID",
            "MUSICBRAINZ_TRACKID",
            "MUSICBRAINZ_RELEASETRACKID",
        ):
            tags[key] = [f"{key}-value"]
        hints = EXTRACTOR.extract_hints_from_tags(tags)
        assert hints.musicbrainz_artist_ids == ("MUSICBRAINZ_ARTISTID-value",)
        assert hints.musicbrainz_album_artist_ids == (
            "MUSICBRAINZ_ALBUMARTISTID-value",
        )
        assert hints.musicbrainz_release_group_ids == (
            "MUSICBRAINZ_RELEASEGROUPID-value",
        )
        assert hints.musicbrainz_release_ids == ("MUSICBRAINZ_ALBUMID-value",)
        assert hints.musicbrainz_recording_ids == ("MUSICBRAINZ_RECORDINGID-value",)
        assert hints.musicbrainz_release_track_ids == (
            "MUSICBRAINZ_RELEASETRACKID-value",
        )

    def test_same_role_conflict_preserved(self):
        tags = VCommentDict()
        tags["MUSICBRAINZ_ARTISTID"] = ["mb-a", "mb-a", "mb-b"]
        hints = EXTRACTOR.extract_hints_from_tags(tags)
        # Distinct values preserved — never first-wins.
        assert hints.musicbrainz_artist_ids == ("mb-a", "mb-b")

    def test_role_separation(self):
        tags = VCommentDict()
        tags["MUSICBRAINZ_ARTISTID"] = ["mb-artist"]
        tags["MUSICBRAINZ_ALBUMARTISTID"] = ["mb-album-artist"]
        hints = EXTRACTOR.extract_hints_from_tags(tags)
        artist = ArtistIdentityHints.from_file_hints(hints)
        album = AlbumIdentityHints.from_file_hints(hints)
        assert artist.artist_ids == ("mb-artist",)
        assert album.album_artist_ids == ("mb-album-artist",)


class TestID3Family:
    def _id3_tags(self):
        tags = ID3()
        tags.add(TXXX(encoding=3, desc="MusicBrainz Artist Id", text="mb-artist-1"))
        tags.add(
            TXXX(
                encoding=3,
                desc="MusicBrainz Release Group Id",
                text=["rg-1", "rg-2"],
            )
        )
        tags.add(UFID(owner="http://musicbrainz.org", data=b"mb-recording-1"))
        return tags

    def test_txxx_and_ufid_extracted(self):
        hints = EXTRACTOR.extract_hints_from_tags(self._id3_tags())
        assert hints.musicbrainz_artist_ids == ("mb-artist-1",)
        assert hints.musicbrainz_release_group_ids == ("rg-1", "rg-2")
        assert hints.musicbrainz_recording_ids == ("mb-recording-1",)

    def test_foreign_ufid_owner_ignored(self):
        tags = ID3()
        tags.add(UFID(owner="https://example.org/other", data=b"x"))
        hints = EXTRACTOR.extract_hints_from_tags(tags)
        assert hints.musicbrainz_recording_ids == ()

    def test_id3_empty_when_no_mb_frames(self):
        hints = EXTRACTOR.extract_hints_from_tags(ID3())
        assert hints == ExternalIdentityHints()


class TestMP4Family:
    def _mp4_tags(self):
        tags = MP4()
        tags["----:com.apple.iTunes:MusicBrainz Artist Id"] = [
            MP4FreeForm(b"mb-artist-1")
        ]
        tags["----:com.apple.iTunes:MusicBrainz Album Id"] = [
            MP4FreeForm(b"mb-release-1")
        ]
        tags["----:com.apple.iTunes:MusicBrainz Release Group Id"] = [
            MP4FreeForm(b"rg-1")
        ]
        return tags

    def test_freeform_atoms_extracted(self):
        hints = EXTRACTOR.extract_hints_from_tags(self._mp4_tags())
        assert hints.musicbrainz_artist_ids == ("mb-artist-1",)
        assert hints.musicbrainz_release_ids == ("mb-release-1",)
        assert hints.musicbrainz_release_group_ids == ("rg-1",)


class TestASFFamily:
    """ASF/WMA: a real ASF container cannot be fabricated with mutagen
    (ASFHeaderError on placeholder files) and the repository has no WMA
    fixture — the production KEY MAPPING (the real adapter logic for
    ASF keys) is tested at the mapping seam; the container path yields
    EMPTY hints when unreadable."""

    def test_asf_key_mapping(self):
        from michi.infrastructure.enrichment_identity_hints import (
            _role_for_key,
        )

        assert _role_for_key("MusicBrainz/Artist Id") == "artist_ids"
        assert _role_for_key("MusicBrainz/Album Artist Id") == "album_artist_ids"
        assert _role_for_key("MusicBrainz/Album Id") == "release_ids"
        assert _role_for_key("MusicBrainz/Release Group Id") == "release_group_ids"
        assert _role_for_key("MusicBrainz/Release Track Id") == "release_track_ids"
        assert _role_for_key("Title") is None

    def test_unreadable_container_yields_empty_hints(self, tmp_path):
        # A non-audio file is unreadable by Mutagen: empty hints, never
        # an error for the scan.
        bogus = tmp_path / "song.mp3"
        bogus.write_bytes(b"not an audio file")
        hints = EXTRACTOR.extract_hints(bogus)
        assert hints == ExternalIdentityHints()


class TestBytesAndWhitespaceHygiene:
    def test_bytes_duplicates_and_whitespace(self):
        tags = MP4()
        tags["----:com.apple.iTunes:MusicBrainz Artist Id"] = [
            MP4FreeForm(b" mb-a "),
            MP4FreeForm(b"mb-a"),
            MP4FreeForm(b""),
            MP4FreeForm(b"mb-b"),
        ]
        hints = EXTRACTOR.extract_hints_from_tags(tags)
        assert hints.musicbrainz_artist_ids == ("mb-a", "mb-b")
