pragma Singleton
import QtQuick

QtObject {
    property bool reduceMotion: typeof themeBridge !== "undefined" && themeBridge ? themeBridge.reducedMotion : false
    property bool highContrast: typeof themeBridge !== "undefined" && themeBridge ? themeBridge.highContrast : false
    readonly property real fontScaleFactor: MichiAccessibility.fontScale
    readonly property int motionDurationFast: MichiMotion.durationFast
    readonly property int motionDurationNormal: MichiMotion.durationNormal
    readonly property int motionDurationSlow: MichiMotion.durationSlow
    readonly property color textPrimary: MichiColors.textPrimary
    readonly property color textMuted: MichiColors.textMuted
    readonly property int minimumInteractiveSize: MichiTheme.minimumInteractiveSize
    property bool darkMode: typeof themeBridge !== "undefined" && themeBridge ? themeBridge.darkMode : false
    readonly property color accentPrimary: MichiColors.accentPrimary
    readonly property color surfaceCard: MichiColors.surfaceCard
}
