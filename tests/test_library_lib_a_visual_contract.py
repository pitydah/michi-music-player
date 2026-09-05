"""LIB-A P2-G/P2-K — i18n scanner con allowlist + contratos visuales.

COR53: strings de usuario obvias sin qsTr en las superficies tocadas por
LIB-A (scanner con allowlist mínima); COR54-57: sin folders/navegador.
"""

from pathlib import Path

import pytest

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"

# Superficies Library tocadas por LIB-A.
SURFACES = (
    "views/LibraryHeader.qml",
    "views/LibraryTabs.qml",
    "views/LibraryContentHost.qml",
    "views/LibraryToolbar.qml",
    "views/SongsView.qml",
    "views/FavoritesView.qml",
    "views/HistoryView.qml",
    "views/RecentlyAddedView.qml",
    "views/AlbumDetailView.qml",
    "views/ArtistDetailView.qml",
    "views/AlbumsView.qml",
    "media/TrackTableHeaderContextMenu.qml",
    "media/ResizableTrackHeader.qml",
    "media/TrackRow.qml",
)

# Allowlist explícita y mínima: solo símbolos/valores técnicos inmutables/
# claves internas (nunca frases de usuario).
_ALLOWLIST = {
    "ART",
    "TITLE",
    "ARTIST",
    "ALBUM",
    "FORMAT",
    "SAMPLE RATE",
    "BIT DEPTH",
    "DSD RATE",
    "BITRATE",
    "CHANNELS",
    "FILE SIZE",
    "GENRE",
    "COMPOSER",
    "YEAR",
    "DURATION",
    "VIEWS",
    "TRACKS",
    "TRACK TABLE",
    "IDENTITY",
    "MUSICAL CONTEXT",
    "AUDIO",
    "METADATA",
    "TIME",
    "UTILITY",
    "COLUMN LAYOUT",
    "COLUMNS",
    "CUSTOMIZE COLUMNS",
    "DISC",
    "Back",
    "Library",
    "Unknown",
    "Standard",
    "Mixed formats",
    "High-resolution PCM",
    "Path",
    "About this album",
    "About the artist",
    "Track information",
    "LIBRARY QUALITY",
    "Album facts",
    "Format",
    "Sample rate",
    "Bit depth",
    "Channels",
    "File size",
    "Album",
    "Artist",
    "Genre",
}


def _raw_string_tokens(text: str):
    """Strings en asignaciones visibles sin qsTr: text/label/title/
    message/placeholderText con contenido de letras."""
    import re

    tokens = []
    for match in re.finditer(
        r"\b(?:text|label|title|message|placeholderText|subtitle|accessibleName)"
        r"\s*:\s*\"([^\"]+)\"",
        text,
    ):
        token = match.group(1)
        if any(ch.isalpha() for ch in token):
            tokens.append(token)
    return tokens


@pytest.mark.parametrize("surface", SURFACES)
def test_cor53_no_raw_user_strings(surface):
    """COR53: las strings visibles de usuario van por qsTr (allowlist
    técnica mínima)."""
    source = (QML / surface).read_text(encoding="utf-8")
    offenders = []
    for token in _raw_string_tokens(source):
        if token not in _ALLOWLIST and not token.startswith("%"):
            offenders.append(token)
    assert not offenders, f"{surface}: strings sin qsTr: {offenders}"


def test_cor54_57_no_filesystem_browser():
    """COR54-57: sin tab/route/view de folders ni navegador de archivos."""
    tabs = (QML / "views" / "LibraryTabs.qml").read_text()
    host = (QML / "views" / "LibraryContentHost.qml").read_text()
    assert "folders" not in tabs
    assert '"folders"' not in host
    assert not (QML / "views" / "FoldersView.qml").exists()
    for surface in ("views/LibraryTabs.qml", "shell/Sidebar.qml"):
        source = (QML / surface).read_text()
        for forbidden in ("os.listdir", "Path.iterdir", "QDir"):
            assert forbidden not in source
