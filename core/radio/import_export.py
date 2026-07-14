from __future__ import annotations

import json
import os
import re
import tempfile
from typing import Protocol

from core.radio.models import (
    StationCreateRequest, ImportResult, ExportResult,
    Station, AtomicMode,
)

_M3U_EXTINF = re.compile(r"#EXTINF:\s*(-?\d+),(.*)")
_PLS_ENTRY = re.compile(r"^File\d+=(.+)$", re.IGNORECASE)
_PLS_TITLE = re.compile(r"^Title\d+=(.+)$", re.IGNORECASE)


class ImportExportRepository(Protocol):
    def add(self, req: StationCreateRequest) -> Station: ...
    def bulk_add(self, stations: list[StationCreateRequest], mode: str) -> int: ...
    def get_all_for_export(self) -> list[Station]: ...
    def find_by_url(self, url: str) -> Station | None: ...


class RadioImportService:
    def __init__(self, repo: ImportExportRepository):
        self._repo = repo

    def import_m3u(self, content: str, mode: AtomicMode = AtomicMode.BEST_EFFORT) -> ImportResult:
        result = ImportResult()
        lines = content.splitlines()
        stations: list[StationCreateRequest] = []
        current_name = ""
        mode_str = mode.value

        for line in lines:
            line = line.strip()
            if not line:
                continue
            m = _M3U_EXTINF.match(line)
            if m:
                current_name = m.group(2).strip()
                continue
            if line.startswith("#"):
                continue
            url = line
            if not current_name:
                current_name = _name_from_url(url)
            stations.append(StationCreateRequest(
                name=current_name[:200], stream_url=url,
            ))
            current_name = ""

        result.total_entries = len(stations)
        return self._process_stations(stations, result, mode_str)

    def import_pls(self, content: str, mode: AtomicMode = AtomicMode.BEST_EFFORT) -> ImportResult:
        result = ImportResult()
        lines = content.splitlines()
        urls: dict[int, str] = {}
        titles: dict[int, str] = {}
        mode_str = mode.value

        for line in lines:
            line = line.strip()
            m = _PLS_ENTRY.match(line)
            if m:
                idx = int(re.search(r"(\d+)", m.group(0)).group(1))
                urls[idx] = m.group(1).strip()
                continue
            mt = _PLS_TITLE.match(line)
            if mt:
                idx = int(re.search(r"(\d+)", mt.group(0)).group(1))
                titles[idx] = mt.group(1).strip()

        stations: list[StationCreateRequest] = []
        for idx in sorted(urls):
            url = urls[idx]
            name = titles.get(idx, _name_from_url(url))
            stations.append(StationCreateRequest(
                name=name[:200], stream_url=url,
            ))

        result.total_entries = len(stations)
        return self._process_stations(stations, result, mode_str)

    def _process_stations(self, stations: list[StationCreateRequest],
                          result: ImportResult, mode: str) -> ImportResult:
        if mode == "all_or_nothing":
            imported = self._repo.bulk_add(stations, mode)
            result.imported = imported
            result.failed = len(stations) - imported
        else:
            for req in stations:
                existing = self._repo.find_by_url(req.stream_url)
                if existing:
                    result.duplicates += 1
                    continue
                try:
                    self._repo.add(req)
                    result.imported += 1
                except Exception as e:
                    result.failed += 1
                    result.errors.append(str(e))
        return result


class RadioExportService:
    def __init__(self, repo: ImportExportRepository):
        self._repo = repo

    def export_m3u8(self, stations: list[Station] | None = None, path: str = "") -> ExportResult:
        if stations is None:
            stations = self._repo.get_all_for_export()
        lines = ["#EXTM3U"]
        for s in stations:
            lines.append(f"#EXTINF:-1,{s.name}")
            lines.append(s.stream_url)
        return self._write_file(path, "\n".join(lines), len(stations))

    def export_pls(self, stations: list[Station] | None = None, path: str = "") -> ExportResult:
        if stations is None:
            stations = self._repo.get_all_for_export()
        lines = ["[playlist]"]
        lines.append(f"NumberOfEntries={len(stations)}")
        for i, s in enumerate(stations, 1):
            lines.append(f"File{i}={s.stream_url}")
            lines.append(f"Title{i}={s.name}")
            lines.append(f"Length{i}=-1")
        lines.append("Version=2")
        return self._write_file(path, "\n".join(lines), len(stations))

    def export_json(self, stations: list[Station] | None = None, path: str = "") -> ExportResult:
        if stations is None:
            stations = self._repo.get_all_for_export()
        data = [
            {
                "name": s.name,
                "stream_url": s.stream_url,
                "homepage_url": s.homepage_url,
                "favicon_url": s.favicon_url,
                "genre": s.genre,
                "country": s.country,
                "language": s.language,
                "codec": s.codec,
                "bitrate": s.bitrate,
                "favorite": s.favorite,
            }
            for s in stations
        ]
        return self._write_file(path, json.dumps(data, indent=2, ensure_ascii=False), len(stations))

    def _write_file(self, path: str, content: str, count: int) -> ExportResult:
        if not path:
            return ExportResult(error="No path provided")
        dirname = os.path.dirname(path)
        if dirname and not os.path.isdir(dirname):
            return ExportResult(error=f"Directory does not exist: {dirname}")
        try:
            fd, tmp = tempfile.mkstemp(suffix=".tmp", dir=dirname or None)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, path)
            if not os.path.exists(path):
                return ExportResult(error="File not found after write")
            return ExportResult(path=path, count=count, ok=True)
        except (OSError, IOError) as e:
            return ExportResult(error=str(e))


def detect_playlist_format(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("#EXTM3U"):
        return "m3u8"
    if stripped.startswith("[playlist]"):
        return "pls"
    if stripped.startswith("<?xml") or "<playlist" in stripped[:200]:
        return "xspf"
    if stripped.startswith("#EXTINF"):
        return "m3u"
    if stripped.startswith("{"):
        return "json"
    if _looks_like_m3u(stripped):
        return "m3u"
    return "unknown"


def _looks_like_m3u(content: str) -> bool:
    lines = content.splitlines()
    url_count = sum(1 for line in lines if line.strip().startswith("http"))
    return url_count >= 1


def _name_from_url(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.hostname or "radio"
    return f"Radio {host}"
