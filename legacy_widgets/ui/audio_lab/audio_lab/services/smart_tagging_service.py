"""Smart Tagging service — MusicBrainz-powered metadata suggestions with confidence scoring."""

from __future__ import annotations

import logging
from typing import Any

from ui.audio_lab.models import TagSuggestion, TrackMetadata

logger = logging.getLogger("michi.audio_lab.smart_tagging")


class SmartTaggingService:
    def __init__(self):
        self._kb = None

    def _get_kb(self):
        if self._kb is None:
            try:
                from integrations.knowledge_broker.service import KnowledgeBrokerService
                self._kb = KnowledgeBrokerService()
            except Exception as e:
                logger.warning("KnowledgeBroker not available: %s", e)
                self._kb = None
        return self._kb

    def suggest_for_track(self, track: TrackMetadata) -> list[TagSuggestion]:
        suggestions: list[TagSuggestion] = []

        kb = self._get_kb()
        if kb is None:
            return suggestions

        if track.artist:
            art_result = kb.lookup_artist(track.artist)
            if art_result.get("data"):
                art_data = art_result["data"].get("data", art_result["data"])
                art_name = art_data.get("name", "")
                if art_name and art_name.lower() != track.artist.lower():
                    suggestions.append(TagSuggestion(
                        field="artist", current=track.artist,
                        suggested=art_name,
                        confidence=0.90 if art_name.lower() == track.artist.lower() else 0.85,
                        source="musicbrainz", apply=False,
                    ))

        if track.artist and track.title:
            rec_result = kb.lookup_recording(track.title, track.artist)
            if rec_result.get("data"):
                rec_data = rec_result["data"].get("data", rec_result["data"])
                mb_title = rec_data.get("title", "")
                mb_isrc = rec_data.get("isrc", "")
                if mb_title and mb_title.lower() != track.title.lower():
                    suggestions.append(TagSuggestion(
                        field="title", current=track.title,
                        suggested=mb_title, confidence=0.82,
                        source="musicbrainz", apply=False,
                    ))
                if mb_isrc and not track.title:  # ISRC only for empty tracks
                    suggestions.append(TagSuggestion(
                        field="isrc", current="",
                        suggested=mb_isrc, confidence=0.88,
                        source="musicbrainz", apply=False,
                    ))

        return suggestions

    def suggest_for_album(self, artist: str, album: str,
                          track_list: list[TrackMetadata] | None = None) -> list[TagSuggestion]:
        suggestions: list[TagSuggestion] = []

        kb = self._get_kb()
        if kb is None:
            return suggestions

        alb_result = kb.lookup_album(album, artist)
        if alb_result.get("data"):
            alb_data = alb_result["data"].get("data", alb_result["data"])
            mb_title = alb_data.get("title", "")
            mb_year = alb_data.get("year", "")
            mb_cover = alb_data.get("cover_url", "")
            mb_rg_mbid = alb_data.get("release_group_mbid", "")

            if mb_title and mb_title.lower() != album.lower():
                suggestions.append(TagSuggestion(
                    field="album", current=album,
                    suggested=mb_title, confidence=0.90,
                    source="musicbrainz", apply=False,
                ))
            if mb_year:
                yr = str(mb_year)
                suggestions.append(TagSuggestion(
                    field="year", current="",
                    suggested=yr, confidence=0.85,
                    source="musicbrainz", apply=False,
                ))
            if mb_rg_mbid:
                suggestions.append(TagSuggestion(
                    field="mb_album_id", current="",
                    suggested=mb_rg_mbid, confidence=0.95,
                    source="musicbrainz", apply=False,
                ))
            if mb_cover:
                suggestions.append(TagSuggestion(
                    field="cover_url", current="",
                    suggested=mb_cover, confidence=0.80,
                    source="coverart", apply=False,
                ))

        return suggestions

    def suggest_by_disc_toc(self, toc: dict) -> list[TagSuggestion]:
        suggestions: list[TagSuggestion] = []
        kb = self._get_kb()
        if kb is None:
            return suggestions

        track_list = toc.get("track_list", [])
        if track_list:
            suggestions.append(TagSuggestion(
                field="tracks", current=f"{len(track_list)}",
                suggested="", confidence=0.70,
                source="disc_toc", apply=False,
            ))

        return suggestions

    def normalize_artist_name(self, name: str) -> TagSuggestion:
        if not name:
            return TagSuggestion(
                field="artist", current=name, suggested=name,
                confidence=0.0, source="normalizer", apply=False,
            )
        normalized = name.strip()
        if normalized != name:
            return TagSuggestion(
                field="artist", current=name, suggested=normalized,
                confidence=0.95, source="normalizer", apply=False,
            )
        return TagSuggestion(
            field="artist", current=name, suggested=normalized,
            confidence=0.0, source="normalizer", apply=False,
        )

    def suggest_genre(self, track_metadata: Any) -> TagSuggestion:
        genre = getattr(track_metadata, "genre", "") or ""
        if not genre:
            return TagSuggestion(
                field="genre", current="",
                suggested="", confidence=0.0,
                source="ai_suggestion", apply=False,
            )
        from metadata.genre_normalizer import normalize_genre_name
        normalized = normalize_genre_name(genre)
        if normalized and normalized.lower() != genre.lower():
            return TagSuggestion(
                field="genre", current=genre, suggested=normalized,
                confidence=0.88, source="genre_normalizer", apply=False,
            )
        return TagSuggestion(field="genre", current=genre, suggested=genre,
                             confidence=0.0, source="genre_normalizer", apply=False)

    def detect_featured_artists(self, title_or_artist: str) -> list[str]:
        import re
        features = []
        feat_match = re.search(r"\((?:feat\.?|ft\.?)\s+([^)]+)\)", title_or_artist, re.IGNORECASE)
        if not feat_match:
            feat_match = re.search(r"\[(?:feat\.?|ft\.?)\s+([^\]]+)\]", title_or_artist, re.IGNORECASE)
        if feat_match:
            artists = [a.strip() for a in feat_match.group(1).split(",")]
            features = [a for a in artists if a]
        return features

    def suggest_folder_structure(self, album_metadata: dict) -> str:
        artist = album_metadata.get("artist", "Unknown Artist")
        album = album_metadata.get("album", "Unknown Album")
        year = album_metadata.get("year", "")
        safe_artist = self._sanitize(artist)
        safe_album = self._sanitize(album)
        if year:
            return f"{safe_artist}/{year} - {safe_album}"
        return f"{safe_artist}/{safe_album}"

    def generate_album_description(self, album_metadata: dict) -> str:
        artist = album_metadata.get("artist", "")
        album = album_metadata.get("album", "")
        year = album_metadata.get("year", "")
        parts = []
        if artist:
            parts.append(artist)
        if album:
            parts.append(f"'{album}'")
        if year:
            parts.append(f"({year})")
        return " ".join(parts) if parts else ""

    @staticmethod
    def _sanitize(text: str) -> str:
        return text.replace("/", "_").replace("\\", "_").replace(":", " -").strip()
