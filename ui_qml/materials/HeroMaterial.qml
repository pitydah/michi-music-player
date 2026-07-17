import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Hero Material"
    objectName: "heroMaterial"
    focus: true
    id: root

    property int radius: MichiTheme.radius.lg
    property bool showGlow: false

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: MichiTheme.colors.surfaceHero

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: MichiTheme.colors.accentSurface }
                GradientStop { position: 0.5; color: "transparent" }
                GradientStop { position: 1.0; color: MichiTheme.colors.shadowSoft }
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            visible: root.showGlow
            gradient: Gradient {
                GradientStop { position: 0.0; color: MichiTheme.colors.surfaceHeroGlow }
                GradientStop { position: 0.6; color: "transparent" }
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            border.color: MichiTheme.colors.borderSubtle
            border.width: MichiTheme.borderWidth
            color: "transparent"
        }
    }
}
