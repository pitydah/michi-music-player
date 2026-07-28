import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Sidebar Material"
    objectName: "sidebarMaterial"
    id: root

    default property alias content: contentLayer.data

    property int radius: 0

    Item {
        id: backgroundLayer
        anchors.fill: parent
        z: 0
        enabled: false

        Rectangle {
            anchors.fill: parent
            color: MichiTheme.colors.surfaceSidebar

            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: MichiTheme.colors.accentGlow }
                    GradientStop { position: 0.68; color: Qt.rgba(0.561, 0.718, 1.0, 0.0) }
                    GradientStop { position: 1.0; color: MichiTheme.colors.surfaceSheen }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.width
                height: Math.min(parent.height * 0.34, 320)
                gradient: Gradient {
                    GradientStop { position: 0.0; color: MichiTheme.colors.accentGlowSubtle }
                    GradientStop { position: 1.0; color: Qt.rgba(0.561, 0.718, 1.0, 0.0) }
                }
            }

            TextureOverlay {
                anchors.fill: parent
                variant: "grain"
                strength: 0.40
            }

            Rectangle {
                anchors.right: parent.right
                width: MichiTheme.borderWidth
                height: parent.height
                color: MichiTheme.colors.accentSeparator
            }

            Rectangle {
                anchors.right: parent.right
                width: 8
                height: parent.height
                opacity: MichiTheme.darkMode ? 0.26 : 0.12
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: Qt.rgba(0.0, 0.0, 0.0, 0.0) }
                    GradientStop {
                        position: 1.0
                        color: MichiTheme.colors.shadowSoft
                    }
                }
            }
        }
    }

    Item {
        id: contentLayer
        anchors.fill: parent
        z: 1
    }
}
