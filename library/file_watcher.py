"""FileWatcher — real-time filesystem monitoring for library roots.

Uses QFileSystemWatcher to detect new, modified, and deleted audio files
across all active library roots. Events are debounced and processed in
batches to avoid overloading the scanner.

Integration:
    watcher = FileWatcher(db)
    watcher.file_added.connect(lambda path: ...)
    watcher.file_removed.connect(lambda path: ...)
    watcher.start()
"""
import os
import contextlib
import logging

from PySide6.QtCore import QObject, Signal, QTimer, QFileSystemWatcher

from library.metadata_extractor import ALL_EXTS

logger = logging.getLogger("michi.file_watcher")

_DEBOUNCE_MS = 3000
_MAX_BATCH = 100
_MAX_WATCHED_DIRS = 2048


class FileWatcher(QObject):
    """Monitors library root directories for file system changes.

    Emits batched signals after a debounce period so rapid events
    (e.g. bulk copy) are grouped into a single notification.
    """

    files_added = Signal(list)
    files_removed = Signal(list)
    files_modified = Signal(list)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db
        self._watcher = QFileSystemWatcher(self)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(_DEBOUNCE_MS)
        self._timer.timeout.connect(self._flush)

        self._pending_added: set[str] = set()
        self._pending_removed: set[str] = set()
        self._pending_modified: set[str] = set()

        self._watcher.directoryChanged.connect(self._on_dir_changed)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._running = False
        self._watched_count = 0
        self._degraded = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._watch_roots()

    def stop(self):
        self._running = False
        self._timer.stop()
        dirs = list(self._watcher.directories())
        files = list(self._watcher.files())
        import contextlib
        if dirs:
            with contextlib.suppress(RuntimeError):
                self._watcher.removePaths(dirs)
        if files:
            with contextlib.suppress(RuntimeError):
                self._watcher.removePaths(files)
        self._flush()

    def refresh_roots(self):
        self._watched_count = 0
        self._degraded = False
        dirs = list(self._watcher.directories())
        import contextlib
        if dirs:
            with contextlib.suppress(RuntimeError):
                self._watcher.removePaths(dirs)
        self._watch_roots()

    def _watch_roots(self):
        roots = self._db.get_library_roots()
        for root in roots:
            if not os.path.isdir(root):
                logger.warning("FileWatcher: root offline, skipping watch: %s", root)
                continue
            self._watch_recursive(root)

    def _watch_recursive(self, directory: str):
        if self._watched_count >= _MAX_WATCHED_DIRS:
            if not self._degraded:
                logger.warning(
                    "FileWatcher degraded: max watched dirs reached (%d). "
                    "Use manual refresh for large libraries.", _MAX_WATCHED_DIRS)
                self._degraded = True
            return
        try:
            ok = self._watcher.addPath(directory)
            if ok:
                self._watched_count += 1
            for entry in os.listdir(directory):
                full = os.path.join(directory, entry)
                if os.path.isdir(full) and not entry.startswith("."):
                    self._watch_recursive(full)
        except Exception as e:
            logger.debug("FileWatcher: could not watch %s — %s", directory, e)

    def _on_dir_changed(self, dirpath: str):
        if not self._running:
            return
        if not os.path.isdir(dirpath):
            logger.warning("FileWatcher: changed directory unavailable, skipping: %s", dirpath)
            return
        # Watch new subdirectories created inside this directory
        try:
            for entry in os.listdir(dirpath):
                full = os.path.join(dirpath, entry)
                if os.path.isdir(full) and full not in self._watcher.directories():
                    self._watch_recursive(full)
        except PermissionError:
            pass

    def _on_file_changed(self, filepath: str):
        """Handle individual file changes. Currently delegates to dir handler."""
        dirpath = os.path.dirname(filepath) if os.path.isfile(filepath) else filepath
        self._on_dir_changed(dirpath)
        try:
            current = {
                os.path.join(dirpath, f)
                for f in os.listdir(dirpath)
                if os.path.splitext(f)[1].lower() in ALL_EXTS
            }
        except PermissionError:
            return

        known = {
            r[0] for r in self._db.conn.execute(
                "SELECT filepath FROM media_items "
                "WHERE directory = ? AND deleted_at IS NULL",
                (dirpath,)
            ).fetchall()
        }

        added = current - known
        removed = known - current
        modified = current & known

        if added:
            self._pending_added.update(added)
        if removed:
            self._pending_removed.update(removed)
        if modified:
            for fp in modified:
                try:
                    st = os.stat(fp)
                except OSError:
                    continue
                sig = self._db.get_file_signature(fp)
                if sig and (st.st_size, st.st_mtime) != (sig[0], sig[1]):
                    self._pending_modified.add(fp)

        total = (len(self._pending_added) + len(self._pending_removed)
                 + len(self._pending_modified))
        if total >= _MAX_BATCH:
            self._flush()
        else:
            self._timer.start()

    def _flush(self):
        self._timer.stop()
        added = list(self._pending_added)
        removed = list(self._pending_removed)
        modified = list(self._pending_modified)

        self._pending_added.clear()
        self._pending_removed.clear()
        self._pending_modified.clear()

        if added:
            logger.info("FileWatcher: %d files added", len(added))
            self.files_added.emit(added)
        if removed:
            logger.info("FileWatcher: %d files removed", len(removed))
            self.files_removed.emit(removed)
        if modified:
            logger.info("FileWatcher: %d files modified", len(modified))
            self.files_modified.emit(modified)

    def add_root(self, path: str):
        if os.path.isdir(path):
            self._watch_recursive(path)

    def remove_root(self, path: str):
        with contextlib.suppress(RuntimeError):
            self._watcher.removePath(path)
