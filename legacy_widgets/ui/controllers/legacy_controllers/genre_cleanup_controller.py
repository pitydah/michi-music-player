"""GenreCleanupController — orchestrates cleanup operations between UI and services."""
import logging

_log = logging.getLogger("michi.genre_cleanup_ctrl")


class GenreCleanupController:
    def __init__(self, window, cleanup_service, stats_service, genre_repo,
                 cleanup_page=None):
        self._win = window
        self._ctx = window._ctx
        self._cleanup_svc = cleanup_service
        self._stats_svc = stats_service
        self._repo = genre_repo
        self._page = cleanup_page

    def set_page(self, page):
        self._page = page

    def scan_and_show(self):
        if not self._page:
            return
        try:
            duplicates = self._cleanup_svc.detect_duplicates()
            junk = self._cleanup_svc.detect_junk()
            rare = self._cleanup_svc.detect_rare_genres()
            untagged = self._cleanup_svc.detect_untagged()
            multi = self._cleanup_svc.detect_multi_genre_issues()

            self._page.set_duplicates(duplicates)
            self._page.set_junk(junk)
            self._page.set_rare(rare)
            self._page.set_untagged(untagged)
            self._page.set_multi_genre(multi)

            has_issues = any([duplicates, junk, rare,
                              untagged.get("count", 0) > 0, multi])
            if not has_issues:
                self._page.show_empty()
        except Exception as e:
            _log.warning("scan_and_show failed: %s", e)

    def execute_merge(self, source_genres: list[str], target: str) -> dict:
        if not source_genres or not target:
            _log.warning("execute_merge called with empty sources or target")
            return {"success": False, "affected": 0}
        result = self._cleanup_svc.execute_merge(source_genres, target)
        self._stats_svc.invalidate()
        toast = getattr(self._win, '_toast_svc', None)
        if toast:
            toast.show(
                f"Fusionados {result.get('affected', 0)} tracks en '{target}'",
                "success")
        return result

    def execute_rename(self, old: str, new: str) -> int:
        count = self._cleanup_svc.execute_rename(old, new)
        if count:
            self._stats_svc.invalidate()
        return count

    def execute_apply_genre(self, track_ids: list[int], genre: str,
                            write_tags: bool = False) -> int:
        count = self._cleanup_svc.execute_apply_genre(track_ids, genre,
                                                       write_tags=write_tags)
        if count:
            self._stats_svc.invalidate()
        return count
