import QtQuick
import "../theme"

Item {
    id: root

    property int radius: 16
    property bool showGlow: false

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: MichiColors.surfaceHero

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(0.561, 0.718, 1.0, 0.05) }
                GradientStop { position: 0.5; color: "transparent" }
                GradientStop { position: 1.0; color: Qt.rgba(0.0, 0.0, 0.0, 0.25) }
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            visible: root.showGlow
            gradient: Gradient {
                GradientStop { position: 0.0; color: MichiColors.surfaceHeroGlow }
                GradientStop { position: 0.6; color: "transparent" }
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            border.color: Qt.rgba(1.0, 1.0, 1.0, 0.04)
            border.width: 1
            color: "transparent"
        }
    }
}
