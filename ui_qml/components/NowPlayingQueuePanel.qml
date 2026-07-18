import QtQuick
import QtQuick.Controls
import "../theme"

Item {
    Accessible.role: Accessible.Pane
    Accessible.name: "Now Playing Queue"
    objectName: "nowPlayingQueuePanel"
    focus: true
    id: root

    property var playbackState: typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null
    property bool expanded: false

    implicitHeight: expanded ? Math.min(200, contentHeight) : 0
    clip: true

    property real contentHeight: column.height + MichiTheme.spacing.md * 2

    Column {
        id: column
        width: parent.width
        spacing: MichiTheme.spacing.xs

        Text {
            text: qsTr("Cola (") + (root.playbackState ? root.playbackState.queue.length : 0) + ")"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: MichiTheme.typography.weightMedium
            leftPadding: MichiTheme.spacing.md
            topPadding: MichiTheme.spacing.sm
            visible: root.expanded
        }

        Repeater {
            model: root.expanded && root.playbackState ? root.playbackState.queue.slice(0, 8) : []

            Rectangle {
                width: parent.width; height: 28; color: "transparent"
                Row {
                    anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                    Text { width: parent.width * 0.50; text: modelData.title || "—"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                    Text { width: parent.width * 0.40; text: modelData.artist || ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                }
            }
        }

        Text {
            text: qsTr("Sin canciones en cola")
            color: MichiTheme.colors.textMuted
            font.pixelSize: MichiTheme.typography.metaSize
            leftPadding: MichiTheme.spacing.md
            visible: root.expanded && root.playbackState && root.playbackState.queue.length === 0
        }

        Text {
            text: qsTr("Historial (") + (root.playbackState ? root.playbackState.history.length : 0) + ")"
            color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: MichiTheme.typography.weightMedium
            leftPadding: MichiTheme.spacing.md
            topPadding: MichiTheme.spacing.sm
            visible: root.expanded && root.playbackState && root.playbackState.history.length > 0
        }

        Repeater {
            model: root.expanded && root.playbackState ? root.playbackState.history.slice(-5).reverse() : []

            Rectangle {
                width: parent.width; height: 28; color: "transparent"
                Row {
                    anchors.fill: parent; anchors.leftMargin: MichiTheme.spacing.md; spacing: MichiTheme.spacing.sm
                    Text { width: parent.width * 0.50; text: modelData.title || "—"; color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                    Text { width: parent.width * 0.40; text: modelData.artist || ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.metaSize; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                }
            }
        }
    }
}
