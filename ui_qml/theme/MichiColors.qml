pragma Singleton
import QtQuick

QtObject {
    property bool lightMode: false

    // ── Fondo ──
    readonly property color bgBase: lightMode ? "#F5F6FA" : "#070A10"
    readonly property color bgCanvas: lightMode ? "#EEF0F5" : "#090B11"
    readonly property color bgApp: bgBase
    readonly property color bgContent: bgCanvas

    // ── Superficies ── Elevation 0-5
    readonly property color surfaceElevation0: lightMode ? "#FAFAFE" : bgCanvas
    readonly property color surfaceElevation1: lightMode ? "#F0F2F7" : "#0D0F16"
    readonly property color surfaceElevation2: lightMode ? "#E8EAF0" : "#11131C"
    readonly property color surfaceElevation3: lightMode ? "#E0E3EA" : "#141620"
    readonly property color surfaceElevation4: lightMode ? "#D8DBE3" : "#17191F"
    readonly property color surfaceElevation5: lightMode ? "#D0D4DC" : "#1A1C24"

    readonly property color surfaceCard: surfaceElevation1
    readonly property color surfaceCardHover: surfaceElevation2
    readonly property color surfaceCardElevated: surfaceElevation3
    readonly property color surfaceToolbar: lightMode ? Qt.rgba(0.96, 0.97, 0.98, 0.92) : Qt.rgba(0.027, 0.039, 0.063, 0.92)
    readonly property color surfaceSidebar: lightMode ? "#F0F2F7" : "#080A10"
    readonly property color surfacePopup: lightMode ? "#FAFAFE" : "#0F1219"
    readonly property color surfaceInput: lightMode ? "#FFFFFF" : "#0C0E15"
    readonly property color surfaceHero: lightMode ? "#F0F2F7" : "#0A0D14"
    readonly property color surfaceHeroGlow: lightMode ? Qt.rgba(0.561, 0.718, 1.0, 0.06) : Qt.rgba(0.561, 0.718, 1.0, 0.03)
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
    readonly property color focusHalo: lightMode ? Qt.rgba(0.561, 0.718, 1.0, 0.30) : Qt.rgba(0.561, 0.718, 1.0, 0.18)

    // ── Bordes ──
    readonly property color borderSubtle: lightMode ? Qt.rgba(0, 0, 0, 0.08) : Qt.rgba(1.0, 1.0, 1.0, 0.05)
    readonly property color borderCard: lightMode ? Qt.rgba(0, 0, 0, 0.10) : Qt.rgba(1.0, 1.0, 1.0, 0.07)
    readonly property color borderInner: lightMode ? Qt.rgba(0, 0, 0, 0.04) : Qt.rgba(1.0, 1.0, 1.0, 0.03)
    readonly property color borderActive: "#8FB7FF"
    readonly property color borderHover: lightMode ? Qt.rgba(0, 0, 0, 0.18) : Qt.rgba(1.0, 1.0, 1.0, 0.15)
    readonly property color borderFocus: "#8FB7FF"
    readonly property color borderError: "#F87171"

    // ── Texto ──
    readonly property color textPrimary: lightMode ? "#1A1D26" : "#F0F2F8"
    readonly property color textNormal: lightMode ? "#3A3D46" : "#D0D4E0"
    readonly property color textSecondary: lightMode ? "#707880" : "#9098A8"
    readonly property color textTertiary: lightMode ? "#9098A0" : "#606878"
    readonly property color textMuted: textTertiary
    readonly property color textMeta: lightMode ? "#A0A8B0" : "#485068"
    readonly property color textOnAccent: lightMode ? "#FFFFFF" : bgBase
    readonly property color textOnError: lightMode ? "#FFFFFF" : bgBase
    readonly property color textOnSuccess: lightMode ? "#FFFFFF" : bgBase

    readonly property color accentPrimary: "#8FB7FF"
    readonly property color accentSecondary: "#A78BFA"
    readonly property color accentSoft: Qt.rgba(0.561, 0.718, 1.0, lightMode ? 0.15 : 0.10)
    readonly property color accentSelection: Qt.rgba(0.561, 0.718, 1.0, lightMode ? 0.20 : 0.18)
    readonly property color accent: accentPrimary
    readonly property color accentBlue: accentPrimary
    readonly property color accentSurface: accentSoft
    readonly property color experimental: accentSecondary

    readonly property color success: "#4ADE80"
    readonly property color warning: "#FBBF24"
    readonly property color error: "#F87171"
    readonly property color info: accentPrimary
    readonly property color disconnected: lightMode ? "#9CA3AF" : "#6B7280"

    readonly property color badgeInfoBg: Qt.rgba(0.561, 0.718, 1.0, 0.12)
    readonly property color badgeInfoText: accentPrimary
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

    readonly property color shadowSoft: lightMode ? Qt.rgba(0, 0, 0, 0.10) : Qt.rgba(0.0, 0.0, 0.0, 0.30)
    readonly property color shadowFloating: lightMode ? Qt.rgba(0, 0, 0, 0.15) : Qt.rgba(0.0, 0.0, 0.0, 0.45)

    readonly property color skeletonBase: surfaceCard
    readonly property color skeletonHighlight: surfaceCardHover

    readonly property color nowPlayingBackground: lightMode ? "#F5F6FA" : bgBase
    readonly property color nowPlayingBorder: lightMode ? Qt.rgba(0, 0, 0, 0.08) : Qt.rgba(1, 1, 1, 0.06)
    readonly property color nowPlayingTrack: lightMode ? "#D0D4DC" : "#24272E"
    readonly property color nowPlayingThumb: "#F92141"
    readonly property color nowPlayingThumbBorder: lightMode ? "#FFFFFF" : "#FFFFFF"
    readonly property color nowPlayingGradientStart: "#FF7903"
    readonly property color nowPlayingGradientMiddle: "#FF5D1C"
    readonly property color nowPlayingGradientEnd: "#FA393E"
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
    readonly property color surfaceNowPlayingBorder: Qt.rgba(1.0, 1.0, 1.0, 0.06)
    readonly property color overlayDark: Qt.rgba(0.02, 0.03, 0.05, 0.70)

    function toggleLightMode() {
        lightMode = !lightMode
    }
}
