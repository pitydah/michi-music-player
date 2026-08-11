pragma Singleton
import QtQuick

QtObject {
    // ── Palette ──────────────────────────────────────────────
    readonly property color backgroundBase: "#090B11"
    readonly property color backgroundRaised: "#0F1220"

    readonly property color surfacePrimary: "#141829"
    readonly property color surfaceSecondary: "#1A1F35"
    readonly property color surfaceHover: "#1E2440"
    readonly property color surfacePressed: "#252C4A"
    readonly property color surfaceSelected: "#1E2848"

    readonly property color textPrimary: "#E4E6F0"
    readonly property color textSecondary: "#9598B0"
    readonly property color textMuted: "#5E6180"
    readonly property color textDisabled: "#3A3D55"

    readonly property color accent: "#C06C9A"
    readonly property color accentHover: "#D17DAB"
    readonly property color accentPressed: "#A8557A"

    readonly property color borderSubtle: "#1E2440"
    readonly property color borderStrong: "#2A3155"

    readonly property color success: "#5C9E6D"
    readonly property color warning: "#C9A24B"
    readonly property color error: "#C95B6B"

    // ── Spacing ──────────────────────────────────────────────
    readonly property int space2: 2
    readonly property int space4: 4
    readonly property int space6: 6
    readonly property int space8: 8
    readonly property int space12: 12
    readonly property int space16: 16
    readonly property int space20: 20
    readonly property int space24: 24
    readonly property int space32: 32

    // ── Radii ────────────────────────────────────────────────
    readonly property int radiusSmall: 4
    readonly property int radiusMedium: 8
    readonly property int radiusLarge: 12
    readonly property int radiusXLarge: 16

    // ── Typography ───────────────────────────────────────────
    readonly property int fontSizeCaption: 11
    readonly property int fontSizeBody: 13
    readonly property int fontSizeBodyLarge: 14
    readonly property int fontSizeTitle: 18
    readonly property int fontSizeHeading: 24

    readonly property string fontFamily: ""

    readonly property int fontWeightNormal: Font.Normal
    readonly property int fontWeightMedium: Font.Medium
    readonly property int fontWeightBold: Font.Bold

    // ── Control sizes ────────────────────────────────────────
    readonly property int controlHeightSmall: 28
    readonly property int controlHeightMedium: 36
    readonly property int controlHeightLarge: 44

    // ── Icon sizes ───────────────────────────────────────────
    readonly property int iconSmall: 14
    readonly property int iconMedium: 20
    readonly property int iconLarge: 28

    // ── Motion ───────────────────────────────────────────────
    readonly property int durationFast: 120
    readonly property int durationNormal: 200
}
