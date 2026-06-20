"""Batch tag actions — apply operations across multiple TrackTags."""
from metadata.tag_model import TrackTags


def apply_field_to_all(items: list[TrackTags], field: str, value: str):
    for t in items:
        t.set_field(field, value)


def auto_number_tracks(items: list[TrackTags], start: int = 1):
    for i, t in enumerate(items):
        t.set_field("tracknumber", str(start + i))


def normalize_spaces(items: list[TrackTags]):
    text_fields = ["title", "artist", "album", "albumartist", "genre", "composer", "comment"]
    for t in items:
        for f in text_fields:
            val = getattr(t, f, "").strip()
            if "  " in val:
                val = " ".join(val.split())
            if val != getattr(t, f, ""):
                t.set_field(f, val)


def title_case(items: list[TrackTags]):
    text_fields = ["title", "artist", "album", "albumartist", "composer"]
    for t in items:
        for f in text_fields:
            val = getattr(t, f, "")
            if val and val != val.title():
                t.set_field(f, val.title())


def search_replace(items: list[TrackTags], field: str, old: str, new: str):
    for t in items:
        val = getattr(t, field, "")
        if old in val:
            t.set_field(field, val.replace(old, new))


def clear_field(items: list[TrackTags], field: str):
    for t in items:
        t.set_field(field, "")


def copy_field(items: list[TrackTags], source_field: str, target_field: str):
    for t in items:
        t.set_field(target_field, getattr(t, source_field, ""))


def trim_all_fields(items: list[TrackTags]):
    text_fields = TrackTags.TEXT_FIELDS
    for t in items:
        for f in text_fields:
            val = getattr(t, f, "")
            trimmed = val.strip()
            if trimmed != val:
                t.set_field(f, trimmed)
