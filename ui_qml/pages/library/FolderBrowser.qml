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
                            color: MichiTheme.colors.borderInner
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

            Item { width: parent.width; height: 180; visible: root.folders.length === 0
                Column { anchors.centerIn: parent; spacing: MichiTheme.spacing.lg
                    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; width: 48; height: 48; radius: 12; color: MichiTheme.colors.accentSurface
                        Text { anchors.centerIn: parent; text: "FD"; color: MichiTheme.colors.accentBlue; font.pixelSize: 18; font.weight: MichiTheme.typography.weightBold; opacity: 0.7 } }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "No hay carpetas"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.sectionTitleSize; font.weight: MichiTheme.typography.weightMedium }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Configura carpetas de música desde Ajustes."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.bodySize; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
                    Row { anchors.horizontalCenter: parent.horizontalCenter; spacing: MichiTheme.spacing.sm
                        MichiButton { text: "Ajustes"; variant: "primary"; onClicked: { if (typeof navigationBridge !== "undefined" && navigationBridge) navigationBridge.navigate("settings") } }
                    }
                }
            }
        }
    }
}
