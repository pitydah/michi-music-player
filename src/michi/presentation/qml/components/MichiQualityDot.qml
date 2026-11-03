import QtQuick
import "../theme"

// Nominal source-quality dot. It never encodes path proof: the proof state is
// rendered separately so a Hi-Res badge cannot imply verification.
Rectangle {
    id: root
    property string qualityClass: "unknown"
    property real diameter: 8
    width: diameter
    height: diameter
    radius: diameter / 2
    color: qualityClass === "pcm_hires"
        ? MichiPalette.auroraBlue
        : qualityClass === "dsd" ? MichiPalette.auroraPurple
        : qualityClass === "pcm_standard" ? MichiPalette.success
        : qualityClass === "lossy" ? MichiPalette.warning
        : MichiPalette.textMuted
    Accessible.ignored: true
}
