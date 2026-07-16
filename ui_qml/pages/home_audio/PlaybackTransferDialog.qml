import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Playback Transfer"
    objectName: "playbackTransferDialog"
    focus: true
    id: root

    property var targetZones: []
    property string currentSource: ""

    signal transferRequested(string targetZoneId)
    signal cancelRequested()

    implicitHeight: 300

    GlassMaterial {
        anchors.fill: parent
        radius: MichiTheme.radiusMd
        variant: "elevated"

        Column {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.lg
            spacing: MichiTheme.spacing.md

            Text {
                text: "Transferir reproducción"
                color: MichiTheme.colors.textPrimary
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
            }

            Text {
                text: "Selecciona la zona destino para transferir la reproducción actual:"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Repeater {
                model: root.targetZones

                Rectangle {
                    width: parent.width
                    height: 48
                    radius: MichiTheme.radiusSm
                    color: mouseArea.containsMouse ? MichiTheme.colors.accentSurface : "transparent"
                    border.color: MichiTheme.colors.border
                    border.width: 1

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.transferRequested(modelData.id || "")
                    }

                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left; anchors.leftMargin: MichiTheme.spacing.md
                        spacing: MichiTheme.spacing.sm

                        Text {
                            text: modelData.name || "Zona"
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                        }

                        Text {
                            text: modelData.deviceCount > 0 ? "(" + modelData.deviceCount + " disp.)" : ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                        }
                    }
                }
            }

            MichiButton {
                text: "Cancelar"
                variant: "ghost"
                onClicked: root.cancelRequested()
            }
        }
    }
}
