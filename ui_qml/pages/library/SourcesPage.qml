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
    property var sourcesBridge: typeof librarySourcesBridge !== "undefined" ? librarySourcesBridge : null
    property var _sources: []
    property bool _errorState: false
    property string _errorMessage: ""
    property bool _scanAllActive: false
    property string _scanAllLabel: "Escanear todo"

    enum PageState {
        LOADING,
        READY,
        EMPTY,
        ERROR
    }

    property int pageState: SourcesPage.LOADING

    objectName: "sources.page"
    Accessible.role: Accessible.Panel
    Accessible.name: "Fuentes de biblioteca"
    Accessible.description: "Gestiona las fuentes de música de la biblioteca"

    signal sourceSelected(int sourceId)
    signal sourceAdded(string path)
    signal sourceRemoved(int sourceId)

    function reload() {
        root.pageState = SourcesPage.LOADING
        root._errorState = false
        root._errorMessage = ""
        if (root.sourcesBridge && root.sourcesBridge.sources) {
            root._sources = root.sourcesBridge.sources
            root.pageState = root._sources.length > 0 ? SourcesPage.READY : SourcesPage.EMPTY
        } else if (root.bridge && root.bridge.getSourcesList) {
            root._sources = root.bridge.getSourcesList()
            root.pageState = root._sources.length > 0 ? SourcesPage.READY : SourcesPage.EMPTY
        } else {
            root._errorState = true
            root._errorMessage = "Servicio de fuentes no disponible"
            root.pageState = SourcesPage.ERROR
        }
    }

    function addSource(path) {
        if (!path) return
        var result = null
        if (root.sourcesBridge && root.sourcesBridge.addSource) {
            result = root.sourcesBridge.addSource(path)
        } else if (root.bridge && root.bridge.addFolder) {
            result = root.bridge.addFolder(path)
        }
        if (result && result.ok) {
            root.sourceAdded(path)
            root.reload()
        } else {
            root._errorState = true
            root._errorMessage = result && result.error ? result.error : "Error al añadir fuente"
        }
    }

    function editSource(sourceId, data) {
        if (root.bridge && root.bridge.editSource) {
            var result = root.bridge.editSource(sourceId, data)
            if (result && result.ok) root.reload()
        }
    }

    function removeSource(sourceId) {
        var result = null
        if (root.sourcesBridge && root.sourcesBridge.removeSource) {
            result = root.sourcesBridge.removeSource(sourceId)
        } else if (root.bridge && root.bridge.removeSource) {
            result = root.bridge.removeSource(sourceId)
        }
        if (result && result.ok) {
            root.sourceRemoved(sourceId)
            root.reload()
        }
    }

    function toggleSource(sourceId, enable) {
        if (root.sourcesBridge && root.sourcesBridge.setSourceEnabled) {
            root.sourcesBridge.setSourceEnabled(sourceId, enable)
        } else {
            if (enable && root.bridge && root.bridge.enableSource) root.bridge.enableSource(sourceId)
            else if (!enable && root.bridge && root.bridge.disableSource) root.bridge.disableSource(sourceId)
        }
        root.reload()
    }

    function scanSource(sourceId) {
        if (root.sourcesBridge && root.sourcesBridge.scanSource) root.sourcesBridge.scanSource(sourceId)
        else if (root.bridge && root.bridge.scanSource) root.bridge.scanSource(sourceId)
    }

    function cancelScan(sourceId) {
        if (root.sourcesBridge && root.sourcesBridge.cancelSourceScan) root.sourcesBridge.cancelSourceScan(sourceId)
        else if (root.bridge && root.bridge.cancelSourceScan) root.bridge.cancelSourceScan(sourceId)
    }

    function scanAll() {
        root._scanAllActive = true
        root._scanAllLabel = "Cancelar todo"
        if (root.sourcesBridge && root.sourcesBridge.scanAllSources) {
            root.sourcesBridge.scanAllSources()
        }
        for (var i = 0; i < root._sources.length; i++) {
            root.scanSource(root._sources[i].id || root._sources[i].source_id || 0)
        }
    }

    function cancelAllScans() {
        root._scanAllActive = false
        root._scanAllLabel = "Escanear todo"
        for (var i = 0; i < root._sources.length; i++) {
            root.cancelScan(root._sources[i].id || root._sources[i].source_id || 0)
        }
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

                Text {
                    text: root._sources.length > 0 ? root._sources.length + " fuente(s)" : ""
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                    visible: text !== ""
                }

                Item { Layout.fillWidth: true }

                MichiButton {
                    text: root._scanAllLabel
                    variant: "ghost"
                    Accessible.name: root._scanAllActive ? "Cancelar todos los escaneos" : "Escanear todas las fuentes"
                    onClicked: root._scanAllActive ? root.cancelAllScans() : root.scanAll()
                }
                MichiButton {
                    text: "Añadir fuente"
                    variant: "primary"
                    Accessible.name: "Añadir nueva fuente de música"
                    onClicked: addDialog.open()
                }
                MichiButton {
                    text: "Refrescar"
                    variant: "ghost"
                    Accessible.name: "Refrescar lista de fuentes"
                    onClicked: root.reload()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 24
            color: MichiTheme.colors.errorSurface
            visible: root._errorState
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                Text {
                    text: root._errorMessage
                    color: MichiTheme.colors.error
                    font.pixelSize: MichiTheme.typography.metaSize
                    Accessible.name: "Error: " + root._errorMessage
                }
            }
        }

        Loader {
            Layout.fillWidth: true; Layout.fillHeight: true
            active: root.pageState === SourcesPage.LOADING
            sourceComponent: Item {
                BusyIndicator {
                    anchors.centerIn: parent
                    running: true
                    Accessible.name: "Cargando fuentes"
                }
            }
        }

        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            visible: root.pageState === SourcesPage.READY
            model: root._sources
            clip: true; boundsBehavior: Flickable.StopAtBounds
            spacing: MichiTheme.spacing.xs
            objectName: "sources.list"
            Accessible.name: "Lista de fuentes de música"

            ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

            delegate: SourceCard {
                width: parent.width
                sourceId: modelData.id || modelData.source_id || 0
                sourceName: modelData.name || modelData.path || ""
                sourcePath: modelData.path || ""
                sourceType: modelData.source_type || "local"
                enabled: modelData.enabled !== false
                status: modelData.status || modelData.error || ""
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
                    confirmDialog.sourceName = sourceName
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
                    if (root.bridge && root.bridge.setSourcePriority)
                        root.bridge.setSourcePriority(sourceId, newPriority)
                }
                onWatchModeToggled: function(enable) {
                    if (root.bridge && root.bridge.setSourceWatchMode)
                        root.bridge.setSourceWatchMode(sourceId, enable)
                }
                onExclusionsRequested: {
                    if (typeof navigationBridge !== "undefined")
                        navigationBridge.navigateWithParams("library.source_exclusions", {source_id: sourceId})
                }
                Accessible.name: "Fuente: " + sourceName
            }
        }

        Loader {
            Layout.fillWidth: true; Layout.fillHeight: true
            active: root.pageState === SourcesPage.EMPTY
            sourceComponent: LibraryEmptyState {
                title: "No hay fuentes configuradas"
                message: "Añade carpetas con música para empezar a construir tu biblioteca"
                actionText: "Añadir fuente"
                Accessible.name: "No hay fuentes configuradas"
                onActionRequested: addDialog.open()
            }
        }

        Loader {
            Layout.fillWidth: true; Layout.fillHeight: true
            active: root.pageState === SourcesPage.ERROR
            sourceComponent: LibraryErrorState {
                title: "Error al cargar fuentes"
                message: root._errorMessage || "No se pudieron cargar las fuentes de música"
                Accessible.name: "Error al cargar fuentes"
                onActionRequested: root.reload()
            }
        }
    }

    FolderDialog {
        id: addDialog
        title: "Seleccionar carpeta de música"
        objectName: "sources.addFolderDialog"
        Accessible.name: "Diálogo para seleccionar carpeta de música"
        onAccepted: {
            var folderPath = selectedFolder.toLocalFile()
            root.addSource(folderPath)
        }
    }

    SourceEditorDialog {
        id: editDialog
        bridge: root.sourcesBridge || root.bridge
        objectName: "sources.editDialog"
        Accessible.name: "Diálogo de edición de fuente"
        onAccepted: {
            root.editSource(editDialog.sourceId, editDialog.getData())
        }
    }

    Popup {
        id: confirmDialog
        property int sourceId: 0
        property string sourceName: ""
        modal: true
        focus: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3
        width: 320
        objectName: "sources.confirmRemoveDialog"
        Accessible.name: "Confirmar eliminación de fuente"
        Accessible.role: Accessible.Dialog

        Column {
            spacing: MichiTheme.spacing.md
            padding: MichiTheme.spacing.lg

            Label {
                text: "Eliminar fuente"
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                font.weight: MichiTheme.typography.weightSemiBold
                color: MichiTheme.colors.textPrimary
                Accessible.name: "Eliminar fuente"
            }

            Label {
                text: "¿Eliminar \"" + confirmDialog.sourceName + "\" de la biblioteca?"
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.bodySize
                wrapMode: Text.WordWrap
                width: parent.width
                Accessible.name: text
            }

            Label {
                text: "Los archivos no se eliminarán del disco."
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                wrapMode: Text.WordWrap
                width: parent.width
            }

            Row {
                spacing: MichiTheme.spacing.sm
                anchors.horizontalCenter: parent.horizontalCenter
                MichiButton {
                    text: "Eliminar"
                    variant: "danger"
                    Accessible.name: "Confirmar eliminación"
                    onClicked: {
                        root.removeSource(confirmDialog.sourceId)
                        confirmDialog.close()
                    }
                }
                MichiButton {
                    text: "Cancelar"
                    variant: "ghost"
                    Accessible.name: "Cancelar eliminación"
                    onClicked: confirmDialog.close()
                }
            }
        }
    }
}
