"""Deduplication — prevent repeated detections within a time window."""
import time


def is_duplicate_detection(db, title: str, artist: str,
                           source_uri: str = "",
                           minutes: int = 10) -> bool:
    """Check if this detection is a duplicate within the time window."""
    if hasattr(db, 'find_detected_track_recent'):
        existing = db.find_detected_track_recent(title, artist)
        if existing:
            return True

    # Also check in-memory if the DB method is too strict
    if hasattr(db, 'get_detected_tracks'):
        recent = db.get_detected_tracks(limit=50)
        cutoff = time.time() - minutes * 60
        nt = " ".join(title.lower().strip().split())
        na = " ".join(artist.lower().strip().split()) if artist else ""
        for r in recent:
            rt = " ".join(r.get("title", "").lower().strip().split())
            ra = " ".join(r.get("artist", "").lower().strip().split())
            rtime = r.get("detected_at", 0)
            if rt == nt and ra == na and rtime > cutoff:
                return True
    return False
