"""Artwork utilities — extract, set, remove, resize embedded artwork."""
import os
import io

try:
    from PIL import Image
    _pillow_available = True
except ImportError:
    _pillow_available = False

PRESETS = {
    "300": 300,
    "600": 600,
    "1000": 1000,
    "1400": 1400,
}
DEFAULT_SIZE = 600


def image_info(path_or_data) -> dict | None:
    if not _pillow_available:
        return None
    try:
        if isinstance(path_or_data, bytes):
            img = Image.open(io.BytesIO(path_or_data))
        else:
            img = Image.open(path_or_data)
        w, h = img.size
        fmt = img.format or "JPEG"
        mode = img.mode
        size_bytes = len(path_or_data) if isinstance(path_or_data, bytes) else os.path.getsize(path_or_data)
        return {
            "width": w, "height": h,
            "format": fmt,
            "mode": mode,
            "size_bytes": size_bytes,
            "size_mb": size_bytes / (1024 * 1024),
        }
    except Exception:
        return None


def resize_artwork_bytes(
    data: bytes,
    max_size: int = DEFAULT_SIZE,
    output_format: str = "JPEG",
    quality: int = 85,
    crop_square: bool = True,
    keep_aspect: bool = True,
) -> tuple[bytes, str, dict] | None:
    """Resize artwork from bytes. Returns (new_bytes, mime, info_dict)."""
    if not _pillow_available:
        return None
    try:
        img = Image.open(io.BytesIO(data))
        original_info = {
            "ow": img.size[0], "oh": img.size[1],
            "ofmt": img.format or "JPEG",
        }

        if crop_square:
            img = _crop_center_square(img)

        w, h = img.size
        if keep_aspect:
            ratio = min(max_size / max(w, h), 1.0)
            new_w, new_h = int(w * ratio), int(h * ratio)
        else:
            new_w, new_h = max_size, max_size

        img = img.resize((new_w, new_h), Image.LANCZOS)

        out_fmt = output_format.upper()
        mime = "image/jpeg" if out_fmt == "JPEG" else "image/png"

        if out_fmt == "JPEG" and img.mode in ("RGBA", "P"):
            background = Image.new("RGB", img.size, (9, 11, 17))
            if img.mode == "RGBA":
                background.paste(img, mask=img.split()[3])
            else:
                img = img.convert("RGB")
                background.paste(img)
            img = background
        elif out_fmt == "JPEG":
            img = img.convert("RGB")

        buf = io.BytesIO()
        save_kw = {"format": out_fmt}
        if out_fmt == "JPEG":
            save_kw["quality"] = quality
            save_kw["optimize"] = True
        img.save(buf, **save_kw)
        new_data = buf.getvalue()

        info = {
            **original_info,
            "nw": new_w, "nh": new_h,
            "nf_size": len(new_data),
            "nf_mb": len(new_data) / (1024 * 1024),
        }
        return new_data, mime, info
    except Exception:
        return None


def _crop_center_square(img) -> Image.Image:
    w, h = img.size
    if w == h:
        return img
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def make_artwork_pixmap(data: bytes, size: int = 220):
    """Create QPixmap from artwork bytes."""
    try:
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        pix = QPixmap()
        pix.loadFromData(data)
        return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:
        return None


def extract_artwork(filepath: str, dest_path: str) -> bool:
    try:
        from metadata.tag_reader import read_tags
        tags = read_tags(filepath)
        if tags.artwork_data:
            mime = tags.artwork_mime or "image/jpeg"
            ext = ".jpg" if "jpeg" in mime else ".png"
            out = dest_path if dest_path.endswith(ext) else dest_path + ext
            with open(out, "wb") as f:
                f.write(tags.artwork_data)
            return True
    except Exception:
        import logging
    logging.getLogger("astra").debug("Artwork extraction failed")
    return False


def set_artwork(filepath: str, image_path: str) -> bool:
    if not os.path.isfile(image_path):
        return False
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(image_path)[1].lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

        from metadata.tag_reader import read_tags
        from metadata.tag_writer import write_tags
        tags = read_tags(filepath)
        if tags.error:
            return False
        tags.has_artwork = True
        tags.artwork_mime = mime
        tags.artwork_data = data
        tags.mark_artwork_dirty()
        return write_tags(tags)
    except Exception:
        return False


def remove_artwork(filepath: str) -> bool:
    try:
        from metadata.tag_reader import read_tags
        from metadata.tag_writer import write_tags
        tags = read_tags(filepath)
        if tags.error:
            return False
        tags.has_artwork = False
        tags.artwork_mime = ""
        tags.artwork_data = None
        tags.mark_artwork_dirty()
        return write_tags(tags)
    except Exception:
        return False


def load_image_as_bytes(image_path: str) -> bytes | None:
    if not os.path.isfile(image_path):
        return None
    try:
        with open(image_path, "rb") as f:
            return f.read()
    except Exception:
        return None
