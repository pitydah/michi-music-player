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

    readonly property int sidebarWidth: 250
    readonly property int sidebarWidthCompact: 68
    readonly property int nowPlayingHeight: 88
    readonly property int headerHeight: 56
}
