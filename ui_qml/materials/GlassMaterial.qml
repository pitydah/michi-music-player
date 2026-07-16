import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Glass Material"
    objectName: "glassMaterial"
    focus: true
    id: root

    property string variant: "base"
    property bool hovered: false
    property bool interactive: false
    property bool pressed: false
    property int radius: MichiTheme.radiusMd
    property alias backgroundColor: bgRect.color
    property alias borderColor: bgRect.border.color
    property alias borderWidth: bgRect.border.width

    Item {
        anchors.fill: parent

        Rectangle {
            id: bgRect
            anchors.fill: parent
            radius: root.radius
            color: {
                if (root.pressed && root.interactive) return Qt.rgba(1.0, 1.0, 1.0, 0.03)
                switch (root.variant) {
                    case "compact": return Qt.rgba(0.05, 0.06, 0.09, 0.85)
                    case "elevated": return MichiTheme.colors.surfaceCardElevated
                    case "accent": return MichiTheme.colors.accentSurface
                    case "floating": return Qt.rgba(0.05, 0.06, 0.09, 0.92)
                    case "status": return Qt.rgba(0.05, 0.06, 0.09, 0.75)
                    case "hero": return MichiTheme.colors.surfaceHero
                    case "danger": return Qt.rgba(0.95, 0.25, 0.25, 0.08)
                    default: return MichiTheme.colors.surfaceCard
                }
            }

            Behavior on color {
                ColorAnimation { duration: MichiTheme.motion.fast; easing.type: MichiTheme.motion.easing.standard }
            }

            border.color: {
                if (root.hovered && root.interactive) return MichiTheme.colors.borderFocus
                switch (root.variant) {
                    case "accent": return MichiTheme.colors.borderActive
                    case "danger": return Qt.rgba(0.95, 0.25, 0.25, 0.20)
                    case "floating": return MichiTheme.colors.borderCard
                    case "hero": return MichiTheme.colors.borderSubtle
                    default: return MichiTheme.colors.borderCard
                }
            }

            Behavior on border.color {
                ColorAnimation { duration: MichiTheme.motion.fast; easing.type: MichiTheme.motion.easing.standard }
            }

            border.width: MichiTheme.borderWidth

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: Qt.rgba(1.0, 1.0, 1.0, 0.025) }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: "transparent"
                border.color: Qt.rgba(1.0, 1.0, 1.0, 0.02)
                border.width: MichiTheme.borderWidth
            }
        }
    }
}
