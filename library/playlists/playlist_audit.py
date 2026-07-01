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
    issues: list[PlaylistAuditIssue] = []

    if not tracks:
        issues.append(PlaylistAuditIssue(
            issue_type="empty", severity="warning",
            message="Playlist vacía",
        ))
        report.score = 0
        report.issues = issues
        store.update_health(pid, report)
        return report

    # Lost files
    lost = [t for t in tracks if not t.exists]
    for t in lost:
        issues.append(PlaylistAuditIssue(
            issue_type="lost", severity="error",
            message=f"Archivo no encontrado: {t.filepath}",
            track_id=t.track_id, filepath=t.filepath,
        ))

    # Duplicates by filepath
    seen = {}
    for t in tracks:
        fp = t.filepath
        if fp in seen:
            issues.append(PlaylistAuditIssue(
                issue_type="duplicate", severity="warning",
                message=f"Duplicado: {t.title} ({fp})",
                track_id=t.track_id, filepath=fp,
                details={"original_position": seen[fp], "duplicate_position": t.position},
            ))
        seen[fp] = t.position

    # Missing metadata
    no_title = [t for t in tracks if not t.title]
    for t in no_title:
        issues.append(PlaylistAuditIssue(
            issue_type="missing_metadata", severity="warning",
            message=f"Sin título: {t.filepath}",
            track_id=t.track_id, filepath=t.filepath,
            details={"fields": ["title"]},
        ))

    # Missing cover
    no_cover = [t for t in tracks if not t.has_cover]
    for t in no_cover[:5]:
        issues.append(PlaylistAuditIssue(
            issue_type="missing_cover", severity="info",
            message=f"Sin carátula: {t.title}",
            track_id=t.track_id,
        ))

    # Low quality
    low_quality = [t for t in tracks if t.quality_kind == "lossy" and t.bitrate and t.bitrate < 256000]
    for t in low_quality[:5]:
        issues.append(PlaylistAuditIssue(
            issue_type="low_quality", severity="info",
            message=f"Calidad baja: {t.title} ({t.bitrate // 1000}kbps)",
            track_id=t.track_id,
            details={"bitrate": t.bitrate, "ext": t.ext},
        ))

    # Remote files
    remote = [t for t in tracks if t.filepath.startswith("http://") or t.filepath.startswith("https://")]
    for t in remote:
        issues.append(PlaylistAuditIssue(
            issue_type="remote", severity="info",
            message=f"Archivo remoto: {t.title} ({t.filepath[:60]})",
            track_id=t.track_id, filepath=t.filepath,
        ))

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
            logger = __import__("logging").getLogger("michi.playlist_audit")
            logger.warning("Audit failed for playlist %d: %s", s.id, e)
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
            duplicates.append({
                "filepath": fp,
                "title": t.title,
                "first_position": seen[fp],
                "duplicate_position": t.position,
            })
        seen[fp] = t.position
    return duplicates


def find_lost_items(store: PlaylistStore, pid: int) -> list:
    tracks = store.get_playlist_items(pid)
    return [t for t in tracks if not t.exists]


def find_missing_metadata(store: PlaylistStore, pid: int) -> list[dict]:
    tracks = store.get_playlist_items(pid)
    result = []
    for t in tracks:
        missing = []
        if not t.title:
            missing.append("title")
        if not t.artist:
            missing.append("artist")
        if not t.album:
            missing.append("album")
        if not t.genre:
            missing.append("genre")
        if missing:
            result.append({"track_id": t.track_id, "filepath": t.filepath,
                           "missing": missing})
    return result


def find_missing_covers(store: PlaylistStore, pid: int) -> list[dict]:
    tracks = store.get_playlist_items(pid)
    result = []
    for t in tracks:
        if not t.has_cover:
            result.append({"track_id": t.track_id, "filepath": t.filepath,
                           "title": t.title})
    return result


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
    # Cap
    for issue in report.issues:
        if issue.issue_type == "lost":
            score -= 5  # extra penalty per lost
    return max(0, min(100, score))


def _compute_basic_stats(tracks: list) -> dict:
    artists = set()
    albums = set()
    genres = set()
    total_dur = 0.0
    format_counts = {}
    years = []
    for t in tracks:
        if t.artist:
            artists.add(t.artist)
        if t.album:
            albums.add(t.album)
        if t.genre:
            genres.add(t.genre)
        total_dur += t.duration
        if t.ext:
            fmt = t.ext.upper()
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        if t.year:
            years.append(t.year)
    return {
        "total_duration": total_dur,
        "unique_artists": len(artists),
        "unique_albums": len(albums),
        "unique_genres": len(genres),
        "formats": format_counts,
        "year_min": min(years) if years else 0,
        "year_max": max(years) if years else 0,
    }
