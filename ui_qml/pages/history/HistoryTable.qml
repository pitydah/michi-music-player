import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var model: null
    property var bridge: null

    signal playRequested(int eventId, int trackId, string title)
    signal queueRequested(int eventId, int trackId)
    signal openTrackRequested(int trackId)
    signal openAlbumRequested(string albumKey)
    signal removeRequested(int eventId)

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surface
        radius: MichiTheme.radiusSm

        Column {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                width: parent.width
                height: 32
                color: MichiTheme.colors.surfaceHover

                Row {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    spacing: MichiTheme.spacing.sm

                    Text { width: parent.width * 0.30; text: "Título"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium }
                    Text { width: parent.width * 0.18; text: "Artista"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium }
                    Text { width: parent.width * 0.18; text: "Álbum"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium }
                    Text { width: 80; text: "Fecha"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium }
                    Text { width: 60; text: "Disp."; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium }
                    Text { width: 100; text: "Acciones"; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize; font.weight: MichiTheme.typography.weightMedium }
                }
            }

            ListView {
                id: tableView
                width: parent.width
                height: parent.height - 32
                clip: true
                spacing: 0
                model: root.model

                delegate: Rectangle {
                    width: tableView.width
                    height: 40
                    color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
                    radius: 0

                    objectName: "history.tableItem." + index
                    Accessible.role: Accessible.ListItem
                    Accessible.name: (modelData.title || model.title || "") + " por " + (modelData.artist || model.artist || "")

                    Row {
                        anchors.fill: parent
                        anchors.margins: MichiTheme.spacing.sm
                        spacing: MichiTheme.spacing.sm

                        Text {
                            width: parent.width * 0.30
                            text: modelData.title || model.title || ""
                            color: MichiTheme.colors.textPrimary
                            font.pixelSize: MichiTheme.typography.bodySize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.18
                            text: modelData.artist || model.artist || ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: parent.width * 0.18
                            text: modelData.album || model.album || ""
                            color: MichiTheme.colors.textSecondary
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: 80
                            text: modelData.playedAt || model.played_at || ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            width: 60
                            text: modelData.device || model.device || ""
                            color: MichiTheme.colors.textMuted
                            font.pixelSize: MichiTheme.typography.metaSize
                            elide: Text.ElideRight
                            anchors.verticalCenter: parent.verticalCenter
                            visible: text !== ""
                        }
                        Row {
                            width: 100
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 4

                            Text {
                                text: "\u25B6"; color: MichiTheme.colors.accent
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: 20; height: 20
                                verticalAlignment: Text.AlignVCenter
                                horizontalAlignment: Text.AlignHCenter
                                MouseArea {
                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                    onClicked: root.playRequested(
                                        modelData.eventId || modelData.id || model.eventId || model.id || 0,
                                        modelData.trackId || modelData.track_id || model.trackId || model.track_id || 0,
                                        modelData.title || model.title || "")
                                }
                                Accessible.role: Accessible.Button
                                Accessible.name: "Reproducir"
                            }
                            Text {
                                text: "\uD83D\uDD0A"; color: MichiTheme.colors.accent
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: 20; height: 20
                                verticalAlignment: Text.AlignVCenter
                                horizontalAlignment: Text.AlignHCenter
                                MouseArea {
                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                    onClicked: root.queueRequested(
                                        modelData.eventId || modelData.id || model.eventId || model.id || 0,
                                        modelData.trackId || modelData.track_id || model.trackId || model.track_id || 0)
                                }
                                Accessible.role: Accessible.Button
                                Accessible.name: "Agregar a la cola"
                            }
                            Text {
                                text: "\uD83C\uDFB5"; color: MichiTheme.colors.accent
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: 20; height: 20
                                verticalAlignment: Text.AlignVCenter
                                horizontalAlignment: Text.AlignHCenter
                                MouseArea {
                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                    onClicked: root.openTrackRequested(
                                        modelData.trackId || modelData.track_id || model.trackId || model.track_id || 0)
                                }
                                Accessible.role: Accessible.Button
                                Accessible.name: "Abrir pista"
                            }
                            Text {
                                text: "\u2716"; color: MichiTheme.colors.error
                                font.pixelSize: MichiTheme.typography.metaSize
                                width: 20; height: 20
                                verticalAlignment: Text.AlignVCenter
                                horizontalAlignment: Text.AlignHCenter
                                MouseArea {
                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                    onClicked: root.removeRequested(
                                        modelData.eventId || modelData.id || model.eventId || model.id || 0)
                                }
                                Accessible.role: Accessible.Button
                                Accessible.name: "Eliminar registro"
                            }
                        }
                    }

                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: tableView.count === 0
                    text: "No hay registros de historial"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                }
            }
        }
    }
}
