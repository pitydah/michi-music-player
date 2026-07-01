"""Playlist audit service — health scores, duplicate detection, coverage checks."""
from __future__ import annotations

from library.playlists.playlist_models import PlaylistAuditIssue, PlaylistHealthReport
from library.playlists.playlist_store import PlaylistStore


def audit_playlist(store: PlaylistStore, pid: int) -> PlaylistHealthReport:
    pl = store.get_playlist(pid)
    name = pl["name"] if pl else f"Playlist {pid}"
    report = PlaylistHealthReport(playlist_id=pid, playlist_name=name)
    tracks = store.get_playlist_items(pid)
    report.track_count = len(tracks)
    issues = []
    if not tracks:
        issues.append(PlaylistAuditIssue(issue_type="empty", severity="warning", message="Playlist vacía"))
        report.score = 0
        report.issues = issues
        store.update_health(pid, report)
        return report
    lost = [t for t in tracks if not t.exists]
    for t in lost:
        issues.append(PlaylistAuditIssue(issue_type="lost", severity="error", message=f"Archivo no encontrado: {t.filepath}", track_id=t.track_id, filepath=t.filepath))
    seen = {}
    for t in tracks:
        fp = t.filepath
        if fp in seen:
            issues.append(PlaylistAuditIssue(issue_type="duplicate", severity="warning", message=f"Duplicado: {t.title}", track_id=t.track_id, filepath=fp, details={"original_position": seen[fp], "duplicate_position": t.position}))
        seen[fp] = t.position
    for t in [t for t in tracks if not t.title]:
        issues.append(PlaylistAuditIssue(issue_type="missing_metadata", severity="warning", message=f"Sin título: {t.filepath}", track_id=t.track_id, filepath=t.filepath, details={"fields": ["title"]}))
    for t in [t for t in tracks if not t.has_cover][:5]:
        issues.append(PlaylistAuditIssue(issue_type="missing_cover", severity="info", message=f"Sin carátula: {t.title}", track_id=t.track_id))
    for t in [t for t in tracks if t.quality_kind == "lossy" and t.bitrate and t.bitrate < 256000][:5]:
        issues.append(PlaylistAuditIssue(issue_type="low_quality", severity="info", message=f"Calidad baja: {t.title} ({t.bitrate // 1000}kbps)", track_id=t.track_id, details={"bitrate": t.bitrate, "ext": t.ext}))
    for t in [t for t in tracks if t.filepath.startswith("http://") or t.filepath.startswith("https://")]:
        issues.append(PlaylistAuditIssue(issue_type="remote", severity="info", message=f"Remoto: {t.title[:40]}", track_id=t.track_id, filepath=t.filepath))
    report.issues = issues
    report.score = _calculate_score(report)
    report.stats = _compute_basic_stats(tracks)
    store.update_health(pid, report)
    return report


def audit_all_playlists(store: PlaylistStore) -> list[PlaylistHealthReport]:
    summaries = store.get_all_playlists(include_stats=False)
    reports = []
    for s in summaries:
        try:
            reports.append(audit_playlist(store, s.id))
        except Exception as e:
            __import__("logging").getLogger("michi.playlist_audit").warning("Audit failed for playlist %d: %s", s.id, e)
    return reports


def find_empty_playlists(store: PlaylistStore) -> list[int]:
    return store.find_empty_playlists()


def find_duplicates_in_playlist(store: PlaylistStore, pid: int) -> list[dict]:
    tracks = store.get_playlist_items(pid)
    seen = {}
    duplicates = []
    for t in tracks:
        fp = t.filepath
        if fp in seen:
            duplicates.append({"filepath": fp, "title": t.title, "first_position": seen[fp], "duplicate_position": t.position})
        seen[fp] = t.position
    return duplicates


def find_lost_items(store: PlaylistStore, pid: int) -> list:
    return [t for t in store.get_playlist_items(pid) if not t.exists]


def find_missing_metadata(store: PlaylistStore, pid: int) -> list[dict]:
    result = []
    for t in store.get_playlist_items(pid):
        missing = [field for field, val in
                   [("title", t.title), ("artist", t.artist),
                    ("album", t.album), ("genre", t.genre)]
                   if not val]
        if missing:
            result.append({"track_id": t.track_id, "filepath": t.filepath, "missing": missing})
    return result


def find_missing_covers(store: PlaylistStore, pid: int) -> list[dict]:
    return [{"track_id": t.track_id, "filepath": t.filepath, "title": t.title}
            for t in store.get_playlist_items(pid) if not t.has_cover]


def calculate_health_score(report: PlaylistHealthReport) -> int:
    return _calculate_score(report)


def _calculate_score(report: PlaylistHealthReport) -> int:
    score = 100
    for issue in report.issues:
        if issue.severity == "error":
            score -= 20
        elif issue.severity == "warning":
            score -= 10
        else:
            score -= 5
    for issue in report.issues:
        if issue.issue_type == "lost":
            score -= 5
    return max(0, min(100, score))


def _compute_basic_stats(tracks: list) -> dict:
    artists = {t.artist for t in tracks if t.artist}
    albums = {t.album for t in tracks if t.album}
    genres = {t.genre for t in tracks if t.genre}
    total_dur = sum(t.duration for t in tracks)
    format_counts = {}
    years = []
    for t in tracks:
        if t.ext:
            fmt = t.ext.upper()
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        if t.year:
            years.append(t.year)
    return {"total_duration": total_dur, "unique_artists": len(artists), "unique_albums": len(albums),
            "unique_genres": len(genres), "formats": format_counts, "year_min": min(years) if years else 0, "year_max": max(years) if years else 0}
