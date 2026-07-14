import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Qt.labs.platform
import "../../theme"
import "../../components"
import "../../materials"

Item {
    id: root

    property var bridge: null
    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var _sources: []
    property bool _errorState: false
    property string _errorMessage: ""

    signal sourceSelected(int sourceId)
    signal sourceAdded(string path)
    signal sourceRemoved(int sourceId)

    function reload() {
        if (root.lib && root.lib.getSourcesList) {
            root._sources = root.lib.getSourcesList()
            root._errorState = false
            root._errorMessage = ""
        } else {
            root._errorState = true
            root._errorMessage = "Servicio de fuentes no disponible"
        }
    }

    function addSource(path) {
        if (!path) return
        if (root.lib && root.lib.addFolder) {
            var result = root.lib.addFolder(path)
            if (result && result.ok) {
                root.sourceAdded(path)
                root.reload()
            } else {
                root._errorState = true
                root._errorMessage = result && result.error ? result.error : "Error al añadir fuente"
            }
        }
    }

    function editSource(sourceId, data) {
        if (root.lib && root.lib.editSource) {
            var result = root.lib.editSource(sourceId, data)
            if (result && result.ok) root.reload()
        }
    }

    function removeSource(sourceId) {
        if (root.lib && root.lib.removeSource) {
            var result = root.lib.removeSource(sourceId)
            if (result && result.ok) {
                root.sourceRemoved(sourceId)
                root.reload()
            }
        }
    }

    function toggleSource(sourceId, enable) {
        if (enable && root.lib && root.lib.enableSource) root.lib.enableSource(sourceId)
        else if (!enable && root.lib && root.lib.disableSource) root.lib.disableSource(sourceId)
        root.reload()
    }

    function scanSource(sourceId) {
        if (root.lib && root.lib.scanSource) root.lib.scanSource(sourceId)
    }

    function cancelScan(sourceId) {
        if (root.lib && root.lib.cancelSourceScan) root.lib.cancelSourceScan(sourceId)
    }

    Component.onCompleted: reload()

    ColumnLayout {
        anchors.fill: parent; spacing: 0

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 40
            color: MichiTheme.colors.surfaceCard

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md; anchors.rightMargin: MichiTheme.spacing.md

                Text {
                    text: "Fuentes de biblioteca"
                    color: MichiTheme.colors.textPrimary
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    font.weight: MichiTheme.typography.weightSemiBold
                }

                Item { Layout.fillWidth: true }

                MichiButton { text: "Añadir fuente"; variant: "primary"; onClicked: addDialog.open() }
                MichiButton { text: "Refrescar"; variant: "ghost"; onClicked: root.reload() }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 24
            color: MichiTheme.colors.errorSurface
            visible: root._errorState
            Text {
                anchors.centerIn: parent
                text: root._errorMessage
                color: MichiTheme.colors.errorColor
                font.pixelSize: MichiTheme.typography.metaSize
            }
        }

        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            model: root._sources
            clip: true; boundsBehavior: Flickable.StopAtBounds
            spacing: MichiTheme.spacing.xs

            ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

            delegate: SourceCard {
                width: parent.width
                sourceId: modelData.id || 0
                sourceName: modelData.name || ""
                sourcePath: modelData.path || ""
                sourceType: modelData.source_type || "local"
                enabled: modelData.enabled !== false
                status: modelData.status || ""
                trackCount: modelData.track_count || 0
                lastIndexed: modelData.last_indexed || ""
                scanning: modelData.scanning || false
                scanProgress: modelData.scan_progress || ""
                priority: modelData.priority || 0
                watchMode: modelData.watch_mode || false
                exclusionCount: modelData.exclusion_count || 0

                onEditRequested: {
                    editDialog.sourceId = sourceId
                    editDialog.sourceData = modelData
                    editDialog.open()
                }
                onRemoveRequested: {
                    confirmDialog.sourceId = sourceId
                    confirmDialog.open()
                }
                onToggleEnabled: function(enable) {
                    root.toggleSource(sourceId, enable)
                }
                onScanRequested: {
                    root.scanSource(sourceId)
                }
                onCancelScanRequested: {
                    root.cancelScan(sourceId)
                }
                onPriorityChanged: function(newPriority) {
                    if (root.lib && root.lib.setSourcePriority)
                        root.lib.setSourcePriority(sourceId, newPriority)
                }
                onWatchModeToggled: function(enable) {
                    if (root.lib && root.lib.setSourceWatchMode)
                        root.lib.setSourceWatchMode(sourceId, enable)
                }
                onExclusionsRequested: {
                    if (typeof navigationBridge !== "undefined")
                        navigationBridge.navigateWithParams("library.source_exclusions", {source_id: sourceId})
                }
            }

            Text {
                anchors.centerIn: parent
                text: root._sources.length === 0 ? "No hay fuentes configuradas" : ""
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.bodySize
                visible: root._sources.length === 0
            }
        }
    }

    FolderDialog {
        id: addDialog
        title: "Seleccionar carpeta de música"
        onAccepted: {
            var folderPath = selectedFolder.toLocalFile()
            root.addSource(folderPath)
        }
    }

    SourceEditorDialog {
        id: editDialog
        bridge: root.lib
        onAccepted: {
            root.editSource(editDialog.sourceId, editDialog.getData())
        }
    }

    Popup {
        id: confirmDialog
        property int sourceId: 0
        modal: true
        focus: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3
        width: 320

        Column {
            spacing: MichiTheme.spacing.md
            padding: MichiTheme.spacing.lg

            Label {
                text: "Eliminar fuente"
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                color: MichiTheme.colors.textPrimary
            }

            Label {
                text: "¿Eliminar esta fuente de la biblioteca?"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm
                anchors.horizontalCenter: parent.horizontalCenter
                MichiButton {
                    text: "Sí"
                    variant: "danger"
                    onClicked: {
                        root.removeSource(confirmDialog.sourceId)
                        confirmDialog.close()
                    }
                }
                MichiButton {
                    text: "No"
                    variant: "ghost"
                    onClicked: confirmDialog.close()
                }
            }
        }
    }
}
