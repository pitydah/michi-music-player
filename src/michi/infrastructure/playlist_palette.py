"""Lightweight asynchronous color extraction for playlist hero ambience."""

import logging
import threading
from collections import Counter, OrderedDict
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QImageReader

from michi.application.ports import PlaylistPaletteExtractorPort

logger = logging.getLogger(__name__)

DEFAULT_PLAYLIST_PALETTE = ("#152A45", "#13243D", "#0A0D14")


class QtPlaylistPaletteExtractor(PlaylistPaletteExtractorPort):
    """Extracts two atmospheric colors on one background worker.

    Images are requested at 48×48, quantized, then neutralized toward
    obsidian. The cache key includes path, size and mtime, so replacing a
    managed cover at the same path invalidates the result naturally.
    """

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="michi-playlist-palette"
        )
        self._lock = threading.Lock()
        self._cache: OrderedDict[tuple[tuple[str, int, int], ...], tuple[str, ...]] = (
            OrderedDict()
        )
        self._pending: dict[
            tuple[tuple[str, int, int], ...],
            list[Callable[[tuple[str, ...]], None]],
        ] = {}
        self._closed = False

    @staticmethod
    def _key(source_paths: tuple[str, ...]) -> tuple[tuple[str, int, int], ...]:
        entries: list[tuple[str, int, int]] = []
        for raw_path in source_paths[:4]:
            path = Path(raw_path)
            try:
                stat = path.stat()
            except OSError:
                continue
            if path.is_file():
                entries.append((str(path), stat.st_size, stat.st_mtime_ns))
        return tuple(entries)

    def request_palette(
        self,
        source_paths: tuple[str, ...],
        callback: Callable[[tuple[str, ...]], None],
    ) -> None:
        key = self._key(source_paths)
        if not key:
            callback(DEFAULT_PLAYLIST_PALETTE)
            return
        immediate: tuple[str, ...] | None = None
        with self._lock:
            if self._closed:
                immediate = DEFAULT_PLAYLIST_PALETTE
            else:
                immediate = self._cache.get(key)
                if immediate is not None:
                    self._cache.move_to_end(key)
                if immediate is None:
                    callbacks = self._pending.get(key)
                    if callbacks is not None:
                        callbacks.append(callback)
                        return
                    self._pending[key] = [callback]
                    future = self._executor.submit(self._extract, key)
                    future.add_done_callback(lambda done: self._complete(key, done))
                    return
        callback(immediate or DEFAULT_PLAYLIST_PALETTE)

    def _complete(
        self,
        key: tuple[tuple[str, int, int], ...],
        future: Future[tuple[str, ...]],
    ) -> None:
        try:
            palette = future.result()
        except Exception:  # best-effort visual enrichment boundary
            logger.exception("Playlist palette extraction failed")
            palette = DEFAULT_PLAYLIST_PALETTE
        with self._lock:
            callbacks = self._pending.pop(key, [])
            if not self._closed:
                self._cache[key] = palette
                self._cache.move_to_end(key)
                while len(self._cache) > 128:
                    self._cache.popitem(last=False)
        for callback in callbacks:
            callback(palette)

    @classmethod
    def _extract(cls, key: tuple[tuple[str, int, int], ...]) -> tuple[str, ...]:
        buckets: Counter[tuple[int, int, int]] = Counter()
        for raw_path, _size, _mtime in key:
            reader = QImageReader(raw_path)
            reader.setAutoTransform(True)
            reader.setScaledSize(QSize(48, 48))
            image = reader.read()
            if image.isNull():
                continue
            for y in range(0, image.height(), 2):
                for x in range(0, image.width(), 2):
                    pixel = image.pixelColor(x, y)
                    if pixel.alpha() < 128:
                        continue
                    red, green, blue = pixel.red(), pixel.green(), pixel.blue()
                    maximum, minimum = max(red, green, blue), min(red, green, blue)
                    saturation = maximum - minimum
                    # Near-white/black pixels carry little identity; retain
                    # them at low weight rather than letting them dominate.
                    weight = 1 + min(4, saturation // 36)
                    if maximum > 242 or maximum < 18:
                        weight = 1
                    bucket = (red // 16 * 16, green // 16 * 16, blue // 16 * 16)
                    buckets[bucket] += weight

        if not buckets:
            return DEFAULT_PLAYLIST_PALETTE
        ranked = [rgb for rgb, _count in buckets.most_common(12)]
        primary = ranked[0]
        secondary = next(
            (
                rgb
                for rgb in ranked[1:]
                if sum(abs(rgb[index] - primary[index]) for index in range(3)) > 72
            ),
            ranked[min(1, len(ranked) - 1)],
        )
        return (
            cls._atmospheric(primary, 0.42),
            cls._atmospheric(secondary, 0.32),
            "#0A0D14",
        )

    @staticmethod
    def _atmospheric(rgb: tuple[int, int, int], strength: float) -> str:
        obsidian = (9, 11, 17)
        mixed = [
            round(obsidian[index] * (1.0 - strength) + rgb[index] * strength)
            for index in range(3)
        ]
        # Clamp perceived brightness so arbitrary user artwork never owns
        # text contrast; QML adds an additional semantic scrim.
        luminance = 0.2126 * mixed[0] + 0.7152 * mixed[1] + 0.0722 * mixed[2]
        if luminance > 68:
            scale = 68 / luminance
            mixed = [round(channel * scale) for channel in mixed]
        return "#" + "".join(f"{channel:02X}" for channel in mixed)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._pending.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)
