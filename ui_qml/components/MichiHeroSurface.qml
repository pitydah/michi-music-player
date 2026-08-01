import QtQuick
import "../theme"

/* MichiHeroSurface — hero surface with artwork glow support. */
Item {
    id: root

    property color accent: MichiTheme.colors.accentWarmViolet
    property bool showGlow: true
    property int radius: MichiTheme.radius.lg

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: MichiTheme.colors.surfaceHero

        // Top inner highlight
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: parent.height * 0.4
            radius: root.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.05) }
                GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0) }
            }
        }

        // Accent glow
        Rectangle {
            anchors.fill: parent
            radius: root.radius
            visible: root.showGlow
            gradient: Gradient {
                GradientStop { position: 0.0; color: root.accent }
                GradientStop { position: 0.6; color: Qt.rgba(0, 0, 0, 0) }
            }
            opacity: 0.12
        }

        // Border
        Rectangle {
            anchors.fill: parent
            radius: root.radius
            border.color: MichiTheme.colors.borderSubtle
            border.width: 1
            color: "transparent"
        }
    }
}
