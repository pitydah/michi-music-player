"""Metadata diagnostics — detect issues across loaded TrackTags."""

from metadata.tag_model import TrackTags


def diagnose_items(items: list[TrackTags]) -> dict:
    return {
        "total": len(items),
        "dirty": sum(1 for t in items if t.dirty),
        "no_cover": sum(1 for t in items if not t.has_artwork),
        "no_title": sum(1 for t in items if not t.title),
        "no_artist": sum(1 for t in items if not t.artist),
        "no_album": sum(1 for t in items if not t.album),
        "no_albumartist": sum(1 for t in items if not t.albumartist),
        "no_tracknumber": sum(1 for t in items if not t.tracknumber),
        "no_year": sum(1 for t in items if not t.date),
        "no_genre": sum(1 for t in items if not t.genre),
        "errors": sum(1 for t in items if t.error),
    }


NAV_CATEGORIES = [
    ("all", "Todos los archivos", "total"),
    ("dirty", "Modificados", "dirty"),
    ("no_cover", "Sin carátula", "no_cover"),
    ("no_artist", "Sin artista", "no_artist"),
    ("no_album", "Sin álbum", "no_album"),
    ("no_albumartist", "Sin artista de álbum", "no_albumartist"),
    ("no_tracknumber", "Sin nº pista", "no_tracknumber"),
    ("no_year", "Año vacío", "no_year"),
    ("no_genre", "Género vacío", "no_genre"),
    ("errors", "Con errores", "errors"),
]
