from __future__ import annotations

import os
import tempfile

from core.lyrics.models import (
    TrackIdentity, LyricsDocument, LyricsOperationResult,
    LyricsSource, LyricsErrorCode,
)
from core.lyrics.parser import parse_lrc, parse_plain, serialize_lrc
from core.lyrics.interfaces import SidecarProvider


class FileSidecarProvider(SidecarProvider):
    _SAFE_EXTENSIONS = frozenset({".lrc", ".txt"})

    def __init__(self, search_paths: list[str] | None = None,
                 filename_pattern: str = "{artist} - {title}",
                 clock: callable | None = None):
        self._search_paths = search_paths or []
        self._filename_pattern = filename_pattern
        self._clock = clock or (lambda: __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()))

    def read(self, directory: str, identity: TrackIdentity) -> LyricsOperationResult:
        if not directory:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.PATH_REJECTED,
                message="No directory provided",
            )
        resolved = self._resolve_path(directory)
        if resolved is None:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.PATH_REJECTED,
                message="Path traversal detected",
            )

        candidates = self._find_sidecars(resolved, identity)
        for path, ext in candidates:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                doc = parse_lrc(content) if ext == ".lrc" else parse_plain(content)
                doc.source = LyricsSource.SIDECAR_LRC if ext == ".lrc" else LyricsSource.SIDECAR_TEXT
                doc.identity = identity
                doc.fetched_at = self._clock()
                return LyricsOperationResult(ok=True, document=doc, source=doc.source)
            except (OSError, IOError) as e:
                return LyricsOperationResult(
                    ok=False, code=LyricsErrorCode.READ_ERROR,
                    message=str(e),
                )

        return LyricsOperationResult(
            ok=False, code=LyricsErrorCode.NOT_FOUND,
            message="No sidecar file found",
        )

    def write(self, directory: str, doc: LyricsDocument) -> LyricsOperationResult:
        if not directory:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.PATH_REJECTED,
                message="No directory provided",
            )
        resolved = self._resolve_path(directory)
        if resolved is None:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.PATH_REJECTED,
                message="Path traversal detected",
            )

        filename = self._build_filename(doc.identity, ".lrc")
        filepath = os.path.join(resolved, filename)

        if not filepath.endswith(".lrc") and not filepath.endswith(".txt"):
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.PATH_REJECTED,
                message="Invalid extension",
            )

        if not os.path.isdir(resolved):
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.WRITE_ERROR,
                message="Directory does not exist",
            )

        safe_path = os.path.realpath(filepath)
        if not safe_path.startswith(os.path.realpath(resolved)):
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.PATH_REJECTED,
                message="Path escape detected",
            )

        content = doc.synced_text if doc.synced_text else (serialize_lrc(doc) if doc.has_synced else doc.plain_text)
        try:
            fd, tmp = tempfile.mkstemp(suffix=".lrc.tmp", dir=resolved)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, safe_path)
            if not os.path.exists(safe_path):
                return LyricsOperationResult(
                    ok=False, code=LyricsErrorCode.WRITE_ERROR,
                    message="File not found after write",
                )
            return LyricsOperationResult(
                ok=True, document=doc, source=LyricsSource.SIDECAR_LRC,
            )
        except (OSError, IOError) as e:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.WRITE_ERROR,
                message=str(e),
            )

    def delete(self, directory: str, identity: TrackIdentity) -> bool:
        resolved = self._resolve_path(directory)
        if resolved is None:
            return False
        candidates = self._find_sidecars(resolved, identity)
        for path, _ in candidates:
            try:
                os.remove(path)
                return True
            except OSError:
                pass
        return False

    def _find_sidecars(self, directory: str, identity: TrackIdentity) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []
        patterns = self._filename_patterns(identity)
        try:
            entries = os.listdir(directory)
        except (OSError, IOError):
            return []
        for fname in entries:
            if fname.startswith("."):
                continue
            fpath = os.path.join(directory, fname)
            if not os.path.isfile(fpath):
                continue
            _, ext = os.path.splitext(fname)
            if ext.lower() not in self._SAFE_EXTENSIONS:
                continue
            if fname in patterns:
                candidates.append((fpath, ext.lower()))
        return candidates

    def _filename_patterns(self, identity: TrackIdentity) -> set[str]:
        patterns = set()
        patterns.add(f"{identity.title}.lrc")
        patterns.add(f"{identity.title}.txt")
        patterns.add(f"{identity.artist} - {identity.title}.lrc")
        patterns.add(f"{identity.artist} - {identity.title}.txt")
        if identity.filepath:
            base, _ = os.path.splitext(os.path.basename(identity.filepath))
            patterns.add(f"{base}.lrc")
            patterns.add(f"{base}.txt")
        return patterns

    def _build_filename(self, identity: TrackIdentity, ext: str) -> str:
        if identity.filepath:
            base, _ = os.path.splitext(os.path.basename(identity.filepath))
            return f"{base}{ext}"
        return f"{identity.artist} - {identity.title}{ext}"

    def _resolve_path(self, path: str) -> str | None:
        if ".." in path.split(os.sep):
            return None
        try:
            return os.path.realpath(path)
        except (OSError, IOError):
            return None
