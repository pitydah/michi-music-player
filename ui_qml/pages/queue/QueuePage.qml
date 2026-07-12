import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    property var bridge: typeof queueBridge !== "undefined" ? queueBridge : null

    function refresh() { if (root.bridge) root.bridge.refresh() }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.md
        RowLayout {
            Layout.fillWidth: true
            Label { text: "Cola de reproducción"; font.pixelSize: MichiTheme.typography.sectionTitleSize; color: MichiTheme.colors.textPrimary }
            Item { Layout.fillWidth: true }
            Label { text: root.bridge ? root.bridge.queueCount + " pistas" : ""; color: MichiTheme.colors.textSecondary }
            MichiButton { text: "Limpiar"; variant: "ghost"; destructive: true; onClicked: { if (root.bridge) root.bridge.clearQueue(); root.refresh() } }
            MichiButton { text: "Guardar como playlist"; variant: "ghost"; onClicked: saveDialog.open() }
        }
        ListView {
            id: queueList; Layout.fillWidth: true; Layout.fillHeight: true
            model: root.bridge ? root.bridge.queueModel : null; clip: true; spacing: 2
            delegate: Rectangle {
                width: queueList.width; height: 48; color: MichiTheme.colors.surfaceCard; radius: MichiTheme.radius.sm
                RowLayout {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                    Label { text: model.title || ""; Layout.fillWidth: true; elide: Text.ElideRight; color: MichiTheme.colors.textPrimary }
                    Label { text: model.artist || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.captionSize }
                    MichiButton { text: "X"; variant: "ghost"; onClicked: { if (root.bridge) root.bridge.removeFromQueue(index); root.refresh() } }
                }
            }
            Item { anchors.centerIn: parent; visible: queueList.count === 0
                Label { text: "Cola vacía"; color: MichiTheme.colors.textSecondary }
            }
        }
    }
    Dialog {
        id: saveDialog; title: "Guardar cola como playlist"; standardButtons: Dialog.Ok | Dialog.Cancel; modal: true
        x: (parent.width - width) / 2; y: (parent.height - height) / 3; width: 300
        TextField { id: playlistName; width: parent.width; placeholderText: "Nombre de la playlist" }
        onAccepted: { if (root.bridge && playlistName.text) { root.bridge.saveAsPlaylist(playlistName.text); if (typeof notificationBridge !== 'undefined') notificationBridge.showMessage("Playlist guardada", "info") } }
    }
    Component.onCompleted: root.refresh()
}
