#!/usr/bin/env python3
"""qml_decommission_audit.py — W1/W3 domain audit for decommission matrix."""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UI_DIR = REPO / "ui"
CORE_DIR = REPO / "core"
MATRIX_PATH = REPO / "config" / "qwidget_decommission_matrix.yaml"

SQL_PATTERN = re.compile(r'\b(SELECT\s+\w+|INSERT\s+INTO\s+\w+|UPDATE\s+\w+\s+SET|DELETE\s+FROM\s+\w+)\b', re.IGNORECASE)
FS_PATTERN = re.compile(r'os\.(path|listdir|walk|makedirs|remove|rename|stat|unlink|rmdir|scandir)', re.IGNORECASE)
MUTAGEN_PATTERN = re.compile(r'\b(mutagen|tinytag|eyed3|musicbrainzngs|discogs_client)\b', re.IGNORECASE)
THREAD_PATTERN = re.compile(r'threading\.Thread\(')
PLAYLIST_IO_PATTERN = re.compile(r'\b(m3u|pls|xspf|playlist.*(import|export|parse|serialize))\b', re.IGNORECASE)


def check_domain(domain: str, ui_files: list[Path]) -> dict:
    domain_files = [f for f in ui_files if domain.replace("_", "") in str(f).replace("_", "").lower()]
    sql_count = 0
    fs_count = 0
    mutagen_count = 0
    thread_count = 0
    playlist_io_count = 0
    for f in domain_files:
        text = f.read_text()
        sql_count += len(SQL_PATTERN.findall(text))
        fs_count += len(FS_PATTERN.findall(text))
        mutagen_count += len(MUTAGEN_PATTERN.findall(text))
        thread_count += len(THREAD_PATTERN.findall(text))
        playlist_io_count += len(PLAYLIST_IO_PATTERN.findall(text))
    business_rules = sql_count + mutagen_count + thread_count + playlist_io_count
    return {
        "domain": domain,
        "files_checked": len(domain_files),
        "sql_in_ui": sql_count,
        "filesystem_in_ui": fs_count,
        "metadata_parsing_in_ui": mutagen_count,
        "raw_threading_in_ui": thread_count,
        "playlist_io_in_ui": playlist_io_count,
        "business_rules_in_ui": business_rules,
        "pass": business_rules == 0 and fs_count == 0,
    }


def main() -> int:
    ui_files = sorted(UI_DIR.rglob("*.py"))
    ui_files = [f for f in ui_files if not f.name.startswith("__")]

    domains = [
        "nowplaying", "queue", "lyrics", "settings", "output_profiles",
        "metadata", "smart_tagging", "diagnostics",
        "library", "album", "artist", "folders", "sources",
        "playlists", "history", "global_search", "mix", "radio",
        "eq", "audio_lab", "devices", "connections", "home_audio",
    ]

    results = []
    all_pass = True
    for d in domains:
        r = check_domain(d, ui_files)
        results.append(r)
        status = "PASS" if r["pass"] else "FAIL"
        print(f"  {d:25s} {status:5s}  biz_rules={r['business_rules_in_ui']:2d}  fs={r['filesystem_in_ui']:2d}")
        if not r["pass"]:
            all_pass = False

    print(f"\nDomain audit: {'ALL PASS' if all_pass else 'SOME FAIL'}")
    print(json.dumps({"results": results, "pass": all_pass}, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
