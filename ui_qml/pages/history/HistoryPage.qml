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
    property string _state: "LOADING"
    property string _statusMsg: ""
    property string _searchText: ""
    property string _artistFilter: ""
    property string _albumFilter: ""
    property string _deviceFilter: ""
    property bool _dateRangeEnabled: false
    property int _dateFrom: 0
    property int _dateTo: 0
    property int _currentPage: 0
    property int _pageSize: 50
    property var _events: []

    objectName: "history.page"
    focus: true

    Accessible.role: Accessible.Panel
    Accessible.name: "Historial"
    Accessible.description: "Historial de reproducción musical"

    function refresh() {
        root._state = "LOADING"
        if (root.bridge && typeof root.bridge.refresh !== "undefined")
            root.bridge.refresh()
        root._loadPage()
    }

    function _loadPage() {
        if (!root.bridge) {
            root._state = "READY"
            root._events = []
            return
        }
        try {
            var data = root.bridge.historyModel
            if (data && typeof data === "object") {
                var items = []
                if (typeof data.length !== "undefined") {
                    items = data
                } else if (typeof data.get === "function") {
                    var cnt = data.count || 0
                    for (var i = 0; i < cnt; i++) items.push(data.get(i))
                }
                root._events = root._filterEvents(items)
                root._state = root._events.length > 0 ? "READY" : "EMPTY"
            } else {
                root._events = []
                root._state = "READY"
            }
        } catch (e) {
            root._events = []
            root._state = "ERROR"
            root._statusMsg = "Error al cargar historial"
        }
    }

    function _filterEvents(items) {
        var q = root._searchText.toLowerCase()
        return items.filter(function(e) {
            if (q && (e.title || "").toLowerCase().indexOf(q) < 0 &&
                (e.artist || "").toLowerCase().indexOf(q) < 0 &&
                (e.album || "").toLowerCase().indexOf(q) < 0)
                return false
            if (root._artistFilter && (e.artist || "").toLowerCase().indexOf(root._artistFilter.toLowerCase()) < 0)
                return false
            if (root._albumFilter && (e.album || "").toLowerCase().indexOf(root._albumFilter.toLowerCase()) < 0)
                return false
            if (root._deviceFilter && (e.device || "").toLowerCase().indexOf(root._deviceFilter.toLowerCase()) < 0)
                return false
            if (root._dateRangeEnabled && root._dateFrom > 0 && root._dateTo > 0) {
                var ts = e.playedAt || 0
                if (ts < root._dateFrom || ts > root._dateTo) return false
            }
            return true
        })
    }

    function removeItem(eventId) {
        if (root.bridge && typeof root.bridge.removeHistoryEvent !== "undefined") {
            var result = root.bridge.removeHistoryEvent(String(eventId))
            if (result && result.ok) {
                root._statusMsg = "Registro eliminado"
                root.refresh()
            } else {
                root._statusMsg = result && result.error ? "Error: " + result.error : "Error al eliminar"
            }
        }
    }

    function clearAll() {
        if (root.bridge && typeof root.bridge.clearHistory !== "undefined") {
            var result = root.bridge.clearHistory()
            if (result && result.ok) {
                root._statusMsg = "Historial limpiado"
                root._events = []
                root._state = "EMPTY"
            } else {
                root._statusMsg = result && result.error ? "Error: " + result.error : "Error al limpiar"
            }
        }
    }

    function clearFiltered() {
        var filtered = root._filterEvents(root.bridge && root.bridge.historyModel || [])
        for (var i = 0; i < filtered.length; i++) {
            root.removeItem(filtered[i].eventId || filtered[i].id || 0)
        }
        root._statusMsg = "Filtrados eliminados: " + filtered.length
        root.refresh()
    }

    function playEvent(eventId, trackId) {
        if (root.bridge && typeof root.bridge.playHistoryItem !== "undefined") {
            var result = root.bridge.playHistoryItem(String(trackId))
            if (result && result.ok) root._statusMsg = "Reproduciendo"
            else root._statusMsg = result && result.error ? "Error: " + result.error : "Error al reproducir"
        }
    }

    function queueEvent(eventId, trackId) {
        if (root.bridge && root.bridge.playbackBridge &&
            typeof root.bridge.playbackBridge.enqueue !== "undefined") {
            root.bridge.playbackBridge.enqueue(trackId)
            root._statusMsg = "Agregado a la cola"
        }
    }

    function openTrack(trackId) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigateWithParams("track_detail", {trackId: trackId})
    }

    function openAlbum(albumKey) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigateWithParams("album_detail", {albumKey: albumKey})
    }

    Component.onCompleted: root.refresh()

    Loader {
        anchors.fill: parent
        active: !root.bridge
        sourceComponent: UnavailableState {
            title: "Historial no disponible"
            message: "El servicio de historial no está disponible en este momento."
            explanation: "History Bridge no está configurado o el módulo no está activo."
            objectName: "history.unavailableState"
        }
    }

    FocusScope {
        id: focusScope
        visible: !!root.bridge
        anchors.fill: parent
        objectName: "history.focusScope"
        activeFocusOnTab: true

        Keys.onEscapePressed: {
            if (confirmClearDialog.opened) confirmClearDialog.close()
            if (retentionDialog.opened) retentionDialog.close()
            if (exportDialog.opened) exportDialog.close()
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.md

            RowLayout {
                Layout.fillWidth: true
                objectName: "history.toolbar"

                Label {
                    id: historyTitle
                    text: "Historial"
                    font.pixelSize: MichiTheme.typography.sectionTitleSize
                    color: MichiTheme.colors.textPrimary
                    font.weight: MichiTheme.typography.weightSemiBold
                    Accessible.role: Accessible.Heading
                    Accessible.name: "Historial de reproducción"
                }

                Item { Layout.fillWidth: true }

                Label {
                    text: root.bridge ? root.bridge.historyCount + " registros" : ""
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    Accessible.role: Accessible.StatusBar
                    Accessible.name: text
                }

                MichiButton {
                    id: clearFilteredBtn
                    text: "Limpiar filtrados"
                    variant: "ghost"
                    onClicked: root.clearFiltered()
                    objectName: "history.toolbar.clearFiltered"
                    Accessible.name: "Limpiar registros filtrados"
                    KeyNavigation.tab: viewToggleBtn
                }

                MichiButton {
                    id: viewToggleBtn
                    text: "Vista"
                    variant: "ghost"
                    onClicked: root._viewMode = root._viewMode === "timeline" ? "table" : "timeline"
                    objectName: "history.toolbar.viewToggle"
                    Accessible.name: "Cambiar vista: " + (root._viewMode === "timeline" ? "tabla" : "línea de tiempo")
                    KeyNavigation.tab: retentionBtn
                    KeyNavigation.backtab: clearFilteredBtn
                }

                MichiButton {
                    id: retentionBtn
                    text: "Retención"
                    variant: "ghost"
                    onClicked: retentionDialog.open()
                    objectName: "history.toolbar.retention"
                    Accessible.name: "Configurar retención de historial"
                    KeyNavigation.tab: exportBtn
                    KeyNavigation.backtab: viewToggleBtn
                }

                MichiButton {
                    id: exportBtn
                    text: "Exportar"
                    variant: "ghost"
                    onClicked: exportDialog.open()
                    objectName: "history.toolbar.export"
                    Accessible.name: "Exportar historial"
                    KeyNavigation.tab: clearBtn
                    KeyNavigation.backtab: retentionBtn
                }

                MichiButton {
                    id: clearBtn
                    text: "Limpiar todo"
                    variant: "danger"
                    onClicked: confirmClearDialog.open()
                    objectName: "history.toolbar.clearAll"
                    Accessible.name: "Limpiar todo el historial"
                    Accessible.description: "Elimina todos los registros del historial de reproducción"
                    KeyNavigation.backtab: exportBtn
                }
            }

            HistoryFilterBar {
                id: filterBar
                Layout.fillWidth: true
                objectName: "history.filterBar"
                Accessible.name: "Barra de filtros de historial"
                searchText: root._searchText
                artistFilter: root._artistFilter
                albumFilter: root._albumFilter
                deviceFilter: root._deviceFilter
                dateRangeEnabled: root._dateRangeEnabled
                dateFrom: root._dateFrom
                dateTo: root._dateTo
                onSearchTextChanged: { root._searchText = text; root._loadPage() }
                onArtistFilterChanged: { root._artistFilter = text; root._loadPage() }
                onAlbumFilterChanged: { root._albumFilter = text; root._loadPage() }
                onDeviceFilterChanged: { root._deviceFilter = text; root._loadPage() }
                onDateRangeEnabledChanged: { root._dateRangeEnabled = enabled; root._loadPage() }
                onDateFromChanged: { root._dateFrom = ts; root._loadPage() }
                onDateToChanged: { root._dateTo = ts; root._loadPage() }
                onClearFilters: {
                    root._searchText = ""; root._artistFilter = ""; root._albumFilter = ""
                    root._deviceFilter = ""; root._dateRangeEnabled = false
                    root._dateFrom = 0; root._dateTo = 0
                    root._loadPage()
                }
                KeyNavigation.tab: statsBar
                KeyNavigation.backtab: clearBtn
            }

            HistoryStats {
                id: statsBar
                Layout.fillWidth: true
                totalCount: root._events.length
                objectName: "history.statsBar"
                Accessible.name: "Estadísticas de historial"
                KeyNavigation.tab: viewContainer
                KeyNavigation.backtab: filterBar
            }

            Item {
                id: viewContainer
                Layout.fillWidth: true
                Layout.fillHeight: true
                objectName: "history.viewContainer"

                LoadingState {
                    anchors.fill: parent
                    visible: root._state === "LOADING"
                    title: "Cargando historial"
                    objectName: "history.loadingState"
                }

                ErrorState {
                    anchors.fill: parent
                    visible: root._state === "ERROR"
                    title: "Error al cargar historial"
                    message: root._statusMsg
                    objectName: "history.errorState"
                    onRetryRequested: root.refresh()
                }

                EmptyState {
                    anchors.centerIn: parent
                    visible: root._state === "EMPTY"
                    title: "Sin registros"
                    subtitle: "No hay registros de reproducción en el historial."
                    iconText: "\uD83C\uDFB5"
                    objectName: "history.emptyState"
                }

                HistoryTimeline {
                    id: timelineView
                    anchors.fill: parent
                    visible: root._viewMode === "timeline" && root._state === "READY"
                    model: root._events
                    bridge: root.bridge
                    objectName: "history.timelineView"
                    onPlayRequested: function(eventId, trackId, title) {
                        root.playEvent(eventId, trackId)
                    }
                    onQueueRequested: function(eventId, trackId) {
                        root.queueEvent(eventId, trackId)
                    }
                    onOpenTrackRequested: function(trackId) {
                        root.openTrack(trackId)
                    }
                    onOpenAlbumRequested: function(albumKey) {
                        root.openAlbum(albumKey)
                    }
                    onRemoveRequested: function(eventId) {
                        root.removeItem(eventId)
                    }
                }

                HistoryTable {
                    id: tableView
                    anchors.fill: parent
                    visible: root._viewMode === "table" && root._state === "READY"
                    model: root._events
                    bridge: root.bridge
                    objectName: "history.tableView"
                    onPlayRequested: function(eventId, trackId, title) {
                        root.playEvent(eventId, trackId)
                    }
                    onQueueRequested: function(eventId, trackId) {
                        root.queueEvent(eventId, trackId)
                    }
                    onOpenTrackRequested: function(trackId) {
                        root.openTrack(trackId)
                    }
                    onOpenAlbumRequested: function(albumKey) {
                        root.openAlbum(albumKey)
                    }
                    onRemoveRequested: function(eventId) {
                        root.removeItem(eventId)
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: root._state === "READY" && root._events.length > root._pageSize
                spacing: MichiTheme.spacing.sm

                Item { Layout.fillWidth: true }

                MichiButton {
                    text: "< Anterior"
                    variant: "ghost"
                    enabled: root._currentPage > 0
                    onClicked: { root._currentPage--; root._loadPage() }
                    objectName: "history.pagination.prev"
                    Accessible.name: "Página anterior"
                }

                Label {
                    text: "Página " + (root._currentPage + 1)
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                    anchors.verticalCenter: parent.verticalCenter
                }

                MichiButton {
                    text: "Siguiente >"
                    variant: "ghost"
                    enabled: (root._currentPage + 1) * root._pageSize < root._events.length
                    onClicked: { root._currentPage++; root._loadPage() }
                    objectName: "history.pagination.next"
                    Accessible.name: "Página siguiente"
                }

                Item { Layout.fillWidth: true }
            }

            Text {
                text: root._statusMsg
                color: root._statusMsg.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                Layout.fillWidth: true
                visible: text !== ""
                objectName: "history.statusMessage"
                Accessible.role: Accessible.StatusBar
                Accessible.name: root._statusMsg
            }
        }
    }

    HistoryRetentionDialog {
        id: retentionDialog
        bridge: root.bridge
        objectName: "history.retentionDialog"
        onRetentionApplied: function(count) {
            root._statusMsg = "Retención aplicada: " + count + " registros eliminados"
            root.refresh()
        }
    }

    HistoryExportDialog {
        id: exportDialog
        bridge: root.bridge
        objectName: "history.exportDialog"
        onExportCompleted: function(path, count) {
            root._statusMsg = "Exportación completada: " + count + " registros a " + path
        }
        onExportCancelled: {
            root._statusMsg = "Exportación cancelada"
        }
    }

    Dialog {
        id: confirmClearDialog
        title: "Limpiar historial"
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3
        objectName: "history.confirmClearDialog"

        Accessible.role: Accessible.Dialog
        Accessible.name: "Confirmar limpieza de historial"
        Accessible.description: "Diálogo de confirmación para eliminar todo el historial"

        Text {
            text: "¿Eliminar todo el historial de reproducción? Esta acción no se puede deshacer."
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            width: 300
        }

        Keys.onEscapePressed: confirmClearDialog.close()
        onAccepted: root.clearAll()
        onClosed: {
            if (confirmClearDialog.result === Dialog.Rejected) {
                confirmClearDialog.close()
            }
        }
    }
}
