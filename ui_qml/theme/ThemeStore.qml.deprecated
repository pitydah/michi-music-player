pragma Singleton
import QtQuick

QtObject {
    id: themeStore

    property bool ready: false
    property string currentTheme: "dark"
    property string accentColor: "#8FB7FF"
    property bool highContrast: false
    property bool compactMode: false
    property string fontScale: "normal"

    property bool darkMode: true

    readonly property color bgApp: darkMode ? (highContrast ? "#000205" : "#070A10") : (highContrast ? "#FFFFFF" : "#F5F6FA")
    readonly property color bgContent: darkMode ? (highContrast ? "#000408" : "#090B11") : (highContrast ? "#FAFAFE" : "#EEF0F5")
    readonly property color accent: accentColor
    readonly property color accentSurface: Qt.rgba(
        (parseInt(accentColor.substring(1,3), 16) / 255),
        (parseInt(accentColor.substring(3,5), 16) / 255),
        (parseInt(accentColor.substring(5,7), 16) / 255),
        0.10
    )
    readonly property color accentSelection: Qt.rgba(
        (parseInt(accentColor.substring(1,3), 16) / 255),
        (parseInt(accentColor.substring(3,5), 16) / 255),
        (parseInt(accentColor.substring(5,7), 16) / 255),
        0.18
    )
    readonly property color surfaceCard: darkMode ? (highContrast ? "#050810" : "#0D0F16") : (highContrast ? "#FFFFFF" : "#F0F2F7")
    readonly property color surfaceCardHover: darkMode ? (highContrast ? "#080C15" : "#11131C") : (highContrast ? "#F5F6FA" : "#E8EAF0")
    readonly property color surfaceHover: darkMode ? Qt.rgba(1,1,1, highContrast ? 0.12 : 0.08) : Qt.rgba(0,0,0, highContrast ? 0.08 : 0.05)
    readonly property color surfacePressed: darkMode ? Qt.rgba(1,1,1, highContrast ? 0.18 : 0.12) : Qt.rgba(0,0,0, highContrast ? 0.12 : 0.08)
    readonly property color surfaceDisabled: darkMode ? Qt.rgba(1,1,1, highContrast ? 0.06 : 0.04) : Qt.rgba(0,0,0, highContrast ? 0.04 : 0.03)
    readonly property color textPrimary: darkMode ? (highContrast ? "#FFFFFF" : "#F0F2F8") : (highContrast ? "#000000" : "#1A1D26")
    readonly property color textNormal: darkMode ? (highContrast ? "#E0E4F0" : "#D0D4E0") : (highContrast ? "#2A2D36" : "#3A3D46")
    readonly property color textSecondary: darkMode ? (highContrast ? "#B0B8C8" : "#9098A8") : (highContrast ? "#505860" : "#707880")
    readonly property color textMuted: darkMode ? (highContrast ? "#808898" : "#606878") : (highContrast ? "#808890" : "#9098A0")
    readonly property color textOnAccent: darkMode ? "#070A10" : "#FFFFFF"
    readonly property color borderSubtle: darkMode ? Qt.rgba(1,1,1, highContrast ? 0.08 : 0.05) : Qt.rgba(0,0,0, highContrast ? 0.10 : 0.06)
    readonly property color borderCard: darkMode ? Qt.rgba(1,1,1, highContrast ? 0.10 : 0.07) : Qt.rgba(0,0,0, highContrast ? 0.12 : 0.08)
    readonly property color borderActive: accentColor
    readonly property color borderFocus: accentColor
    readonly property color success: "#4ADE80"
    readonly property color warning: "#FBBF24"
    readonly property color error: "#F87171"
    readonly property color focusHalo: Qt.rgba(
        (parseInt(accentColor.substring(1,3), 16) / 255),
        (parseInt(accentColor.substring(3,5), 16) / 255),
        (parseInt(accentColor.substring(5,7), 16) / 255),
        highContrast ? 0.30 : 0.18
    )
    readonly property color controlTrack: darkMode ? Qt.rgba(1,1,1, highContrast ? 0.12 : 0.08) : Qt.rgba(0,0,0, highContrast ? 0.10 : 0.06)
    readonly property color controlThumb: darkMode ? Qt.rgba(1,1,1, highContrast ? 1.0 : 0.90) : Qt.rgba(0,0,0, highContrast ? 0.90 : 0.80)

    readonly property real fontScaleFactor: {
        switch (fontScale) {
            case "small": return 0.875
            case "large": return 1.125
            case "xlarge": return 1.25
            default: return 1.0
        }
    }

    readonly property real motionDurationFast: reduceMotion ? 0 : 80
    readonly property real motionDurationNormal: reduceMotion ? 0 : 150
    readonly property real motionDurationSlow: reduceMotion ? 0 : 250

    readonly property int minimumInteractiveSize: compactMode ? 32 : 40
    readonly property int spacingXs: compactMode ? 2 : 4
    readonly property int spacingSm: compactMode ? 4 : 8
    readonly property int spacingMd: compactMode ? 8 : 12
    readonly property int spacingLg: compactMode ? 12 : 16
    readonly property int spacingXl: compactMode ? 16 : 24

    function updateFromBridge(bridge) {
        if (!bridge) return
        currentTheme = bridge.theme || "dark"
        accentColor = bridge.accentColor || "#8FB7FF"
        highContrast = bridge.highContrast || false
        compactMode = bridge.compactMode || false
        fontScale = bridge.fontScale || "normal"
        reduceMotion = bridge.reduceMotion || false
        darkMode = currentTheme !== "light"
        ready = true
    }

    function toggleTheme() {
        darkMode = !darkMode
    }

    function apply() {
        var changed = Qt.createQmlObject("import QtQuick; QtObject {}", themeStore)
        changed.destroy()
    }
}
