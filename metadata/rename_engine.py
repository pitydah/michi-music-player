"""Rename engine — preview and rename files based on tag patterns."""
import os

from metadata.tag_model import TrackTags

_PATTERNS = {
    "%artist%/%album%/%track% - %title%":
        lambda t: f"{t.artist}/{t.album}/{t.tracknumber} - {t.title}",
    "%albumartist%/%album%/%track% - %title%":
        lambda t: f"{t.albumartist or t.artist}/{t.album}/{t.tracknumber} - {t.title}",
    "%genre%/%artist%/%album%/%track% - %title%":
        lambda t: f"{t.genre}/{t.artist}/{t.album}/{t.tracknumber} - {t.title}",
    "%artist% - %album%/%track% - %title%":
        lambda t: f"{t.artist} - {t.album}/{t.tracknumber} - {t.title}",
    "%artist% - %title%":
        lambda t: f"{t.artist} - {t.title}",
    "%track% - %title%":
        lambda t: f"{t.tracknumber} - {t.title}",
}

_TEMPLATE_KEYS = {
    "artist": "artist",
    "album": "album",
    "albumartist": "albumartist",
    "track": "tracknumber",
    "title": "title",
    "genre": "genre",
    "year": "date",
}


def sanitize_filename_part(value: str) -> str:
    for ch in '<>:"/\\|?*':
        value = value.replace(ch, "")
    return value.strip().strip(".")


def render_pattern(tags: TrackTags, pattern: str) -> str:
    """Render a free-form pattern using tag values."""
    result = pattern
    for key, attr in _TEMPLATE_KEYS.items():
        val = getattr(tags, attr, "")
        result = result.replace(f"%{key}%", sanitize_filename_part(val or "Desconocido"))
    return result


def preview_rename(items: list[TrackTags], pattern: str) -> list[tuple[str, str]]:
    results = []

    # First try predefined patterns
    fn = _PATTERNS.get(pattern)
    for t in items:
        old = t.filepath
        ext = os.path.splitext(old)[1]
        base_dir = os.path.dirname(old)

        relative = sanitize_filename_part(fn(t)) if fn else render_pattern(t, pattern)

        new = os.path.join(base_dir, relative + ext)
        results.append((old, new))
    return results


def apply_rename(preview: list[tuple[str, str]]) -> tuple[int, int]:
    ok = 0
    fail = 0
    for old, new in preview:
        if old == new:
            continue
        try:
            os.makedirs(os.path.dirname(new), exist_ok=True)
            os.rename(old, new)
            ok += 1
        except OSError:
            fail += 1
    return ok, fail

