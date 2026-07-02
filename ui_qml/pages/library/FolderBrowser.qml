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
        anchors.margins: MichiSpacing.md
        contentHeight: column.height + MichiSpacing.md
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: parent.width
            spacing: MichiSpacing.xs

            Repeater {
                model: root.folders

                GlassMaterial {
                    width: parent.width
                    height: 48
                    radius: 8
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
                        anchors.leftMargin: MichiSpacing.md
                        anchors.rightMargin: MichiSpacing.md
                        spacing: MichiSpacing.sm

                        Rectangle {
                            width: 24; height: 24; radius: 4
                            color: Qt.rgba(1.0, 1.0, 1.0, 0.04)
                            anchors.verticalCenter: parent.verticalCenter
                            Text {
                                anchors.centerIn: parent
                                text: "FD"
                                color: MichiColors.textMuted
                                font.pixelSize: 10
                                font.weight: MichiTypography.weightBold
                            }
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 2

                            Text {
                                text: modelData.name || modelData.path || ""
                                color: MichiColors.textPrimary
                                font.pixelSize: MichiTypography.bodySize
                                elide: Text.ElideRight
                                width: parent.width - 60
                            }

                            Text {
                                text: modelData.track_count > 0 ? modelData.track_count + " canciones" : ""
                                color: MichiColors.textMuted
                                font.pixelSize: MichiTypography.metaSize
                                visible: text !== ""
                            }
                        }
                    }
                }
            }

            Text {
                text: root.folders.length === 0 ? "No hay carpetas disponibles" : ""
                color: MichiColors.textMuted
                font.pixelSize: MichiTypography.bodySize
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                visible: text !== ""
            }
        }
    }
}
