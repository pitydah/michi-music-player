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

    ListView {
        id: timelineView
        anchors.fill: parent
        clip: true
        spacing: 1
        model: root.model

        delegate: Rectangle {
            id: delegateRoot
            width: timelineView.width
            height: 56
            color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
            radius: MichiTheme.radiusSm

            objectName: "history.timelineItem." + index
            Accessible.role: Accessible.ListItem
            Accessible.name: (modelData.title || model.title || "") + " por " + (modelData.artist || model.artist || "")

            Row {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.sm

                Column {
                    width: parent.width - 160
                    spacing: 2
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        text: modelData.title || model.title || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                        elide: Text.ElideRight
                        width: parent.width
                    }

                    Text {
                        text: (modelData.artist || model.artist || "") + " · " + (modelData.album || model.album || "")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.width
                        visible: (modelData.artist || model.artist || modelData.album || model.album) !== ""
                    }

                    Text {
                        text: (modelData.playedAt || model.played_at || "") + (modelData.device || model.device ? " [" + (modelData.device || model.device) + "]" : "")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                        elide: Text.ElideRight
                        width: parent.width
                        visible: text !== ""
                    }
                }

                Row {
                    width: 140
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4
                    layoutDirection: Qt.RightToLeft

                    Text {
                        text: "\u2716"; color: MichiTheme.colors.error
                        font.pixelSize: MichiTheme.typography.metaSize
                        width: 24; height: 24
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

                    Text {
                        text: "\uD83D\uDCC2"; color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.metaSize
                        width: 24; height: 24
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.openAlbumRequested(
                                modelData.albumKey || modelData.album || model.albumKey || model.album || "")
                        }
                        Accessible.role: Accessible.Button
                        Accessible.name: "Abrir álbum"
                    }

                    Text {
                        text: "\uD83C\uDFB5"; color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.metaSize
                        width: 24; height: 24
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
                        text: "\uD83D\uDD0A"; color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.metaSize
                        width: 24; height: 24
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
                        text: "\u25B6"; color: MichiTheme.colors.accent
                        font.pixelSize: MichiTheme.typography.bodySize
                        width: 24; height: 24
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
            visible: timelineView.count === 0
            text: "Sin historial de reproducción"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
        }
    }
}
