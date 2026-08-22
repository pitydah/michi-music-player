pragma Singleton
import QtQuick

QtObject {
    readonly property color backplane: MichiPalette.obsidian
    readonly property color contentSurface: MichiPalette.graphite
    readonly property color contentSurfaceTop: Qt.rgba(0.082, 0.098, 0.129, 1)
    readonly property color contentSurfaceBottom: Qt.rgba(0.055, 0.064, 0.086, 1)
    readonly property color contentAmbientBlue: Qt.rgba(0.298, 0.651, 1, 0.055)
    readonly property color contentAmbientPurple: Qt.rgba(0.604, 0.486, 1, 0.04)
    readonly property color controlSurface: Qt.rgba(0.067, 0.078, 0.114, 0.84)
    readonly property color controlSurfaceStrong: Qt.rgba(0.067, 0.078, 0.114, 0.94)
    readonly property color surfaceHover: Qt.rgba(1, 1, 1, 0.055)
    readonly property color surfacePressed: Qt.rgba(1, 1, 1, 0.09)
    readonly property color surfaceSelected: Qt.rgba(0.298, 0.651, 1, 0.14)
    readonly property color borderSubtle: Qt.rgba(1, 1, 1, 0.07)
    readonly property color borderStrong: Qt.rgba(1, 1, 1, 0.12)
    readonly property color innerHighlight: Qt.rgba(1, 1, 1, 0.075)
    readonly property color innerHighlightStrong: Qt.rgba(1, 1, 1, 0.32)
    readonly property color glassShadow: Qt.rgba(0, 0, 0, 0.26)
    readonly property color glassShadowNear: Qt.rgba(0, 0, 0, 0.18)
    readonly property color glassShadowFar: Qt.rgba(0, 0, 0, 0.075)
    readonly property color glassInnerBorder: Qt.rgba(1, 1, 1, 0.035)
    readonly property color glassSheen: Qt.rgba(1, 1, 1, 0.06)
    readonly property color glassGlint: Qt.rgba(1, 1, 1, 0.07)
    readonly property color glassGlintStrong: Qt.rgba(1, 1, 1, 0.09)
    readonly property color auroraActive: MichiPalette.auroraBlue
    readonly property color auroraHover: "#69B5FF"
    readonly property color auroraPressed: "#378EDB"
    readonly property color focusRing: Qt.rgba(0.298, 0.651, 1, 0.9)
    readonly property color auroraBorderSubtle: Qt.rgba(0.298, 0.651, 1, 0.2)
    readonly property color auroraCyanSurface: Qt.rgba(0.129, 0.839, 0.902, 0.08)
    readonly property color auroraCyanBorder: Qt.rgba(0.129, 0.839, 0.902, 0.28)
    readonly property color auroraCyanBorderSubtle: Qt.rgba(0.129, 0.839, 0.902, 0.20)
    readonly property color auroraPurpleSurface: Qt.rgba(0.604, 0.486, 1, 0.14)
    readonly property color auroraPurpleBorder: Qt.rgba(0.604, 0.486, 1, 0.34)
    readonly property color auroraBlueGlow: Qt.rgba(0.298, 0.651, 1, 0.34)
    readonly property color auroraCyanBorderStrong: Qt.rgba(0.129, 0.839, 0.902, 0.38)
    readonly property color auroraPurpleSurfaceSoft: Qt.rgba(0.604, 0.486, 1, 0.10)
    readonly property color auroraPurpleBorderSoft: Qt.rgba(0.604, 0.486, 1, 0.24)
    readonly property color auroraPurpleBorderMedium: Qt.rgba(0.604, 0.486, 1, 0.30)
    readonly property color scrim: Qt.rgba(0.02, 0.025, 0.04, 0.62)
    readonly property color scrimStrong: Qt.rgba(0.02, 0.025, 0.04, 0.72)
    readonly property color artworkScrim: Qt.rgba(0, 0, 0, 0.12)
    readonly property color artworkScrimHover: Qt.rgba(0, 0, 0, 0.26)

    function statusSurface(toneColor) {
        return Qt.rgba(toneColor.r, toneColor.g, toneColor.b, 0.09)
    }

    function statusBorder(toneColor) {
        return Qt.rgba(toneColor.r, toneColor.g, toneColor.b, 0.24)
    }

    function glassTop(elevated, materialOpacity) {
        return elevated
            ? Qt.rgba(0.094, 0.11, 0.151, Math.min(1, materialOpacity + 0.05))
            : Qt.rgba(0.08, 0.094, 0.129, Math.min(1, materialOpacity + 0.02))
    }

    function glassBottom(elevated, materialOpacity) {
        return elevated
            ? Qt.rgba(0.057, 0.068, 0.096, Math.min(1, materialOpacity + 0.08))
            : Qt.rgba(0.052, 0.062, 0.088, materialOpacity)
    }

    function accentBorder(accentColor) {
        return Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.22)
    }

    function headerAccent(accentColor) {
        return Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.16)
    }
}
