import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "History Timeline"
    objectName: "historyTimeline"
    focus: true
    id: root

    property var model: null
    property var bridge: null

    signal playRequested(int trackId, string title)
    signal removeRequested(int eventId, int trackId)
    signal openTrackRequested(int trackId)
    signal openAlbumRequested(int trackId)
    signal addToQueueRequested(int trackId)

    ListView {
        focusPolicy: Qt.StrongFocus
        id: timelineView
        anchors.fill: parent
        clip: true
        spacing: 1
        model: root.model
        keyNavigationWraps: true

        delegate: Rectangle {
            width: timelineView.width
            height: 52
            color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
            radius: MichiTheme.radiusSm

            Row {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.sm

                Column {
                    width: parent.width - 160
                    spacing: 2
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        text: model.title || modelData.title || ""
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                        elide: Text.ElideRight
                        width: parent.width
                    }
                    Text {
                        text: (model.artist || modelData.artist || "") + " · " +
                              (model.album || modelData.album || "")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.width
                        visible: (model.artist || modelData.artist || model.album || modelData.album) !== ""
                    }
                }

                Column {
                    width: 100
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 1
                    Text {
                        text: model.playedAt || modelData.playedAt || ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.width
                    }
                    Text {
                        text: model.device || modelData.device ? "[" + (model.device || modelData.device) + "]" : ""
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                        visible: (model.device || modelData.device) !== ""
                    }
                }

                Text {
                    text: "▶"
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                    width: 24
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.playRequested(
                            model.trackId || modelData.track_id || model.track_id || 0,
                            model.title || modelData.title || "")
                    }
                }
                Text {
                    text: "☰"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                    width: 24
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: contextMenu.popup()
                    }
                }
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.RightButton
                onClicked: contextMenu.popup()
            }

            Menu {
                id: contextMenu

                MenuItem {
                    text: "Reproducir"
                    onTriggered: root.playRequested(
                        model.trackId || modelData.track_id || model.track_id || 0,
                        model.title || modelData.title || "")
                }
                MenuItem {
                    text: "Añadir a la cola"
                    onTriggered: root.addToQueueRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuItem {
                    text: "Abrir pista"
                    onTriggered: root.openTrackRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuItem {
                    text: "Abrir álbum"
                    onTriggered: root.openAlbumRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuSeparator {}
                MenuItem {
                    text: "Eliminar evento"
                    onTriggered: root.removeRequested(
                        model.id || modelData.id || model.eventId || modelData.event_id || 0,
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
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
