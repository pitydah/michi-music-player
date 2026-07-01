import QtQuick
import QtQuick.Controls
import "../theme"
import "../materials"

Rectangle {
    id: root

    property string text: ""
    property string variant: "primary"
    property bool pressed: false
    property bool hoveredBtn: false
    property bool focused: false
    property bool loading: false
    property int minWidth: 80

    signal clicked()

    implicitWidth: Math.max(minWidth, text !== "" ? contentText.implicitWidth + MichiSpacing.xl * 2 + (loading ? 24 : 0) : 40)
    height: 36
    radius: 10

    color: {
        if (!enabled) return Qt.rgba(0.3, 0.3, 0.35, 0.15)
        if (root.pressed) {
            switch (root.variant) {
                case "primary": return Qt.rgba(0.5, 0.65, 1.0, 1.0)
                case "secondary": return Qt.rgba(1.0, 1.0, 1.0, 0.15)
                case "accent": return Qt.rgba(0.561, 0.718, 1.0, 0.18)
                case "danger": return Qt.rgba(0.95, 0.25, 0.25, 0.20)
                default: return Qt.rgba(1.0, 1.0, 1.0, 0.06)
            }
        }
        if (root.hoveredBtn) {
            switch (root.variant) {
                case "primary": return Qt.rgba(0.65, 0.78, 1.0, 1.0)
                case "secondary": return Qt.rgba(1.0, 1.0, 1.0, 0.10)
                case "accent": return Qt.rgba(0.561, 0.718, 1.0, 0.12)
                case "danger": return Qt.rgba(0.95, 0.25, 0.25, 0.12)
                default: return Qt.rgba(1.0, 1.0, 1.0, 0.04)
            }
        }
        switch (root.variant) {
            case "primary": return MichiColors.accentBlue
            case "secondary": return Qt.rgba(1.0, 1.0, 1.0, 0.06)
            case "ghost": return "transparent"
            case "accent": return Qt.rgba(0.561, 0.718, 1.0, 0.08)
            case "danger": return Qt.rgba(0.95, 0.25, 0.25, 0.08)
            default: return MichiColors.accentBlue
        }
    }

    Behavior on color {
        ColorAnimation { duration: MichiMotion.fast; easing.type: MichiMotion.easing.standard }
    }

    border.color: {
        if (!enabled) return "transparent"
        if (root.focused) return MichiColors.borderFocus
        if (root.variant === "ghost") {
            return root.hoveredBtn ? Qt.rgba(1.0, 1.0, 1.0, 0.12) : "transparent"
        }
        return "transparent"
    }
    border.width: root.focused ? 2 : 1

    scale: root.pressed ? 0.985 : 1.0
    Behavior on scale {
        NumberAnimation { duration: 80; easing.type: Easing.OutCubic }
    }

    Text {
        id: contentText
        anchors.centerIn: parent
        text: root.text
        color: {
            if (!enabled) return MichiColors.textMuted
            if (root.variant === "primary") return MichiColors.textOnAccent
            return MichiColors.textPrimary
        }
        font.pixelSize: MichiTypography.bodySize
        font.weight: MichiTypography.weightMedium
        visible: text !== "" && !root.loading
    }

    Rectangle {
        anchors.centerIn: parent
        width: 16
        height: 16
        radius: 8
        color: "transparent"
        border.color: root.variant === "primary" ? MichiColors.textOnAccent : MichiColors.textSecondary
        border.width: 2
        visible: root.loading
        NumberAnimation on rotation {
            from: 0; to: 360
            duration: 600
            loops: Animation.Infinite
            running: root.loading
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: root.hoveredBtn = true
        onExited: root.hoveredBtn = false
        onPressed: root.pressed = true
        onReleased: root.pressed = false
        onClicked: root.clicked()
    }
}
