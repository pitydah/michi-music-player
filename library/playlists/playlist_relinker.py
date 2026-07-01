"""Playlist relinker — find replacements for lost/moved tracks."""
from __future__ import annotations

import os
import unicodedata

from library.playlists.playlist_models import PlaylistRelinkCandidate


def find_lost_items(store, pid: int) -> list:
    return [t for t in store.get_playlist_items(pid) if t.filepath and not os.path.isfile(t.filepath)]


def find_candidates(lost_item, db_conn) -> list[PlaylistRelinkCandidate]:
    candidates = []
    if lost_item.track_uid:
        for r in db_conn.execute("SELECT * FROM media_items WHERE track_uid=?", (lost_item.track_uid,)).fetchall():
            d = dict(r)
            candidates.append(PlaylistRelinkCandidate(track_id=d["id"], filepath=d["filepath"], title=d.get("title", ""), artist=d.get("artist", ""), score=100, match_type="uid"))
    if lost_item.content_hash:
        for r in db_conn.execute("SELECT * FROM media_items WHERE content_hash=?", (lost_item.content_hash,)).fetchall():
            d = dict(r)
            candidates.append(PlaylistRelinkCandidate(track_id=d["id"], filepath=d["filepath"], title=d.get("title", ""), artist=d.get("artist", ""), score=95, match_type="hash"))
    old_filename = os.path.basename(lost_item.filepath)
    if old_filename:
        for r in db_conn.execute("SELECT * FROM media_items WHERE filename=?", (old_filename,)).fetchall():
            d = dict(r)
            if d["filepath"] != lost_item.filepath:
                candidates.append(PlaylistRelinkCandidate(track_id=d["id"], filepath=d["filepath"], title=d.get("title", ""), artist=d.get("artist", ""), score=70, match_type="filename"))
    if lost_item.title and lost_item.artist:
        for r in db_conn.execute("SELECT * FROM media_items WHERE title=? AND artist=?", (lost_item.title, lost_item.artist)).fetchall():
            d = dict(r)
            if d["filepath"] != lost_item.filepath:
                candidates.append(PlaylistRelinkCandidate(track_id=d["id"], filepath=d["filepath"], title=d.get("title", ""), artist=d.get("artist", ""), score=85, match_type="title_artist"))
    if lost_item.duration > 0:
        lo, hi = lost_item.duration - 3, lost_item.duration + 3
        title_like = f"%{_extract_short_title(lost_item.title)}%" if lost_item.title else "%"
        for r in db_conn.execute("SELECT * FROM media_items WHERE duration BETWEEN ? AND ? AND title LIKE ?", (lo, hi, title_like)).fetchall():
            d = dict(r)
            if not any(c.filepath == d["filepath"] for c in candidates) and d["filepath"] != lost_item.filepath:
                score = 60
                if lost_item.album and d.get("album") == lost_item.album:
                    score += 15
                candidates.append(PlaylistRelinkCandidate(track_id=d["id"], filepath=d["filepath"], title=d.get("title", ""), artist=d.get("artist", ""), score=score, match_type="duration"))
    seen, unique = set(), []
    for c in sorted(candidates, key=lambda x: x.score, reverse=True):
        if c.filepath not in seen:
            seen.add(c.filepath)
            unique.append(c)
    return unique


def score_candidate(lost_item, candidate: PlaylistRelinkCandidate) -> int:
    return candidate.score


def relink_item(store, pid: int, lost_item, candidate: PlaylistRelinkCandidate) -> bool:
    try:
        store.remove_track(pid, track_id=lost_item.track_id, filepath=lost_item.filepath)
        store.add_track(pid, filepath=candidate.filepath, track_id=candidate.track_id, source="relink")
        return True
    except Exception:
        return False


def auto_relink(store, pid: int, db_conn, min_score: int = 80) -> dict:
    lost = find_lost_items(store, pid)
    results = {"relinked": 0, "failed": 0, "skipped": 0, "details": []}
    for item in lost:
        cands = find_candidates(item, db_conn)
        good = [c for c in cands if c.score >= min_score]
        if good:
            ok = relink_item(store, pid, item, good[0])
            if ok:
                results["relinked"] += 1
                results["details"].append({"old": item.filepath, "new": good[0].filepath, "score": good[0].score, "match_type": good[0].match_type})
            else:
                results["failed"] += 1
        else:
            results["skipped"] += 1
    return results


def _normalize(s: str) -> str:
    s = s.strip().lower()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _extract_short_title(title: str) -> str:
    parts = title.strip().split()
    return parts[0][:15] if parts else ""
