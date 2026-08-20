pragma Singleton
import QtQuick

QtObject {
    readonly property color backplane: MichiPalette.obsidian
    readonly property color contentSurface: MichiPalette.graphite
    readonly property color controlSurface: Qt.rgba(0.067, 0.078, 0.114, 0.84)
    readonly property color controlSurfaceStrong: Qt.rgba(0.067, 0.078, 0.114, 0.94)
    readonly property color surfaceHover: Qt.rgba(1, 1, 1, 0.055)
    readonly property color surfacePressed: Qt.rgba(1, 1, 1, 0.09)
    readonly property color surfaceSelected: Qt.rgba(0.298, 0.651, 1, 0.14)
    readonly property color borderSubtle: Qt.rgba(1, 1, 1, 0.07)
    readonly property color borderStrong: Qt.rgba(1, 1, 1, 0.12)
    readonly property color innerHighlight: Qt.rgba(1, 1, 1, 0.045)
    readonly property color auroraActive: MichiPalette.auroraBlue
    readonly property color auroraHover: "#69B5FF"
    readonly property color auroraPressed: "#378EDB"
    readonly property color focusRing: Qt.rgba(0.298, 0.651, 1, 0.9)
}
