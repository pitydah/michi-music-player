"""Metadata resolver — identifies albums from disc TOC and local metadata.

No network/MusicBrainz — operates purely on provided data.
"""

from __future__ import annotations

from ui.audio_lab.models import DiscMetadata, TrackMetadata


class MetadataResolver:
    """Resolves album metadata from disc TOC and artist/album hints."""

    # ── Confidence scoring ──

    def calculate_confidence(self, candidate: DiscMetadata,
                             disc_info: dict) -> float:
        """Score how well a candidate matches the actual disc.

        disc_info may contain:
          - 'tracks' (list): track info with possible 'duration' per track
          - 'total_duration' (float): total disc duration in seconds
          - 'track_count' (int): number of audio tracks on disc

        Scoring weighted:
          - Artist present: 0.15
          - Album present: 0.15
          - Track count match: 0.25
          - Track titles present: 0.20 (proportion)
          - Duration match: 0.15
          - Genre present: 0.05
          - Year present: 0.05
        """
        if not candidate:
            return 0.0

        score = 0.0

        # Artist and album present (basic metadata)
        if candidate.artist and candidate.artist.strip():
            score += 0.15
        if candidate.album and candidate.album.strip():
            score += 0.15

        # Track count match
        disc_tracks = disc_info.get("track_count") or len(
            disc_info.get("tracks", []))
        cand_tracks = len(candidate.tracks) if candidate.tracks else 0
        if disc_tracks > 0 and cand_tracks > 0:
            ratio = min(cand_tracks, disc_tracks) / max(cand_tracks, disc_tracks)
            score += 0.25 * ratio

        # Track titles present (proportion)
        if candidate.tracks:
            titled = sum(1 for t in candidate.tracks
                        if t.title and t.title.strip())
            score += 0.20 * (titled / len(candidate.tracks) if candidate.tracks else 0)

        # Duration match
        disc_duration = disc_info.get("total_duration", 0)
        cand_duration = sum(getattr(t, "duration", 0) or 0 for t in candidate.tracks) if candidate.tracks else 0
        if disc_duration > 0 and cand_duration > 0:
            dur_ratio = min(disc_duration, cand_duration) / max(disc_duration, cand_duration)
            score += 0.15 * dur_ratio

        # Genre present
        if candidate.genre and candidate.genre.strip():
            score += 0.05

        # Year present
        if candidate.year and candidate.year > 0:
            score += 0.05

        return min(score, 1.0)

    # ── Merge ──

    def merge_metadata_candidates(self,
                                  candidates: list[DiscMetadata]) -> DiscMetadata:
        """Merge multiple candidates: best confidence wins, gaps filled from others.

        Never overwrites good data with empty strings or zeros.
        """
        if not candidates:
            return DiscMetadata()

        # Sort by confidence descending
        sorted_candidates = sorted(
            candidates, key=lambda c: c.confidence, reverse=True)

        result = DiscMetadata()

        # Take best candidate's fields
        best = sorted_candidates[0]
        result.artist = best.artist
        result.album = best.album
        result.year = best.year
        result.genre = best.genre
        result.cover_path = best.cover_path
        result.confidence = best.confidence
        result.source = best.source
        result.tracks = list(best.tracks) if best.tracks else []

        # Fill gaps from other candidates
        for candidate in sorted_candidates[1:]:
            if not result.artist and candidate.artist:
                result.artist = candidate.artist
            if not result.album and candidate.album:
                result.album = candidate.album
            if not result.year and candidate.year:
                result.year = candidate.year
            if not result.genre and candidate.genre:
                result.genre = candidate.genre
            if not result.cover_path and candidate.cover_path:
                result.cover_path = candidate.cover_path

            # Merge tracks: fill missing titles
            if candidate.tracks:
                result_tracks = result.tracks
                for i, ct in enumerate(candidate.tracks):
                    if i < len(result_tracks):
                        rt = result_tracks[i]
                        if not rt.title and ct.title:
                            rt.title = ct.title
                        if not rt.artist and ct.artist:
                            rt.artist = ct.artist
                        if not rt.duration and ct.duration:
                            rt.duration = ct.duration

        # Recalculate final confidence
        result.merged_sources = [c.source for c in sorted_candidates if c.source]
        return result

    # ── Artist/Album lookup (local) ──

    def find_album_by_artist_album(self, artist: str,
                                   album: str) -> DiscMetadata | None:
        """Build basic DiscMetadata from artist and album names.

        Confidence: moderate (0.55) — enough information to tag, but not verified.
        """
        if not artist or not album:
            return None
        return DiscMetadata(
            artist=artist.strip(),
            album=album.strip(),
            confidence=0.55,
            source="artist_album",
        )

    # ── Disc TOC lookup ──

    def find_album_by_disc_toc(self, toc: dict) -> DiscMetadata | None:
        """Build partial metadata from a disc Table of Contents.

        toc may contain:
          - 'tracks' (list of dicts): each with optional 'start_sector', 'length_sectors'
          - 'track_count' (int)
          - 'total_sectors' (int)
          - 'lead_out_sector' (int)

        Confidence: low (0.15-0.30) — TOC alone is weak without MusicBrainz.
        """
        if not toc:
            return None

        track_count = toc.get("track_count") or len(toc.get("tracks", []))
        if track_count == 0:
            return None

        tracks_data = toc.get("tracks", [])
        tracks = []
        for i, td in enumerate(tracks_data):
            sectors = td.get("length_sectors", 0) if isinstance(td, dict) else 0
            duration = sectors / 75.0 if sectors else 0  # CD: 75 sectors/sec
            tracks.append(TrackMetadata(
                track_number=i + 1,
                duration=round(duration, 1),
            ))

        # Confidence: track count helps, but no titles = low
        confidence = 0.15 + min(track_count * 0.01, 0.15)

        return DiscMetadata(
            tracks=tracks,
            confidence=round(confidence, 2),
            source="toc_local",
        )
