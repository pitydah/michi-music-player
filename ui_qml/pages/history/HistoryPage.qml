import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var bridge: typeof historyBridge !== "undefined" ? historyBridge : null
    property string _viewMode: "timeline"
    property bool _loading: false
    property string _statusMsg: ""

    function refresh() {
        if (root.bridge && typeof root.bridge.refresh !== "undefined")
            root.bridge.refresh()
    }

    function removeItem(trackId) {
        if (root.bridge && typeof root.bridge.removeHistoryItem !== "undefined") {
            var result = root.bridge.removeHistoryItem(String(trackId))
            if (result && result.ok) root._statusMsg = "Registro eliminado"
            else root._statusMsg = result && result.error ? "Error: " + result.error : "Error al eliminar"
        }
    }

    function clearAll() {
        if (root.bridge && typeof root.bridge.clearHistory !== "undefined") {
            var result = root.bridge.clearHistory()
            if (result && result.ok) root._statusMsg = "Historial limpiado"
            else root._statusMsg = result && result.error ? "Error: " + result.error : "Error al limpiar"
            root.refresh()
        }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: MichiTheme.spacing.md; spacing: MichiTheme.spacing.md

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: "Historial"; font.pixelSize: MichiTheme.typography.sectionTitleSize
                color: MichiTheme.colors.textPrimary; font.weight: MichiTheme.typography.weightSemiBold
            }
            Item { Layout.fillWidth: true }
            Label {
                text: root.bridge ? root.bridge.historyCount + " registros" : ""
                color: MichiTheme.colors.textSecondary; font.pixelSize: MichiTheme.typography.metaSize
            }
            MichiButton {
                text: "Vista"; variant: "ghost"
                onClicked: root._viewMode = root._viewMode === "timeline" ? "table" : "timeline"
            }
            MichiButton { text: "Retención"; variant: "ghost"; onClicked: retentionDialog.open() }
            MichiButton {
                text: "Limpiar todo"; variant: "danger"
                onClicked: confirmClearDialog.open()
            }
            MichiButton {
                text: "Exportar"; variant: "ghost"
                onClicked: {
                    if (root.bridge && root.bridge.historyQueryService &&
                        typeof root.bridge.historyQueryService.fetchHistory !== "undefined") {
                        var data = root.bridge.historyQueryService.fetchHistory(0, 10000)
                        root._statusMsg = "Exportación completada (" + (data ? data.length : 0) + " registros)"
                    }
                }
            }
        }

        HistoryFilterBar {
            id: filterBar; Layout.fillWidth: true
            onFiltersChanged: root.refresh()
        }

        HistoryStats {
            id: statsBar; Layout.fillWidth: true
            totalCount: root.bridge ? root.bridge.historyCount : 0
        }

        Item {
            Layout.fillWidth: true; Layout.fillHeight: true

            HistoryTimeline {
                id: timelineView; anchors.fill: parent
                model: root.bridge ? root.bridge.historyModel : null
                bridge: root.bridge
                visible: root._viewMode === "timeline"
                onPlayRequested: function(trackId, title) {
                    if (root.bridge && root.bridge.playbackBridge &&
                        typeof root.bridge.playbackBridge.play !== "undefined")
                        root.bridge.playbackBridge.play(trackId)
                }
                onContextMenuRequested: function(trackId, index) {
                    if (trackId) root.removeItem(trackId)
                }
            }

            HistoryTable {
                id: tableView; anchors.fill: parent
                model: root.bridge ? root.bridge.historyModel : null
                bridge: root.bridge
                visible: root._viewMode === "table"
                onPlayRequested: function(trackId, title) {
                    if (root.bridge && root.bridge.playbackBridge &&
                        typeof root.bridge.playbackBridge.play !== "undefined")
                        root.bridge.playbackBridge.play(trackId)
                }
                onRemoveRequested: function(trackId) {
                    root.removeItem(trackId)
                }
            }
        }

        Text {
            text: root._statusMsg; color: MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            Layout.fillWidth: true; visible: text !== ""
        }
    }

    HistoryRetentionDialog {
        id: retentionDialog
        bridge: root.bridge
        onRetentionApplied: function(count) {
            root._statusMsg = "Retención aplicada: " + count + " registros eliminados"
            root.refresh()
        }
    }

    Dialog {
        id: confirmClearDialog
        title: "Limpiar historial"
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        x: (parent.width - width) / 2; y: (parent.height - height) / 3
        Text {
            text: "¿Eliminar todo el historial de reproducción? Esta acción no se puede deshacer."
            color: MichiTheme.colors.textPrimary; font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap; width: 300
        }
        onAccepted: root.clearAll()
    }

    Component.onCompleted: root.refresh()
}
