"""Playlist relinker — find replacements for lost/moved tracks."""
from __future__ import annotations

import os
import unicodedata

from library.playlists.playlist_models import PlaylistRelinkCandidate


def find_lost_items(store, pid: int) -> list:
    """Get tracks in playlist whose files no longer exist."""
    tracks = store.get_playlist_items(pid)
    return [t for t in tracks if t.filepath and not os.path.isfile(t.filepath)]


def find_candidates(lost_item, db_conn) -> list[PlaylistRelinkCandidate]:
    """Search for replacement candidates across the media library."""
    candidates = []

    # 1. Match by track_uid
    if lost_item.track_uid:
        rows = db_conn.execute(
            "SELECT * FROM media_items WHERE track_uid=?", (lost_item.track_uid,)
        ).fetchall()
        for r in rows:
            d = dict(r)
            candidates.append(PlaylistRelinkCandidate(
                track_id=d["id"],
                filepath=d["filepath"],
                title=d.get("title", ""),
                artist=d.get("artist", ""),
                score=100,
                match_type="uid",
            ))

    # 2. Match by content_hash
    if lost_item.content_hash:
        rows = db_conn.execute(
            "SELECT * FROM media_items WHERE content_hash=?",
            (lost_item.content_hash,),
        ).fetchall()
        for r in rows:
            d = dict(r)
            candidates.append(PlaylistRelinkCandidate(
                track_id=d["id"],
                filepath=d["filepath"],
                title=d.get("title", ""),
                artist=d.get("artist", ""),
                score=95,
                match_type="hash",
            ))

    # 3. Match by filename
    old_filename = os.path.basename(lost_item.filepath)
    if old_filename:
        rows = db_conn.execute(
            "SELECT * FROM media_items WHERE filename=?",
            (old_filename,),
        ).fetchall()
        for r in rows:
            d = dict(r)
            if d["filepath"] != lost_item.filepath:
                candidates.append(PlaylistRelinkCandidate(
                    track_id=d["id"],
                    filepath=d["filepath"],
                    title=d.get("title", ""),
                    artist=d.get("artist", ""),
                    score=70,
                    match_type="filename",
                ))

    # 4. Match by normalized title + artist
    if lost_item.title and lost_item.artist:
        rows = db_conn.execute(
            "SELECT * FROM media_items WHERE title=? AND artist=?",
            (lost_item.title, lost_item.artist),
        ).fetchall()
        for r in rows:
            d = dict(r)
            if d["filepath"] != lost_item.filepath:
                candidates.append(PlaylistRelinkCandidate(
                    track_id=d["id"],
                    filepath=d["filepath"],
                    title=d.get("title", ""),
                    artist=d.get("artist", ""),
                    score=85,
                    match_type="title_artist",
                ))

    # 5. Match by approximate duration
    if lost_item.duration > 0:
        lo = lost_item.duration - 3
        hi = lost_item.duration + 3
        title_like = f"%{_extract_short_title(lost_item.title)}%" if lost_item.title else "%"
        rows = db_conn.execute(
            "SELECT * FROM media_items WHERE duration BETWEEN ? AND ? AND title LIKE ?",
            (lo, hi, title_like),
        ).fetchall()
        for r in rows:
            d = dict(r)
            already = any(c.filepath == d["filepath"] for c in candidates)
            if not already and d["filepath"] != lost_item.filepath:
                score = 60
                if lost_item.album and d.get("album") == lost_item.album:
                    score += 15
                candidates.append(PlaylistRelinkCandidate(
                    track_id=d["id"],
                    filepath=d["filepath"],
                    title=d.get("title", ""),
                    artist=d.get("artist", ""),
                    score=score,
                    match_type="duration",
                ))

    # Deduplicate and sort
    seen = set()
    unique = []
    for c in sorted(candidates, key=lambda x: x.score, reverse=True):
        if c.filepath not in seen:
            seen.add(c.filepath)
            unique.append(c)
    return unique


def score_candidate(lost_item, candidate: PlaylistRelinkCandidate) -> int:
    return candidate.score


def relink_item(store, pid: int, lost_item, candidate: PlaylistRelinkCandidate) -> bool:
    """Replace a lost track with a candidate. Returns True on success."""
    try:
        store.remove_track(pid, track_id=lost_item.track_id, filepath=lost_item.filepath)
        store.add_track(pid, filepath=candidate.filepath, track_id=candidate.track_id,
                        source="relink")
        return True
    except Exception:
        return False


def auto_relink(store, pid: int, db_conn, min_score: int = 80) -> dict:
    """Automatically relink all lost tracks above threshold."""
    lost = find_lost_items(store, pid)
    results = {"relinked": 0, "failed": 0, "skipped": 0, "details": []}
    for item in lost:
        cands = find_candidates(item, db_conn)
        good = [c for c in cands if c.score >= min_score]
        if good:
            ok = relink_item(store, pid, item, good[0])
            if ok:
                results["relinked"] += 1
                results["details"].append({
                    "old": item.filepath,
                    "new": good[0].filepath,
                    "score": good[0].score,
                    "match_type": good[0].match_type,
                })
            else:
                results["failed"] += 1
        else:
            results["skipped"] += 1
    return results


def _normalize(s: str) -> str:
    s = s.strip().lower()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _extract_short_title(title: str) -> str:
    """Extract first significant word for fuzzy matching."""
    parts = title.strip().split()
    if not parts:
        return ""
    return parts[0][:15]
