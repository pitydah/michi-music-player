from __future__ import annotations

import os

def save_sidecar(audio_path: str, lyrics_text: str, extension: str = ".lrc") -> dict:
    if not audio_path or not os.path.isfile(audio_path):
        return {"ok": False, "error": "INVALID_AUDIO_PATH"}
    directory = os.path.dirname(audio_path)
    base = os.path.splitext(os.path.basename(audio_path))[0]
    sidecar_path = os.path.join(directory, base + extension)
    try:
        with open(sidecar_path, "w", encoding="utf-8") as f:
            f.write(lyrics_text)
    except OSError as e:
        return {"ok": False, "error": f"WRITE_FAILED: {e}"}
    result: dict = {"ok": True, "path": sidecar_path, "embedded": False}
    _write_embedded_tags(audio_path, lyrics_text, result)
    return result


def _write_embedded_tags(audio_path: str, lyrics_text: str, result: dict):
    try:
        import mutagen
        import mutagen.flac
        import mutagen.id3
        import mutagen.mp4
        import mutagen.oggvorbis
    except ImportError:
        return

    try:
        f = mutagen.File(audio_path)
        if f is None:
            return
    except Exception:
        return

    ext = os.path.splitext(audio_path)[1].lower()

    try:
        if ext == ".mp3":
            _write_mp3_uslt(f, lyrics_text)
        elif ext in (".flac", ".ogg", ".opus"):
            _write_vorbis_lyrics(f, lyrics_text)
        elif ext in (".mp4", ".m4a", ".m4b"):
            _write_mp4_lyrics(f, lyrics_text)
        else:
            return
        f.save()
        result["embedded"] = True
    except Exception:
        pass


def _write_mp3_uslt(f, lyrics_text: str):
    from mutagen.id3 import USLT
    if f.tags is None:
        f.add_tags()
    f.tags.delall("USLT")
    f.tags.add(USLT(encoding=3, lang="eng", desc="", text=lyrics_text))


def _write_vorbis_lyrics(f, lyrics_text: str):
    if not hasattr(f, "tags") or f.tags is None:
        return
    f.tags["LYRICS"] = lyrics_text


def _write_mp4_lyrics(f, lyrics_text: str):
    if not hasattr(f, "tags") or f.tags is None:
        return
    f.tags["\xa9lyr"] = [lyrics_text]
