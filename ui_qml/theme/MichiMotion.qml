pragma Singleton
import QtQuick

QtObject {
    readonly property int durationInstant: 80
    readonly property int durationFast: 120
    readonly property int durationNormal: 200
    readonly property int durationSlow: 300
    readonly property int fast: 120
    readonly property int normal: 160
    readonly property int slow: 220
    readonly property int reduced: 40

    readonly property QtObject easing: QtObject {
        readonly property int standard: Easing.OutCubic
        readonly property int emphasis: Easing.OutBack
        readonly property int entrance: Easing.OutCubic
        readonly property int exit: Easing.InCubic
        readonly property int inOut: Easing.InOutCubic
        readonly property int out: Easing.OutCubic
        readonly property int _in: Easing.InCubic
    }
}
