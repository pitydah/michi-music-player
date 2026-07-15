import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var model: null
    property var bridge: null

    signal playRequested(int trackId, string title)
    signal removeRequested(int trackId)
    signal openTrackRequested(int trackId)
    signal openAlbumRequested(int trackId)
    signal addToQueueRequested(int trackId)
    signal playRequested(int eventId, int trackId, string title)
    signal queueRequested(int eventId, int trackId)
    signal openTrackRequested(int trackId)
    signal openAlbumRequested(string albumKey)
    signal removeRequested(int eventId)
    signal playRequested(int trackId, string title)
    signal removeRequested(int trackId)
    signal openTrackRequested(int trackId)
    signal openAlbumRequested(int trackId)
    signal addToQueueRequested(int trackId)

    Rectangle {
        anchors.fill: parent
        color: MichiTheme.colors.surface
        radius: MichiTheme.radiusSm

    ListView {
        id: tableView
        anchors.fill: parent
        clip: true
        spacing: 1
        model: root.model
        objectName: "historyTableList"
        Accessible.role: Accessible.Table
        Accessible.name: "Tabla del historial"
        keyNavigationWraps: true
        Column {
            anchors.fill: parent
            spacing: 0

        delegate: Rectangle {
            width: tableView.width
            height: 44
            color: root._selectedItems.indexOf(model.trackId || modelData.track_id || model.track_id || 0) >= 0
                   ? MichiTheme.colors.accentFaint
                   : mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
            radius: MichiTheme.radiusSm

            Row {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.sm

                CheckBox {
                    width: 24
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.selectionMode
                    checked: root._selectedItems.indexOf(model.trackId || modelData.track_id || model.track_id || 0) >= 0
                    onCheckedChanged: root.toggleSelection(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }

                Text {
                    width: parent.width * 0.25
                    text: model.title || modelData.title || ""
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: parent.width * 0.18
                    text: model.artist || modelData.artist || ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: parent.width * 0.18
                    text: model.album || modelData.album || ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: 80
                    text: {
                        var eventId = model.eventId || modelData.event_id || model.id || modelData.id || ""
                        return eventId > 0 ? "#" + eventId : ""
                    }
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                    visible: eventId > 0
                }
                Text {
                    width: 70
                    text: model.playedAt || modelData.playedAt || ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: 50
                    text: model.device || modelData.device || ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                    visible: (model.device || modelData.device) !== ""
                }
                Text {
                    width: 24
                    text: "▶"
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.playRequested(
                            model.trackId || modelData.track_id || model.track_id || 0,
                            model.title || modelData.title || "")
                    }
                }
                Text {
                    width: 24
                    text: "☰"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: contextMenu.popup()
                    }
                }
                Text {
                    width: 24
                    text: "[X]"
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.metaSize
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.removeRequested(
                            model.trackId || modelData.track_id || model.track_id || 0)
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
                objectName: "historyTableContextMenu"
                Accessible.name: "Menú contextual"

                MenuItem {
                    text: "Reproducir"
                    objectName: "tablePlayMenuItem"
                    Accessible.name: "Reproducir"
                    onTriggered: root.playRequested(
                        model.trackId || modelData.track_id || model.track_id || 0,
                        model.title || modelData.title || "")
                }
                MenuItem {
                    text: "Añadir a la cola"
                    objectName: "tableAddQueueMenuItem"
                    Accessible.name: "Añadir a la cola"
                    onTriggered: root.addToQueueRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuItem {
                    text: "Abrir pista"
                    objectName: "tableOpenTrackMenuItem"
                    Accessible.name: "Abrir pista"
                    onTriggered: root.openTrackRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuItem {
                    text: "Abrir álbum"
                    objectName: "tableOpenAlbumMenuItem"
                    Accessible.name: "Abrir álbum"
                    onTriggered: root.openAlbumRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuSeparator {}
                MenuItem {
                    text: "Eliminar"
                    objectName: "tableRemoveMenuItem"
                    Accessible.name: "Eliminar"
                    onTriggered: root.removeRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
            }
    ListView {
        id: tableView
        anchors.fill: parent
        clip: true
        spacing: 1
        model: root.model
        objectName: "historyTableList"
        Accessible.role: Accessible.Table
        Accessible.name: "Tabla del historial"
        keyNavigationWraps: true

        delegate: Rectangle {
            width: tableView.width
            height: 44
            color: root._selectedItems.indexOf(model.trackId || modelData.track_id || model.track_id || 0) >= 0
                   ? MichiTheme.colors.accentFaint
                   : mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
            radius: MichiTheme.radiusSm

            Row {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.sm

                CheckBox {
                    width: 24
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.selectionMode
                    checked: root._selectedItems.indexOf(model.trackId || modelData.track_id || model.track_id || 0) >= 0
                    onCheckedChanged: root.toggleSelection(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }

                Text {
                    width: parent.width * 0.25
                    text: model.title || modelData.title || ""
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: parent.width * 0.18
                    text: model.artist || modelData.artist || ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: parent.width * 0.18
                    text: model.album || modelData.album || ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: 80
                    text: {
                        var eventId = model.eventId || modelData.event_id || model.id || modelData.id || ""
                        return eventId > 0 ? "#" + eventId : ""
                    }
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                    visible: eventId > 0
                }
                Text {
                    width: 70
                    text: model.playedAt || modelData.playedAt || ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: 50
                    text: model.device || modelData.device || ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                    visible: (model.device || modelData.device) !== ""
                }
                Text {
                    width: 24
                    text: "▶"
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.playRequested(
                            model.trackId || modelData.track_id || model.track_id || 0,
                            model.title || modelData.title || "")
                    }
                }
                Text {
                    width: 24
                    text: "☰"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: contextMenu.popup()
                    }
                }
                Text {
                    width: 24
                    text: "[X]"
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.metaSize
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.removeRequested(
                            model.trackId || modelData.track_id || model.track_id || 0)
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
                objectName: "historyTableContextMenu"
                Accessible.name: "Menú contextual"

                MenuItem {
                    text: "Reproducir"
                    objectName: "tablePlayMenuItem"
                    Accessible.name: "Reproducir"
                    onTriggered: root.playRequested(
                        model.trackId || modelData.track_id || model.track_id || 0,
                        model.title || modelData.title || "")
                }
                MenuItem {
                    text: "Añadir a la cola"
                    objectName: "tableAddQueueMenuItem"
                    Accessible.name: "Añadir a la cola"
                    onTriggered: root.addToQueueRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuItem {
                    text: "Abrir pista"
                    objectName: "tableOpenTrackMenuItem"
                    Accessible.name: "Abrir pista"
                    onTriggered: root.openTrackRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuItem {
                    text: "Abrir álbum"
                    objectName: "tableOpenAlbumMenuItem"
                    Accessible.name: "Abrir álbum"
                    onTriggered: root.openAlbumRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuSeparator {}
                MenuItem {
                    text: "Eliminar"
                    objectName: "tableRemoveMenuItem"
                    Accessible.name: "Eliminar"
                    onTriggered: root.removeRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
            }
    ListView {
        id: tableView
        anchors.fill: parent
        clip: true
        spacing: 1
        model: root.model
        objectName: "historyTableList"
        Accessible.role: Accessible.Table
        Accessible.name: "Tabla del historial"
        keyNavigationWraps: true

        delegate: Rectangle {
            width: tableView.width
            height: 44
            color: root._selectedItems.indexOf(model.trackId || modelData.track_id || model.track_id || 0) >= 0
                   ? MichiTheme.colors.accentFaint
                   : mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
            radius: MichiTheme.radiusSm

            Row {
                anchors.fill: parent
                anchors.margins: MichiTheme.spacing.sm
                spacing: MichiTheme.spacing.sm

                CheckBox {
                    width: 24
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.selectionMode
                    checked: root._selectedItems.indexOf(model.trackId || modelData.track_id || model.track_id || 0) >= 0
                    onCheckedChanged: root.toggleSelection(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }

                Text {
                    width: parent.width * 0.25
                    text: model.title || modelData.title || ""
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: parent.width * 0.18
                    text: model.artist || modelData.artist || ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: parent.width * 0.18
                    text: model.album || modelData.album || ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: 80
                    text: {
                        var eventId = model.eventId || modelData.event_id || model.id || modelData.id || ""
                        return eventId > 0 ? "#" + eventId : ""
                    }
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                    visible: eventId > 0
                }
                Text {
                    width: 70
                    text: model.playedAt || modelData.playedAt || ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: 50
                    text: model.device || modelData.device || ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                    visible: (model.device || modelData.device) !== ""
                }
                Text {
                    width: 24
                    text: "▶"
                    color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.playRequested(
                            model.trackId || modelData.track_id || model.track_id || 0,
                            model.title || modelData.title || "")
                    }
                }
                Text {
                    width: 24
                    text: "☰"
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.bodySize
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: contextMenu.popup()
                    }
                }
                Text {
                    width: 24
                    text: "[X]"
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.metaSize
                    anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.removeRequested(
                            model.trackId || modelData.track_id || model.track_id || 0)
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
                objectName: "historyTableContextMenu"
                Accessible.name: "Menú contextual"

                MenuItem {
                    text: "Reproducir"
                    objectName: "tablePlayMenuItem"
                    Accessible.name: "Reproducir"
                    onTriggered: root.playRequested(
                        model.trackId || modelData.track_id || model.track_id || 0,
                        model.title || modelData.title || "")
                }
                MenuItem {
                    text: "Añadir a la cola"
                    objectName: "tableAddQueueMenuItem"
                    Accessible.name: "Añadir a la cola"
                    onTriggered: root.addToQueueRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuItem {
                    text: "Abrir pista"
                    objectName: "tableOpenTrackMenuItem"
                    Accessible.name: "Abrir pista"
                    onTriggered: root.openTrackRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuItem {
                    text: "Abrir álbum"
                    objectName: "tableOpenAlbumMenuItem"
                    Accessible.name: "Abrir álbum"
                    onTriggered: root.openAlbumRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
                MenuSeparator {}
                MenuItem {
                    text: "Eliminar"
                    objectName: "tableRemoveMenuItem"
                    Accessible.name: "Eliminar"
                    onTriggered: root.removeRequested(
                        model.trackId || modelData.track_id || model.track_id || 0)
                }
            }
        }

        Text {
            anchors.centerIn: parent
            visible: tableView.count === 0
            text: "No hay registros de historial"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
        }

        Text {
            anchors.centerIn: parent
            visible: tableView.count === 0
            text: "No hay registros de historial"
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.bodySize
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
