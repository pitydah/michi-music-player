pragma Singleton
import QtQuick

QtObject {
    readonly property QtObject colors: MichiColors
    readonly property QtObject typography: MichiTypography
    readonly property QtObject spacing: MichiSpacing
    readonly property QtObject motion: MichiMotion

    // ── Radius ──
    readonly property QtObject radius: QtObject {
        readonly property int xs: 4
        readonly property int sm: 8
        readonly property int md: 12
        readonly property int lg: 16
        readonly property int xl: 20
        readonly property int pill: 999
    }

    // ── Elevation ──
    readonly property QtObject elevation: QtObject {
        readonly property int level0: 0
        readonly property int level1: 1
        readonly property int level2: 2
        readonly property int level3: 3
        readonly property int level4: 4
        readonly property int level5: 5
    }

    // ── Opacity ──
    readonly property QtObject opacity: QtObject {
        readonly property real enabled: 1.0
        readonly property real disabled: 0.4
        readonly property real hover: 0.85
        readonly property real pressed: 0.7
        readonly property real muted: 0.6
    }

    // ── Breakpoints ──
    readonly property QtObject breakpoints: QtObject {
        readonly property int compact: 800
        readonly property int medium: 1200
        readonly property int wide: 1600
    }

    // ── Density ──
    readonly property QtObject density: QtObject {
        readonly property int compact: 32
        readonly property int regular: 44
        readonly property int comfortable: 56
    }

    // ── Layout ──
    readonly property real borderWidth: 1
    readonly property real borderWidthFocus: 2
    readonly property int pageMarginCompact: spacing.lg
    readonly property int pageMarginRegular: spacing.xl
    readonly property int pageMarginWide: spacing.page
    readonly property int toolbarHeight: 48
    readonly property int rowHeightCompact: 36
    readonly property int rowHeightComfortable: 44
    readonly property int minimumInteractiveSize: 44

    // ── Covers ──
    readonly property int coverSizeSmall: 48
    readonly property int coverSizeMedium: 128
    readonly property int coverSizeLarge: 224
    readonly property int coverRadius: radius.sm

    // ── Shell ──
    readonly property int sidebarWidth: 244
    readonly property int sidebarWidthCompact: 70
    readonly property int nowPlayingHeight: 112
    readonly property int headerHeight: 56

    // ── Shortcuts ──
    readonly property real focusWidth: borderWidthFocus
    readonly property real disabledOpacity: opacity.disabled
    readonly property int motionFast: motion.durationFast
    readonly property int motionNormal: motion.durationNormal
    readonly property int motionSlow: motion.durationSlow
    readonly property int radiusXs: radius.xs
    readonly property int radiusSm: radius.sm
    readonly property int radiusMd: radius.md
    readonly property int radiusLg: radius.lg
    readonly property int radiusXl: radius.xl
    readonly property int radiusPill: radius.pill
    readonly property real focusOffset: 2

    // ── Theme toggle ──
    property bool darkMode: true

    function setDarkMode(enabled: bool) {
        darkMode = enabled
        MichiColors.lightMode = !enabled
    }
}
