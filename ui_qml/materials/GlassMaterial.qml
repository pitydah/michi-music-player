import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Glass Material"
    objectName: "glassMaterial"
    id: root

    default property alias content: contentLayer.data

    property string variant: "base"
    property bool hovered: false
    property bool interactive: false
    property bool pressed: false
    property int radius: MichiTheme.radius.md
    property alias backgroundColor: bgRect.color
    property alias borderColor: bgRect.border.color
    property alias borderWidth: bgRect.border.width

    implicitWidth: MichiTheme.minimumInteractiveSize
    implicitHeight: MichiTheme.minimumInteractiveSize

    Item {
        id: backgroundLayer
        objectName: "glassBackgroundLayer"
        anchors.fill: parent
        z: 0
        enabled: false

        Rectangle {
            id: bgRect
            anchors.fill: parent
            radius: root.radius
            color: {
                if (root.pressed && root.interactive) return MichiTheme.colors.surfacePressed
                switch (root.variant) {
                    case "compact": return MichiTheme.colors.surfaceToolbar
                    case "elevated": return MichiTheme.colors.surfaceCardElevated
                    case "accent": return MichiTheme.colors.accentSurface
                    case "floating": return MichiTheme.colors.surfaceGlassStrong
                    case "status": return MichiTheme.colors.surfaceCard
                    case "hero": return MichiTheme.colors.surfaceHero
                    case "danger": return MichiTheme.colors.badgeDangerBg
                    default: return MichiTheme.colors.surfaceGlass
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
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: Math.max(1, parent.height * 0.44)
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: MichiTheme.colors.surfaceSheen }
                    GradientStop { position: 1.0; color: Qt.rgba(1.0, 1.0, 1.0, 0.0) }
                }
            }

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: Qt.rgba(1.0, 1.0, 1.0, 0.0)
                border.color: MichiTheme.colors.borderInner
                border.width: MichiTheme.borderWidth
            }
        }
    }

    Item {
        id: contentLayer
        objectName: "glassContentLayer"
        anchors.fill: parent
        z: 1
    }
}
