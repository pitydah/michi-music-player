pragma Singleton
import QtQuick

QtObject {
    property bool lightMode: false

    // ── Fondo ──
    readonly property color bgBase: lightMode ? "#F6F8FC" : "#06080D"
    readonly property color bgCanvas: lightMode ? "#EEF2F8" : "#090B11"
    readonly property color bgApp: bgBase
    readonly property color bgContent: bgCanvas

    // ── Superficies ── Elevation 0-5
    readonly property color surfaceElevation0: lightMode ? "#FAFAFE" : bgCanvas
    readonly property color surfaceElevation1: lightMode ? "#F2F5FA" : "#0D111A"
    readonly property color surfaceElevation2: lightMode ? "#E9EEF6" : "#111722"
    readonly property color surfaceElevation3: lightMode ? "#E1E8F2" : "#151C28"
    readonly property color surfaceElevation4: lightMode ? "#D8E1ED" : "#192230"
    readonly property color surfaceElevation5: lightMode ? "#CFDAE8" : "#1D2838"

    readonly property color surfaceCard: lightMode ? Qt.rgba(1.0, 1.0, 1.0, 0.72)
                                                   : Qt.rgba(0.075, 0.094, 0.133, 0.78)
    readonly property color surfaceCardHover: lightMode ? Qt.rgba(1.0, 1.0, 1.0, 0.94)
                                                        : Qt.rgba(0.102, 0.129, 0.184, 0.88)
    readonly property color surfaceCardElevated: surfaceElevation3
    readonly property color surfaceToolbar: lightMode ? Qt.rgba(0.965, 0.976, 0.996, 0.90)
                                                      : Qt.rgba(0.035, 0.051, 0.082, 0.88)
    readonly property color surfaceSidebar: lightMode ? "#EEF3F9" : "#080B12"
    readonly property color surfacePopup: lightMode ? "#FAFAFE" : "#0F1219"
    readonly property color surfaceInput: lightMode ? "#FFFFFF" : "#0C0E15"
    readonly property color surfaceHero: lightMode ? "#EDF3FB" : "#0A101A"
    readonly property color surfaceHeroGlow: lightMode ? Qt.rgba(0.561, 0.718, 1.0, 0.10)
                                                       : Qt.rgba(0.561, 0.718, 1.0, 0.07)
    readonly property color surfaceInspector: lightMode ? "#F5F6FA" : "#0B0D14"
    readonly property color surfaceNowPlaying: surfaceElevation3
    readonly property color surfacePlaybackPanel: surfaceElevation3
    readonly property color surfaceOverlay: lightMode ? Qt.rgba(0.9, 0.91, 0.93, 0.85) : Qt.rgba(0.02, 0.03, 0.05, 0.85)

    // ── Estados de superficie ──
    readonly property color surfaceHover: lightMode ? Qt.rgba(0, 0, 0, 0.05) : Qt.rgba(1.0, 1.0, 1.0, 0.08)
    readonly property color surfacePressed: lightMode ? Qt.rgba(0, 0, 0, 0.10) : Qt.rgba(1.0, 1.0, 1.0, 0.12)
    readonly property color surfaceDisabled: lightMode ? Qt.rgba(0, 0, 0, 0.03) : Qt.rgba(1.0, 1.0, 1.0, 0.04)
    readonly property color surfaceSubtle: lightMode ? Qt.rgba(0, 0, 0, 0.02) : Qt.rgba(1.0, 1.0, 1.0, 0.03)

    // ── Controles ──
    readonly property color controlTrack: lightMode ? Qt.rgba(0, 0, 0, 0.10) : Qt.rgba(1.0, 1.0, 1.0, 0.08)
    readonly property color controlThumb: lightMode ? Qt.rgba(0, 0, 0, 0.80) : Qt.rgba(1.0, 1.0, 1.0, 0.90)
    readonly property color focusHalo: lightMode ? Qt.rgba(0.561, 0.718, 1.0, 0.26)
                                                 : Qt.rgba(0.561, 0.718, 1.0, 0.22)

    // ── Bordes ──
    readonly property color borderSubtle: lightMode ? Qt.rgba(0, 0, 0, 0.08) : Qt.rgba(1.0, 1.0, 1.0, 0.05)
    readonly property color borderCard: lightMode ? Qt.rgba(0.15, 0.24, 0.38, 0.12)
                                                  : Qt.rgba(0.72, 0.82, 1.0, 0.10)
    readonly property color borderInner: lightMode ? Qt.rgba(0, 0, 0, 0.04) : Qt.rgba(1.0, 1.0, 1.0, 0.03)
    readonly property color borderActive: "#8FB7FF"
    readonly property color borderHover: lightMode ? Qt.rgba(0.24, 0.42, 0.70, 0.28)
                                                   : Qt.rgba(0.561, 0.718, 1.0, 0.28)
    readonly property color borderFocus: "#8FB7FF"
    readonly property color borderError: "#F87171"

    // ── Texto ──
    readonly property color textPrimary: lightMode ? "#1A1D26" : "#F2F5FA"
    readonly property color textNormal: lightMode ? "#3A3D46" : "#D0D4E0"
    readonly property color textSecondary: lightMode ? "#707880" : "#A9B4C7"
    readonly property color textTertiary: lightMode ? "#9098A0" : "#78869D"
    readonly property color textMuted: lightMode ? "#A0A8B0" : "#566176"
    readonly property color textMeta: lightMode ? "#B0B8C0" : "#485068"
    readonly property color textOnAccent: lightMode ? "#FFFFFF" : bgBase
    readonly property color textOnError: lightMode ? "#FFFFFF" : bgBase
    readonly property color textOnSuccess: lightMode ? "#FFFFFF" : bgBase

    // Cool blue is Michi's navigation and interaction accent. Warm colors are
    // intentionally scoped to playback and equalizer controls below.
    readonly property color accentPrimary: "#8FB7FF"
    readonly property color accentInfo: "#8FB7FF"
    readonly property color accentExperimental: "#A78BFA"
    readonly property color accentSecondary: accentExperimental
    readonly property color accentSoft: Qt.rgba(0.561, 0.718, 1.0, lightMode ? 0.16 : 0.12)
    readonly property color accentSelection: Qt.rgba(0.561, 0.718, 1.0, lightMode ? 0.20 : 0.16)
    readonly property color accent: accentPrimary
    readonly property color accentBlue: accentInfo
    readonly property color accentSurface: accentSoft
    readonly property color experimental: accentExperimental

    readonly property color success: "#4ADE80"
    readonly property color warning: "#FBBF24"
    readonly property color error: "#F87171"
    readonly property color info: accentInfo
    readonly property color disconnected: lightMode ? "#9CA3AF" : "#6B7280"

    readonly property color badgeInfoBg: Qt.rgba(0.561, 0.718, 1.0, 0.12)
    readonly property color badgeInfoText: accentInfo
    readonly property color badgeActiveBg: Qt.rgba(0.29, 0.87, 0.50, 0.20)
    readonly property color badgeActiveText: success
    readonly property color badgeExperimentalBg: Qt.rgba(0.655, 0.545, 0.980, 0.15)
    readonly property color badgeExperimentalText: accentSecondary
    readonly property color badgeWarningBg: Qt.rgba(1, 0.75, 0.14, 0.20)
    readonly property color badgeWarningText: warning
    readonly property color badgeDangerBg: Qt.rgba(1, 0.44, 0.44, 0.20)
    readonly property color badgeDangerText: error
    readonly property color badgeMutedBg: lightMode ? Qt.rgba(0, 0, 0, 0.06) : Qt.rgba(1, 1, 1, 0.06)
    readonly property color badgeMutedText: textSecondary

    readonly property color shadowSoft: lightMode ? Qt.rgba(0.08, 0.14, 0.24, 0.12)
                                                  : Qt.rgba(0.0, 0.0, 0.0, 0.34)
    readonly property color shadowFloating: lightMode ? Qt.rgba(0.08, 0.14, 0.24, 0.18)
                                                      : Qt.rgba(0.0, 0.0, 0.0, 0.52)

    readonly property color skeletonBase: surfaceCard
    readonly property color skeletonHighlight: surfaceCardHover

    readonly property color nowPlayingBackground: lightMode ? "#F5F6FA" : bgBase
    readonly property color nowPlayingBorder: lightMode ? Qt.rgba(0, 0, 0, 0.08) : Qt.rgba(1, 1, 1, 0.06)
    readonly property color nowPlayingTrack: lightMode ? "#D0D4DC" : "#24272E"
    readonly property color nowPlayingThumb: "#FF7A00"
    readonly property color nowPlayingThumbBorder: lightMode ? "#FFFFFF" : "#FFFFFF"
    readonly property color nowPlayingGradientStart: "#FF7A00"
    readonly property color nowPlayingGradientMiddle: "#FF4F72"
    readonly property color nowPlayingGradientEnd: "#C65CFF"
    readonly property color nowPlayingTransportBg: lightMode ? "#E8EAF0" : "#1B1D23"
    readonly property color nowPlayingTransportBorder: lightMode ? Qt.rgba(0, 0, 0, 0.10) : Qt.rgba(255, 255, 255, 0.09)
    readonly property color nowPlayingTransportHover: lightMode ? Qt.rgba(0, 0, 0, 0.06) : Qt.rgba(255, 255, 255, 0.12)
    readonly property color nowPlayingTransportHoverBorder: lightMode ? Qt.rgba(0, 0, 0, 0.15) : Qt.rgba(255, 255, 255, 0.145)
    readonly property color nowPlayingTransportPressed: lightMode ? Qt.rgba(0, 0, 0, 0.03) : Qt.rgba(255, 255, 255, 0.055)
    readonly property color nowPlayingShuffleActive: Qt.rgba(249, 33, 65, 0.135)
    readonly property color nowPlayingShuffleActiveBorder: Qt.rgba(249, 33, 65, 0.26)
    readonly property color nowPlayingTransmitActive: Qt.rgba(52, 199, 89, 0.13)
    readonly property color nowPlayingTransmitActiveBorder: Qt.rgba(52, 199, 89, 0.28)
    readonly property color nowPlayingQualityBg: surfaceElevation4
    readonly property color nowPlayingQualityBorder: Qt.rgba(255, 255, 255, 0.08)
    readonly property color nowPlayingMetaText: lightMode ? "#B0B8C0" : "#485068"
    readonly property color surfaceNowPlayingBorder: Qt.rgba(1.0, 1.0, 1.0, 0.06)
    readonly property color overlayDark: Qt.rgba(0.02, 0.03, 0.05, 0.70)

    function toggleLightMode() {
        lightMode = !lightMode
    }
}
