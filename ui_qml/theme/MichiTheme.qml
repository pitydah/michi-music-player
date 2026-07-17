pragma Singleton
import QtQuick

QtObject {
    readonly property QtObject colors: MichiColors
    readonly property QtObject typography: MichiTypography
    readonly property QtObject spacing: MichiSpacing
    readonly property QtObject motion: MichiMotion

    readonly property QtObject radius: QtObject {
        readonly property int xs: 2
        readonly property int sm: 4
        readonly property int md: 8
        readonly property int lg: 12
        readonly property int xl: 16
        readonly property int pill: 999
    }

    readonly property QtObject opacity: QtObject {
        readonly property real enabled: 1.0
        readonly property real disabled: 0.4
        readonly property real hover: 0.85
        readonly property real pressed: 0.7
        readonly property real muted: 0.6
    }

    readonly property QtObject breakpoints: QtObject {
        readonly property int compact: 800
        readonly property int medium: 1200
        readonly property int wide: 1600
    }

    readonly property QtObject density: QtObject {
        readonly property int compact: 32
        readonly property int regular: 44
        readonly property int comfortable: 56
    }

    readonly property real borderWidth: 1
    readonly property real borderWidthFocus: 2

    readonly property int pageMarginCompact: spacing.lg
    readonly property int pageMarginRegular: spacing.xl
    readonly property int pageMarginWide: spacing.page
    readonly property int toolbarHeight: 48
    readonly property int rowHeightCompact: 36
    readonly property int rowHeightComfortable: 44
    readonly property int minimumInteractiveSize: 44

    readonly property int coverSizeSmall: 48
    readonly property int coverSizeMedium: 128
    readonly property int coverSizeLarge: 224
    readonly property int coverRadius: radius.sm

    readonly property real focusWidth: borderWidthFocus
    readonly property real focusOffset: 2
    readonly property real disabledOpacity: opacity.disabled

    readonly property int sidebarWidth: 250
    readonly property int sidebarWidthCompact: 68
    readonly property int nowPlayingHeight: 100
    readonly property int headerHeight: 56
}
