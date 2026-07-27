pragma Singleton
import QtQuick

QtObject {
    readonly property bool reduceMotion: MichiAccessibility.reduceMotion
    property bool highContrast: typeof themeBridge !== "undefined" && themeBridge ? themeBridge.highContrast : false
    readonly property real fontScaleFactor: MichiAccessibility.fontScale
    readonly property int motionDurationFast: MichiMotion.durationFast
    readonly property int motionDurationNormal: MichiMotion.durationNormal
    readonly property int motionDurationSlow: MichiMotion.durationSlow
    readonly property color textPrimary: MichiColors.textPrimary
    readonly property color textMuted: MichiColors.textMuted
    readonly property int minimumInteractiveSize: MichiTheme.minimumInteractiveSize
    readonly property bool darkMode: MichiTheme.darkMode
    readonly property color accentPrimary: MichiColors.accentPrimary
    readonly property color surfaceCard: MichiColors.surfaceCard

    function updateFromBridge(bridge) {
        if (bridge) {
            darkMode = bridge.darkMode
            reduceMotion = bridge.reducedMotion
        }
    }
}
