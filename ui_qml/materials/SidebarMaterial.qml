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
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.width
                height: Math.min(parent.height * 0.28, 240)
                gradient: Gradient {
                    GradientStop { position: 0.0; color: MichiTheme.colors.accentGlowSubtle }
                    GradientStop { position: 1.0; color: Qt.alpha(MichiTheme.colors.accentPrimary, 0.0) }
                }
            }

            Rectangle {
                anchors.right: parent.right
                width: MichiTheme.borderWidth
                height: parent.height
                color: MichiTheme.colors.accentSeparator
            }

            Rectangle {
                anchors.right: parent.right
                width: 6
                height: parent.height
                opacity: MichiTheme.darkMode ? 0.20 : 0.08
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 1.0; color: MichiTheme.colors.shadowSoft }
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
