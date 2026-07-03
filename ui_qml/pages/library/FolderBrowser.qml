import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var folders: []
    property var bridge: null

    signal folderSelected(string path)

    Flickable {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.md
        contentHeight: column.height + MichiTheme.spacing.md
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiTheme.spacing.xs

            Repeater {
                model: root.folders

                GlassMaterial {
                    width: parent.width
                    height: 48
                    radius: MichiTheme.radiusSm
                    hovered: mouseArea.containsMouse
                    interactive: true

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.folderSelected(modelData.path || "")
                    }

                    Row {
                        anchors.fill: parent
                        anchors.leftMargin: MichiTheme.spacing.md
                        anchors.rightMargin: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        Rectangle {
                            width: 24; height: 24; radius: MichiTheme.radiusXs
                            color: Qt.rgba(1.0, 1.0, 1.0, 0.04)
                            anchors.verticalCenter: parent.verticalCenter
                            Text {
                                anchors.centerIn: parent
                                text: "FD"
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: 10
                                font.weight: MichiTheme.typography.weightBold
                            }
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2

                            Text {
                                text: modelData.name || modelData.path || ""
                                color: MichiTheme.colors.textPrimary
                                font.pixelSize: MichiTheme.typography.bodySize
                                elide: Text.ElideRight
                                width: parent.width - 60
                            }

                            Text {
                                text: modelData.track_count > 0 ? modelData.track_count + " canciones" : ""
                                color: MichiTheme.colors.textMuted
                                font.pixelSize: MichiTheme.typography.metaSize
                                visible: text !== ""
                            }
                        }
                    }
                }
            }

            Text {
                text: root.folders.length === 0 ? "No hay carpetas disponibles" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                visible: text !== ""
            }
        }
    }
}
