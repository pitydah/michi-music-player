import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    property var bridge: typeof historyBridge !== "undefined" ? historyBridge : null

    function refresh() { if (root.bridge) root.bridge.refresh() }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.md
        RowLayout {
            Layout.fillWidth: true
            Label { text: "Historial"; font.pixelSize: MichiTheme.typography.sectionTitleSize; color: MichiTheme.colors.textPrimary }
            Item { Layout.fillWidth: true }
            Label { text: root.bridge ? root.bridge.historyCount + " registros" : ""; color: MichiTheme.colors.textSecondary }
            MichiButton { text: "Limpiar"; variant: "ghost"; destructive: true; onClicked: { if (root.bridge) root.bridge.clearHistory(); root.refresh() } }
        }
        ListView {
            id: historyList; Layout.fillWidth: true; Layout.fillHeight: true
            model: root.bridge ? root.bridge.historyModel : null; clip: true; spacing: 2
            delegate: Rectangle {
                width: historyList.width; height: 48; color: MichiTheme.colors.surfaceCard; radius: MichiTheme.radius.sm
                RowLayout {
                    anchors.fill: parent; anchors.margins: MichiTheme.spacing.sm; spacing: MichiTheme.spacing.sm
                    Label { text: model.title || ""; Layout.fillWidth: true; elide: Text.ElideRight; color: MichiTheme.colors.textPrimary }
                    Label { text: model.artist || ""; color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.captionSize }
                    Label { text: model.playedAt || ""; color: MichiTheme.colors.textMuted; font.pixelSize: MichiTheme.typography.captionSize }
                }
            }
            Item { anchors.centerIn: parent; visible: historyList.count === 0
                Label { text: "Sin historial"; color: MichiTheme.colors.textSecondary }
            }
        }
    }
    Component.onCompleted: root.refresh()
}
