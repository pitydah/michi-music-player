import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"

Item {
    id: root
    width: parent.width; height: 32

    property string path: ""
    property var _parts: path ? path.split("/").filter(function(p) { return p !== "" }) : []

    signal navigate(int index)

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surfaceCard

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.xs

            Text {
                text: "BL"
                color: MichiTheme.colors.accentBlue
                font.pixelSize: 12
                font.weight: MichiTheme.typography.weightBold
            }

            Repeater {
                model: root._parts

                RowLayout {
                    spacing: MichiTheme.spacing.xs

                    Text {
                        text: "/"
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.bodySize
                    }

                    Text {
                        text: modelData
                        color: mouse.containsMouse ? MichiTheme.colors.accentBlue : MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.bodySize

                        MouseArea {
                            id: mouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.navigate(index)
                        }
                    }
                }
            }
        }
    }
}
