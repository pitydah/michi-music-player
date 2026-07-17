pragma Singleton
import QtQuick

QtObject {
    // ── Fondo ──
    readonly property color bgBase: "#070A10"
    readonly property color bgCanvas: "#090B11"
    readonly property color bgApp: bgBase
    readonly property color bgContent: bgCanvas

    // ── Superficies ── Elevation 0-5
    readonly property color surfaceElevation0: bgCanvas
    readonly property color surfaceElevation1: "#0D0F16"
    readonly property color surfaceElevation2: "#11131C"
    readonly property color surfaceElevation3: "#141620"
    readonly property color surfaceElevation4: "#17191F"
    readonly property color surfaceElevation5: "#1A1C24"

    readonly property color surfaceCard: surfaceElevation1
    readonly property color surfaceCardHover: surfaceElevation2
    readonly property color surfaceCardElevated: surfaceElevation3
    readonly property color surfaceToolbar: Qt.rgba(0.027, 0.039, 0.063, 0.92)
    readonly property color surfaceSidebar: "#080A10"
    readonly property color surfacePopup: "#0F1219"
    readonly property color surfaceInput: "#0C0E15"
    readonly property color surfaceHero: "#0A0D14"
    readonly property color surfaceHeroGlow: Qt.rgba(0.561, 0.718, 1.0, 0.03)
    readonly property color surfaceInspector: "#0B0D14"
    readonly property color surfaceNowPlaying: surfaceElevation3
    readonly property color surfacePlaybackPanel: surfaceElevation3
    readonly property color surfaceOverlay: Qt.rgba(0.02, 0.03, 0.05, 0.85)

    // ── Estados de superficie ──
    readonly property color surfaceHover: Qt.rgba(1.0, 1.0, 1.0, 0.08)
    readonly property color surfacePressed: Qt.rgba(1.0, 1.0, 1.0, 0.12)
    readonly property color surfaceDisabled: Qt.rgba(1.0, 1.0, 1.0, 0.04)
    readonly property color surfaceSubtle: Qt.rgba(1.0, 1.0, 1.0, 0.03)

    // ── Controles ──
    readonly property color controlTrack: Qt.rgba(1.0, 1.0, 1.0, 0.08)
    readonly property color controlThumb: Qt.rgba(1.0, 1.0, 1.0, 0.90)
    readonly property color focusHalo: Qt.rgba(0.561, 0.718, 1.0, 0.18)

    // ── Bordes ──
    readonly property color borderSubtle: Qt.rgba(1.0, 1.0, 1.0, 0.05)
    readonly property color borderCard: Qt.rgba(1.0, 1.0, 1.0, 0.07)
    readonly property color borderInner: Qt.rgba(1.0, 1.0, 1.0, 0.03)
    readonly property color borderActive: "#8FB7FF"
    readonly property color borderHover: Qt.rgba(1.0, 1.0, 1.0, 0.15)
    readonly property color borderFocus: "#8FB7FF"
    readonly property color borderError: "#F87171"

    // ── Texto ──
    readonly property color textPrimary: "#F0F2F8"
    readonly property color textNormal: "#D0D4E0"
    readonly property color textSecondary: "#9098A8"
    readonly property color textTertiary: "#606878"
    readonly property color textMuted: textTertiary
    readonly property color textMeta: "#485068"
    readonly property color textOnAccent: bgBase
    readonly property color textOnError: bgBase
    readonly property color textOnSuccess: bgBase

    // ── Acento ──
    readonly property color accentPrimary: "#8FB7FF"
    readonly property color accentSecondary: "#A78BFA"
    readonly property color accentSoft: Qt.rgba(0.561, 0.718, 1.0, 0.10)
    readonly property color accentSelection: Qt.rgba(0.561, 0.718, 1.0, 0.18)

    // Aliases de compatibilidad
    readonly property color accent: accentPrimary
    readonly property color accentBlue: accentPrimary
    readonly property color accentSurface: accentSoft
    readonly property color experimental: accentSecondary

    // ── Estados ──
    readonly property color success: "#4ADE80"
    readonly property color warning: "#FBBF24"
    readonly property color error: "#F87171"
    readonly property color info: accentPrimary
    readonly property color disconnected: "#6B7280"

    // ── Badges ──
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
    readonly property color badgeMutedBg: Qt.rgba(1, 1, 1, 0.06)
    readonly property color badgeMutedText: textSecondary

    // ── Sombras ──
    readonly property color shadowSoft: Qt.rgba(0.0, 0.0, 0.0, 0.30)
    readonly property color shadowFloating: Qt.rgba(0.0, 0.0, 0.0, 0.45)

    // ── Skeleton ──
    readonly property color skeletonBase: surfaceCard
    readonly property color skeletonHighlight: surfaceCardHover

    // ── Now Playing ──
    readonly property color nowPlayingBackground: bgBase
    readonly property color nowPlayingBorder: Qt.rgba(1, 1, 1, 0.06)
    readonly property color nowPlayingTrack: "#24272E"
    readonly property color nowPlayingThumb: "#F92141"
    readonly property color nowPlayingThumbBorder: "#FFFFFF"
    readonly property color nowPlayingGradientStart: "#FF7903"
    readonly property color nowPlayingGradientMiddle: "#FF5D1C"
    readonly property color nowPlayingGradientEnd: "#FA393E"
    readonly property color nowPlayingTransportBg: "#1B1D23"
    readonly property color nowPlayingTransportBorder: Qt.rgba(255, 255, 255, 0.09)
    readonly property color nowPlayingTransportHover: Qt.rgba(255, 255, 255, 0.12)
    readonly property color nowPlayingTransportHoverBorder: Qt.rgba(255, 255, 255, 0.145)
    readonly property color nowPlayingTransportPressed: Qt.rgba(255, 255, 255, 0.055)
    readonly property color nowPlayingShuffleActive: Qt.rgba(249, 33, 65, 0.135)
    readonly property color nowPlayingShuffleActiveBorder: Qt.rgba(249, 33, 65, 0.26)
    readonly property color nowPlayingTransmitActive: Qt.rgba(52, 199, 89, 0.13)
    readonly property color nowPlayingTransmitActiveBorder: Qt.rgba(52, 199, 89, 0.28)
    readonly property color nowPlayingQualityBg: surfaceElevation4
    readonly property color nowPlayingQualityBorder: Qt.rgba(255, 255, 255, 0.08)
    readonly property color surfaceNowPlayingBorder: Qt.rgba(1.0, 1.0, 1.0, 0.06)
    readonly property color overlayDark: Qt.rgba(0.02, 0.03, 0.05, 0.70)
}
