"""Golden contract for the canonical 1920×154 NowPlayingBar reference."""

import hashlib
import struct
from pathlib import Path

REFERENCE = Path("tests/golden/now_playing_bar_reference.png")
QML = Path("src/michi/presentation/qml/player/NowPlayingBar.qml")
REFERENCE_SHA256 = "fd731e61c87c772bbffd806b254a72c5d14f46c2b5141084fffcae54066e0dc5"


def _png_size(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert payload[12:16] == b"IHDR"
    return struct.unpack(">II", payload[16:24])


def test_canonical_reference_is_pinned_verbatim() -> None:
    """The supplied project reference is the visual source of truth."""
    assert _png_size(REFERENCE) == (1920, 154)
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == REFERENCE_SHA256


def test_qml_preserves_landmarks_in_a_responsive_three_zone_layout() -> None:
    """The reference composition scales without pinning the component to 1920 px."""
    qml = QML.read_text()
    required = (
        'objectName: "nowPlayingBar"',
        "implicitWidth: 800",
        "implicitHeight: 154",
        "readonly property bool compact",
        'objectName: "trackCard"',
        'objectName: "playbackZone"',
        'objectName: "outputZone"',
        'objectName: "timeline"',
        'objectName: "playPauseButton"',
        'objectName: "queueButton"',
        'objectName: "volumeSlider"',
        'objectName: "outputBadge"',
    )
    assert all(fragment in qml for fragment in required)
    assert "implicitWidth: 1920" not in qml
    assert "transportOrigin" not in qml
