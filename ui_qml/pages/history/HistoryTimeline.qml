import QtQuick
import QtQuick.Controls
import "../../theme"
import "../../components"

Item {
    id: root

    property var model: null
    property var bridge: null

    signal playRequested(int trackId, string title)
    signal contextMenuRequested(int trackId, int index)

    ListView {
        id: timelineView; anchors.fill: parent; clip: true; spacing: 1
        model: root.model
        delegate: Rectangle {
            width: timelineView.width; height: 52
            color: mouseArea.containsMouse ? MichiTheme.colors.surfaceHover : "transparent"
            radius: MichiTheme.radiusSm

            Row {
                anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm

                Column {
                    width: parent.width - 120; spacing: 2; anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: model.title || ""; color: MichiTheme.colors.textPrimary
                        font.pixelSize: MichiTheme.typography.bodySize; font.weight: MichiTheme.typography.weightMedium
                        elide: Text.ElideRight; width: parent.width
                    }
                    Text {
                        text: (model.artist || "") + " · " + (model.album || "")
                        color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
                        elide: Text.ElideRight; width: parent.width
                        visible: (model.artist || model.album) !== ""
                    }
                }

                Column {
                    width: 100; anchors.verticalCenter: parent.verticalCenter; spacing: 1
                    Text {
                        text: model.playedAt || ""; color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; width: parent.width
                    }
                    Text {
                        text: model.device ? "[" + model.device + "]" : ""
                        color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize
                        visible: model.device !== ""
                    }
                }

                Text {
                    text: "▶"; color: MichiTheme.colors.accent
                    font.pixelSize: MichiTheme.typography.bodySize; anchors.verticalCenter: parent.verticalCenter
                    width: 24
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: root.playRequested(model.trackId || model.track_id || 0, model.title || "")
                    }
                }
            }

            MouseArea {
                id: mouseArea; anchors.fill: parent; hoverEnabled: true
                acceptedButtons: Qt.RightButton
                onClicked: root.contextMenuRequested(model.trackId || model.track_id || 0, index)
            }
        }

        Text {
            anchors.centerIn: parent; visible: timelineView.count === 0
            text: "Sin historial de reproducción"
            color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.bodySize
        }
    }
}
