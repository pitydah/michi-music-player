import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Hero Material"
    objectName: "heroMaterial"
    id: root

    default property alias content: contentLayer.data

    property int radius: MichiTheme.radius.lg
    property bool showGlow: false

    Item {
        id: backgroundLayer
        objectName: "heroBackgroundLayer"
        anchors.fill: parent
        z: 0
        enabled: false

        Rectangle {
            anchors.fill: parent
            radius: root.radius
            color: MichiTheme.colors.surfaceHero

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: MichiTheme.colors.accentSurface }
                    GradientStop { position: 0.5; color: Qt.rgba(0.561, 0.718, 1.0, 0.0) }
                    GradientStop { position: 1.0; color: MichiTheme.colors.shadowSoft }
                }
            }

            TextureOverlay {
                anchors.fill: parent
                variant: "contours"
                strength: root.showGlow ? 0.90 : 0.62
            }

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                visible: root.showGlow
                gradient: Gradient {
                    GradientStop { position: 0.0; color: MichiTheme.colors.surfaceHeroGlow }
                    GradientStop { position: 0.6; color: Qt.rgba(0.561, 0.718, 1.0, 0.0) }
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

    Item {
        id: contentLayer
        objectName: "heroContentLayer"
        anchors.fill: parent
        z: 1
    }
}
