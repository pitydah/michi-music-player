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
    property int radius: MichiTheme.radius.md
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
                if (root.pressed && root.interactive) return MichiTheme.colors.surfacePressed
                switch (root.variant) {
                    case "compact": return MichiTheme.colors.surfaceOverlay
                    case "elevated": return MichiTheme.colors.surfaceCardElevated
                    case "accent": return MichiTheme.colors.accentSurface
                    case "floating": return MichiTheme.colors.surfaceElevated
                    case "status": return MichiTheme.colors.surfaceCard
                    case "hero": return MichiTheme.colors.surfaceHero
                    case "danger": return MichiTheme.colors.badgeDangerBg
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
                    case "danger": return MichiTheme.colors.borderError
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
                    GradientStop { position: 0.0; color: MichiTheme.colors.surfaceSubtle }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: "transparent"
                border.color: MichiTheme.colors.borderInner
                border.width: MichiTheme.borderWidth
            }
        }
    }
}
