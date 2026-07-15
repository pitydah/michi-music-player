import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var model: null
    property var bridge: null

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    signal playRequested(int trackId, string title)
    signal removeRequested(int eventId, int trackId)
    signal openTrackRequested(int trackId)
    signal openAlbumRequested(int trackId)
    signal addToQueueRequested(int trackId)
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    signal playRequested(int eventId, int trackId, string title)
    signal queueRequested(int eventId, int trackId)
    signal openTrackRequested(int trackId)
    signal openAlbumRequested(string albumKey)
    signal removeRequested(int eventId)
=======
    signal playRequested(int trackId, string title)
    signal removeRequested(int eventId, int trackId)
    signal openTrackRequested(int trackId)
    signal openAlbumRequested(int trackId)
    signal addToQueueRequested(int trackId)
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    ListView {
        id: timelineView
        anchors.fill: parent
        clip: true
        spacing: 1
        model: root.model
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        objectName: "historyTimelineList"
        Accessible.role: Accessible.List
        Accessible.name: "Línea de tiempo del historial"
        keyNavigationWraps: true
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes

        delegate: Rectangle {
            width: timelineView.width
<<<<<<< Updated upstream
            height: 52
=======
            height: 56
=======
        objectName: "historyTimelineList"
        Accessible.role: Accessible.List
        Accessible.name: "Línea de tiempo del historial"
        keyNavigationWraps: true

        delegate: Rectangle {
            width: timelineView.width
            height: 52
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                        text: model.title || modelData.title || ""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                        text: modelData.title || model.title || ""
=======
                        text: model.title || modelData.title || ""
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                        color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize
                        font.weight: MichiTheme.typography.weightMedium
                        elide: Text.ElideRight
                        width: parent.width
                    }

                    Text {
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                        text: (model.artist || modelData.artist || "") + " · " +
                              (model.album || modelData.album || "")
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                        text: (modelData.artist || model.artist || "") + " · " + (modelData.album || model.album || "")
=======
                        text: (model.artist || modelData.artist || "") + " · " +
                              (model.album || modelData.album || "")
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight
                        width: parent.width
<<<<<<< Updated upstream
<<<<<<< Updated upstream
                        visible: (model.artist || modelData.artist || model.album || modelData.album) !== ""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
                        visible: (modelData.artist || model.artist || modelData.album || model.album) !== ""
                    }

                    Text {
                        text: (modelData.playedAt || model.played_at || "") + (modelData.device || model.device ? " [" + (modelData.device || model.device) + "]" : "")
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.captionSize
                        elide: Text.ElideRight
                        width: parent.width
                        visible: text !== ""
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======

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
=======
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
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
                    }
                }
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
                acceptedButtons: Qt.NoButton
=======
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
                acceptedButtons: Qt.NoButton
=======
>>>>>>> Stashed changes
                acceptedButtons: Qt.RightButton
                onClicked: contextMenu.popup()
            }

            Menu {
                id: contextMenu
                objectName: "historyContextMenu"
                Accessible.name: "Menú contextual"

                MenuItem {
                    text: "Reproducir"
                    objectName: "playEventMenuItem"
                    Accessible.name: "Reproducir"
                    onTriggered: root.playRequested(
                        model.trackId || modelData.track_id || model.track_id || 0,
                        model.title || modelData.title || "")
                }
                MenuItem {
                    text: "Añadir a la cola"
                    objectName: "addToQueueMenuItem"
                    Accessible.name: "Añadir a la cola"
                    onTriggered: root.addToQueueRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuItem {
                    text: "Abrir pista"
                    objectName: "openTrackMenuItem"
                    Accessible.name: "Abrir pista"
                    onTriggered: root.openTrackRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuItem {
                    text: "Abrir álbum"
                    objectName: "openAlbumMenuItem"
                    Accessible.name: "Abrir álbum"
                    onTriggered: root.openAlbumRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuSeparator {}
                MenuItem {
                    text: "Eliminar evento"
                    objectName: "removeEventMenuItem"
                    Accessible.name: "Eliminar evento"
                    onTriggered: root.removeRequested(
                        model.id || modelData.id || model.eventId || modelData.event_id || 0,
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
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
