"""Artwork resolver — local album cover search and embedding.

Local folder scanning for cover.*, folder.*, front.* images.
Remote download is not yet implemented (raises NotImplementedError).
"""

from __future__ import annotations

import logging
import os
import shutil

logger = logging.getLogger("michi.artwork_resolver")

# ── Known cover filenames, ordered by priority ──
# Sort by longest prefix first to avoid "album" matching "albumartsmall"
_COVER_NAMES = sorted([
    ("cover", 100),
    ("folder", 90),
    ("front", 80),
    ("albumartsmall", 10),
    ("album", 70),
], key=lambda x: len(x[0]), reverse=True)

_IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"})

_ICON_SCORE_THRESHOLD = 40  # below this, consider low quality


def _image_dimensions(path: str) -> tuple[int, int]:
    """Get (width, height) of an image without loading it fully.

    Tries PIL first, then falls back to header parsers for JPEG and PNG.
    """
    try:
        from PIL import Image
        with Image.open(path) as img:
            return img.size
    except Exception:
        pass
    try:
        with open(path, "rb") as f:
            sig = f.read(8)
            # ── JPEG ──
            if sig[:2] == b"\xff\xd8":
                f.seek(2)  # rewind to just after SOI marker
                while True:
                    marker = f.read(2)
                    if not marker or marker[0] != 0xff:
                        break
                    if marker in (b"\xff\xd8", b"\xff\xd9"):
                        continue
                    if marker in (b"\xff\xc0", b"\xff\xc1", b"\xff\xc2"):
                        f.read(3)  # skip length + precision
                        h = int.from_bytes(f.read(2), "big")
                        w = int.from_bytes(f.read(2), "big")
                        return (w, h)
                    length = int.from_bytes(f.read(2), "big")
                    f.seek(length - 2, 1)
            # ── PNG ──
            elif sig == b"\x89PNG\r\n\x1a\n":
                f.read(4)  # skip IHDR length (always 13)
                if f.read(4) == b"IHDR":
                    w = int.from_bytes(f.read(4), "big")
                    h = int.from_bytes(f.read(4), "big")
                    return (w, h)
    except Exception:
        pass
    return (0, 0)


class ArtworkResolver:
    """Searches local folders for album cover art."""

    @property
    def available(self) -> bool:
        return True

    # ── Search ──

    def search_album_art(self, album_metadata: dict) -> list[dict]:
        """Search the album's folder for cover images.

        album_metadata may contain:
          - 'album' (str): album name
          - 'folder' (str): directory path
          - 'artist' (str): artist name
        """
        folder = album_metadata.get("folder", "")
        if not folder or not os.path.isdir(folder):
            return []

        results = []
        try:
            entries = os.listdir(folder)
        except OSError:
            return []

        for fname in entries:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in _IMAGE_EXTS:
                continue
            name_lower = os.path.splitext(fname)[0].lower()
            score = 0
            for prefix, base_score in _COVER_NAMES:
                if name_lower == prefix or name_lower.startswith(prefix):
                    score = base_score
                    break
            if score == 0:
                continue

            full_path = os.path.join(folder, fname)
            try:
                size = os.path.getsize(full_path)
            except OSError:
                continue
            if size < 1024:  # too small to be a real cover
                continue

            w, h = _image_dimensions(full_path)
            if (w < 200 or h < 200) and score > 0:
                score = max(score // 2, 5)  # penalize small images

            results.append({
                "source": "local",
                "path": full_path,
                "filename": fname,
                "width": w,
                "height": h,
                "mime": _ext_to_mime(ext),
                "score": score,
                "size": size,
            })

        return results

    # ── Rank ──

    def rank_artwork_quality(self, results: list[dict]) -> list[dict]:
        """Rank results: prefer large, square images. Penalize thumbnails.

        Scoring formula:
            base score * squareness * size bonus

        Squareness: ratio = min(w,h) / max(w,h), clamped to [0.5, 1.0]
        Size bonus: 1.0 for >= 500px, 0.6 for < 200px
        """
        scored = []
        for r in results:
            w, h = r.get("width", 0), r.get("height", 0)
            base = r.get("score", 0)
            if w > 0 and h > 0:
                ratio = min(w, h) / max(w, h) if max(w, h) > 0 else 1.0
                ratio = max(ratio, 0.5)
                size_bonus = 1.0 if min(w, h) >= 500 else 0.8 if min(w, h) >= 300 else 0.6
            else:
                ratio = 1.0
                size_bonus = 0.5
            final_score = base * ratio * size_bonus
            r["_final_score"] = final_score
            scored.append(r)
        scored.sort(key=lambda x: x.get("_final_score", 0), reverse=True)
        return scored

    # ── Save ──

    def save_cover_file(self, cover_file: str, album_folder: str,
                        overwrite: bool = False):
        """Copy a cover image to the album folder as cover.ext.

        If overwrite=False and a cover already exists, does nothing.
        """
        if not os.path.isfile(cover_file):
            raise FileNotFoundError(f"Cover source not found: {cover_file}")
        os.makedirs(album_folder, exist_ok=True)
        ext = os.path.splitext(cover_file)[1].lower()
        dest = os.path.join(album_folder, f"cover{ext}")
        if os.path.exists(dest) and not overwrite:
            logger.debug("Cover already exists at %s, skipping", dest)
            return
        shutil.copy2(cover_file, dest)
        logger.info("Saved cover to %s", dest)

    # ── Embed ──

    def embed_cover(self, audio_file: str, cover_file: str):
        """Embed cover art into an audio file using TagWriter."""
        from ui.audio_lab.services.tag_writer import TagWriter
        writer = TagWriter()
        writer.embed_cover(audio_file, cover_file)

    # ── Remote download (not yet) ──

    def download_cover(self, url: str, destination: str):
        """Download cover art from a remote URL.

        NOT YET IMPLEMENTED — will be added in a future phase.
        """
        raise NotImplementedError(
            "Remote cover download is not yet implemented. "
            "Use search_album_art() for local covers."
        )


def _ext_to_mime(ext: str) -> str:
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp", ".bmp": "image/bmp",
    }.get(ext, "image/jpeg")
