import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Stream Routing"
    objectName: "streamRoutingPage"
    id: root
    focus: true

    property var zones: []
    property var streams: []
    property string activeStreamId: ""
    property string activeStreamName: ""

    signal streamAssigned(string zoneId, string streamId)
    signal backClicked()



    AsyncStateView {
        id: asyncView
        anchors.fill: parent
        state: root.zones.length === 0 ? AsyncStateView.EMPTY : AsyncStateView.READY
        title: qsTr("Sin zonas")
        message: qsTr("No hay zonas disponibles para asignar streams.")

        readyContent: Flickable {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.xl
            contentHeight: column.height + MichiTheme.spacing.xxl
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            activeFocusOnTab: true

            Column {
                id: column
                width: parent.width
                spacing: MichiTheme.spacing.lg

                MichiButton {
                    Accessible.role: Accessible.Button

                    activeFocusOnTab: true

                    text: qsTr("< Volver")
                    variant: "ghost"
                    onClicked: root.backClicked()
                    Keys.onReturnPressed: root.backClicked()
                    Keys.onSpacePressed: root.backClicked()
                }

                Text {
                    text: qsTr("Enrutamiento de stream")
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.pageTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Text {
                    text: qsTr("Stream activo: ") + (root.activeStreamName || "Ninguno")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Text {
                    text: qsTr("Asigna un stream a cada zona:")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.bodySize
                }

                Repeater {
                    id: zoneRepeater
                    model: root.zones

                    GlassMaterial {
                        width: parent.width
                        height: 80
                        radius: MichiTheme.radius.md
                        variant: "base"

                        Row {
                            anchors.fill: parent
                            anchors.margins: MichiTheme.spacing.lg
                            spacing: MichiTheme.spacing.md

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 200
                                spacing: MichiTheme.spacing.xs

                                Text {
                                    text: modelData.name || "Zona"
                                    color: MichiTheme.colors.textPrimary
                                    font.pixelSize: MichiTheme.typography.cardTitleSize
                                    font.weight: MichiTheme.typography.weightSemiBold
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                Text {
                                    text: qsTr("Stream: ") + (modelData.streamId === root.activeStreamId ? root.activeStreamName || "Stream activo" : (modelData.streamId || "Ninguno"))
                                    color: MichiTheme.colors.textSecondary
                                    font.pixelSize: MichiTheme.typography.metaSize
                                }
                            }

                            StatusBadge {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.streamId === root.activeStreamId ? "Stream activo" : qsTr("Stream alterno")
                                kind: modelData.streamId === root.activeStreamId ? "success" : "disconnected"
                            }
                                Accessible.role: Accessible.Button

                                activeFocusOnTab: true


                            MichiButton {
                                anchors.verticalCenter: parent.verticalCenter
                                text: qsTr("Cambiar stream")
                                variant: "ghost"
                                onClicked: root.streamAssigned(modelData.id || "", root.activeStreamId)
                            }
                        }
                    }
                }
            }
        }
    }
}
