pragma Singleton
import QtQuick

QtObject {
    readonly property QtObject colors: MichiColors
    readonly property QtObject typography: MichiTypography
    readonly property QtObject spacing: MichiSpacing
    readonly property QtObject motion: MichiMotion

    readonly property int radiusXs: 6
    readonly property int radiusSm: 8
    readonly property int radiusMd: 12
    readonly property int radiusLg: 16
    readonly property int radiusXl: 22
    readonly property int radiusPill: 999

    readonly property real borderWidth: 1
    readonly property real borderWidthFocus: 2

    readonly property real opacityDisabled: 0.38
    readonly property real opacityHover: 0.82
    readonly property real opacityActive: 0.92
    readonly property real opacityGlass: 0.82
    readonly property real opacityOverlay: 0.72

    readonly property int breakpointCompact: 800
    readonly property int breakpointRegular: 1280
    readonly property int breakpointWide: 1920

    readonly property int pageMarginCompact: spacing.lg
    readonly property int pageMarginRegular: spacing.xl
    readonly property int pageMarginWide: spacing.page
    readonly property int toolbarHeight: 48
    readonly property int rowHeightCompact: 36
    readonly property int rowHeightComfortable: 44
    readonly property int minimumInteractiveSize: 40

    readonly property int coverSizeSmall: 48
    readonly property int coverSizeMedium: 128
    readonly property int coverSizeLarge: 224
    readonly property int coverRadius: radiusSm

    readonly property real focusWidth: borderWidthFocus
    readonly property real focusOffset: 2
    readonly property real disabledOpacity: opacityDisabled
    readonly property real hoverOpacity: opacityHover
    readonly property real pressedOpacity: opacityActive
    readonly property int motionFast: motion.fast
    readonly property int motionNormal: motion.normal
    readonly property int motionSlow: motion.slow

    readonly property int sidebarWidth: 250
    readonly property int sidebarWidthCompact: 68
    readonly property int nowPlayingHeight: 100
    readonly property int headerHeight: 56
}
