import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var model: null
    property var bridge: null
    property var _selectedItems: []
    property bool selectionMode: false

    signal playRequested(int trackId, string title)
    signal removeRequested(int trackId)

    function toggleSelection(trackId) {
        var idx = root._selectedItems.indexOf(trackId)
        if (idx >= 0) root._selectedItems.splice(idx, 1)
        else root._selectedItems.push(trackId)
    }

    ListView {
        id: tableView; anchors.fill: parent; clip: true; spacing: 1
        model: root.model
        delegate: Rectangle {
            width: tableView.width; height: 44
            color: root._selectedItems.indexOf(model.trackId || model.track_id || 0) >= 0
                   ? MichiTheme.colors.accentFaint : mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
            radius: MichiTheme.radiusSm

            Row {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                CheckBox {
                    width: 24; anchors.verticalCenter: parent.verticalCenter
                    visible: root.selectionMode
                    checked: root._selectedItems.indexOf(model.trackId || model.track_id || 0) >= 0
                    onCheckedChanged: root.toggleSelection(model.trackId || model.track_id || 0)
                }

                Text {
                    width: parent.width * 0.30; text: model.title || ""
                    color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
                    font.weight: MichiTheme.typography.weightMedium; elide: Text.ElideRight
                    anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: parent.width * 0.20; text: model.artist || ""
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: parent.width * 0.20; text: model.album || ""
                    color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: 80; text: model.playedAt || ""
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter
                }
                Text {
                    width: 60; text: model.device || ""
                    color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                    elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter; visible: model.device !== ""
                }
                Text {
                    width: 24; text: "▶"; color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: root.playRequested(model.trackId || model.track_id || 0, model.title || "")
                    }
                }
                Text {
                    width: 24; text: "[X]"; color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.metaSize; anchors.verticalCenter: parent.verticalCenter
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: root.removeRequested(model.trackId || model.track_id || 0)
                    }
                }
            }

            MouseArea {
                id: mouseArea; anchors.fill: parent; hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }
        }

        Text {
            anchors.centerIn: parent; visible: tableView.count === 0
            text: "No hay registros de historial"
            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
        }
    }
}
