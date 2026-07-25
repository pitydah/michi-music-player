import QtQuick
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Sidebar Material"
    objectName: "sidebarMaterial"
    focus: true
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
                opacity: MichiTheme.darkMode ? 0.34 : 0.22
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop {
                        position: 0.0
                        color: MichiTheme.darkMode
                               ? Qt.rgba(0.055, 0.082, 0.135, 0.82)
                               : Qt.rgba(0.82, 0.89, 0.98, 0.72)
                    }
                    GradientStop { position: 0.68; color: "transparent" }
                    GradientStop {
                        position: 1.0
                        color: MichiTheme.darkMode
                               ? Qt.rgba(0.02, 0.025, 0.045, 0.44)
                               : Qt.rgba(1.0, 1.0, 1.0, 0.30)
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.width
                height: Math.min(parent.height * 0.34, 320)
                opacity: MichiTheme.darkMode ? 0.22 : 0.12
                gradient: Gradient {
                    GradientStop {
                        position: 0.0
                        color: Qt.rgba(0.561, 0.718, 1.0, 0.28)
                    }
                    GradientStop { position: 1.0; color: "transparent" }
                }
            }

            Rectangle {
                anchors.right: parent.right
                width: MichiTheme.borderWidth
                height: parent.height
                color: Qt.rgba(0.561, 0.718, 1.0,
                               MichiTheme.darkMode ? 0.13 : 0.20)
            }

            Rectangle {
                anchors.right: parent.right
                width: 8
                height: parent.height
                opacity: MichiTheme.darkMode ? 0.26 : 0.12
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "transparent" }
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
