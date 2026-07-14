from __future__ import annotations

import re
import unicodedata

from core.metadata.models import TrackMetadata, MetadataDocument


_MULTI_SPACE = re.compile(r"\s+")
_LEADING_TRAILING = re.compile(r"^\s+|\s+$")


class MetadataNormalizer:
    def __init__(self, unicode_form: str = "NFC",
                 collapse_whitespace: bool = True,
                 strip_punctuation: bool = False):
        self._unicode_form = unicode_form
        self._collapse = collapse_whitespace
        self._strip_punc = strip_punctuation

    def normalize_document(self, doc: MetadataDocument) -> MetadataDocument:
        normalized = MetadataDocument(
            source_path=doc.source_path,
            format=doc.format,
            track=self.normalize_track(doc.track),
            technical=doc.technical,
            artworks=doc.artworks,
            raw_fields=doc.raw_fields,
            warnings=list(doc.warnings),
        )
        return normalized

    def normalize_track(self, track: TrackMetadata) -> TrackMetadata:
        t = TrackMetadata(
            title=self._normalize_text(track.title),
            artists=[self._normalize_text(a) for a in track.artists],
            album=self._normalize_text(track.album),
            album_artist=self._normalize_text(track.album_artist),
            track_number=track.track_number,
            track_total=track.track_total,
            disc_number=track.disc_number,
            disc_total=track.disc_total,
            date=self._normalize_text(track.date),
            original_date=self._normalize_text(track.original_date),
            release_year=self._parse_year(track.date) if track.release_year is None else track.release_year,
            genres=[self._normalize_text(g) for g in track.genres],
            composer=self._normalize_text(track.composer),
            performers=track.performers,
            conductor=self._normalize_text(track.conductor),
            lyricist=self._normalize_text(track.lyricist),
            comment=track.comment,
            copyright_=track.copyright_,
            publisher=self._normalize_text(track.publisher),
            label=self._normalize_text(track.label),
            bpm=track.bpm,
            key=track.key,
            language=self._normalize_text(track.language),
            compilation=track.compilation,
            isrc=self._normalize_isrc(track.isrc),
            barcode=self._normalize_text(track.barcode),
            catalog_number=self._normalize_text(track.catalog_number),
            musicbrainz_recording_id=self._normalize_mbid(track.musicbrainz_recording_id),
            musicbrainz_release_id=self._normalize_mbid(track.musicbrainz_release_id),
            musicbrainz_release_group_id=self._normalize_mbid(track.musicbrainz_release_group_id),
            musicbrainz_artist_ids=[self._normalize_mbid(a) for a in track.musicbrainz_artist_ids],
            musicbrainz_album_artist_ids=[self._normalize_mbid(a) for a in track.musicbrainz_album_artist_ids],
            acoustid_id=self._normalize_text(track.acoustid_id),
            replaygain_track_gain=track.replaygain_track_gain,
            replaygain_track_peak=track.replaygain_track_peak,
            replaygain_album_gain=track.replaygain_album_gain,
            replaygain_album_peak=track.replaygain_album_peak,
            r128_track_gain=track.r128_track_gain,
            r128_album_gain=track.r128_album_gain,
            lyrics=track.lyrics,
            custom_fields=dict(track.custom_fields),
        )
        return t

    def _normalize_text(self, text: str) -> str:
        if not text:
            return text
        text = unicodedata.normalize(self._unicode_form, text)
        if self._collapse:
            text = _MULTI_SPACE.sub(" ", text)
        text = _LEADING_TRAILING.sub("", text)
        return text

    def _normalize_isrc(self, isrc: str) -> str:
        if not isrc:
            return isrc
        return isrc.strip().upper()

    def _normalize_mbid(self, mbid: str) -> str:
        if not mbid:
            return mbid
        return mbid.strip().lower()

    @staticmethod
    def _parse_year(date_str: str) -> int | None:
        if not date_str:
            return None
        m = re.match(r"(\d{4})", date_str)
        if m:
            return int(m.group(1))
        return None

    @staticmethod
    def suggested_display_value(original: str, normalized: str) -> str:
        if original and original != normalized:
            return original
        return normalized
