import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"
import "../../materials"

Item {
    objectName: "historyPage_control"
    id: root
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: "Historial"

    property var bridge: typeof historyBridge !== "undefined" ? historyBridge : null
    property string _viewMode: "timeline"
    property string _state: "LOADING"
    property string _statusMsg: ""
    property int _currentPage: 0
    property int _pageSize: 50
    property int _totalCount: 0
    property var _events: []
    property bool _filtered: false
    property string _artistFilter: ""
    property string _albumFilter: ""
    property string _deviceFilter: ""
    property string _searchText: ""
    property bool _dateRangeEnabled: false
    property int _dateFrom: 0
    property int _dateTo: 0

    PageStateManager {
        id: pageState
        route: "history"
        active: true
        onScrollYChanged: pageState.save()
        onSearchTextChanged: pageState.save()
        onFilterStateChanged: pageState.save()
    }

    function refresh() {
        if (!root.bridge) { root._state = "ERROR"; return }
        root._state = "LOADING"
        if (typeof root.bridge.refresh !== "undefined")
            root.bridge.refresh()
        root._loadPage()
    }

    function _loadPage() {
        if (!root.bridge || !root.bridge.historyQueryService ||
            typeof root.bridge.historyQueryService.fetchHistory === "undefined") {
            root._state = "ERROR"
            return
        }
        var filters = {}
        if (root._artistFilter) filters.artist = root._artistFilter
        if (root._albumFilter) filters.album = root._albumFilter
        if (root._deviceFilter) filters.device = root._deviceFilter
        if (root._searchText) filters.search = root._searchText
        if (root._dateRangeEnabled) {
            filters.date_from = root._dateFrom
            filters.date_to = root._dateTo
        }
        var result = root.bridge.historyQueryService.fetchHistory(
            root._currentPage * root._pageSize, root._pageSize, filters)
        root._events = result || []
        root._totalCount = root.bridge.historyCount
        root._state = root._events.length > 0 ? "READY" : "EMPTY"
        root._filtered = root._artistFilter !== "" || root._albumFilter !== "" ||
                         root._deviceFilter !== "" || root._searchText !== ""
    }

    function removeItem(trackId) {
        if (root.bridge && typeof root.bridge.removeHistoryItem !== "undefined") {
            var result = root.bridge.removeHistoryItem(String(trackId))
            if (result && result.ok) root._statusMsg = "Registro eliminado"
            else root._statusMsg = result && result.error ? "Error: " + result.error : "Error al eliminar"
            root._loadPage()
        }
    }

    function removeEvent(eventId) {
        if (root.bridge && typeof root.bridge.removeHistoryEvent !== "undefined") {
            var result = root.bridge.removeHistoryEvent(String(eventId))
            if (result && result.ok) root._statusMsg = "Evento eliminado"
            else root._statusMsg = result && result.error ? "Error: " + result.error : "Error al eliminar evento"
            root._loadPage()
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

    function clearFiltered() {
        if (!root.bridge || !root.bridge.historyQueryService ||
            typeof root.bridge.historyQueryService.clearFilteredHistory === "undefined") return
        var filters = {}
        if (root._artistFilter) filters.artist = root._artistFilter
        if (root._albumFilter) filters.album = root._albumFilter
        if (root._deviceFilter) filters.device = root._deviceFilter
        if (root._searchText) filters.search = root._searchText
        var result = root.bridge.historyQueryService.clearFilteredHistory(filters)
        if (result && result.ok) root._statusMsg = "Registros filtrados eliminados"
        else root._statusMsg = result && result.error ? "Error: " + result.error : "Error al eliminar filtrados"
        root.refresh()
    }

    function playEvent(trackId) {
        if (root.bridge && typeof root.bridge.playHistoryItem !== "undefined")
            root.bridge.playHistoryItem(String(trackId))
    }

    function openTrack(trackId) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigateWithParams("track_detail", {trackId: trackId})
    }

    function openAlbum(trackId) {
        if (typeof navigationBridge !== "undefined" && navigationBridge)
            navigationBridge.navigateWithParams("album_detail", {trackId: trackId})
    }

    function addToQueue(trackId) {
        if (typeof actionRegistry !== "undefined" && actionRegistry &&
            typeof actionRegistry.execute !== "undefined")
            actionRegistry.execute("track_add_to_queue")
    }

    function applyFilters() {
        root._currentPage = 0
        root._loadPage()
    }

    function nextPage() {
        if ((root._currentPage + 1) * root._pageSize < root._totalCount) {
            root._currentPage++
            root._loadPage()
        }
    }

    function prevPage() {
        if (root._currentPage > 0) {
            root._currentPage--
            root._loadPage()
        }
    }

    function goToPage(page) {
        root._currentPage = Math.max(0, Math.min(page, Math.ceil(root._totalCount / root._pageSize) - 1))
        root._loadPage()
    }

    function openExportDialog() {
        exportDialog.open()
    }

    function openRetentionDialog() {
        retentionDialog.open()
    }

    function openStatistics() {
        statisticsDrawer.open()
    }

    Component.onCompleted: root.refresh()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: MichiTheme.spacing.sm
        spacing: MichiTheme.spacing.sm

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: "Historial"
                font.pixelSize: MichiTheme.typography.sectionTitleSize
                color: MichiTheme.colors.textPrimary
                font.weight: MichiTheme.typography.weightSemiBold
            }
            Item { Layout.fillWidth: true }
            Label {
                id: countLabel
                text: root.bridge ? root._totalCount + " registros" : ""
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
            }
            MichiButton {
                id: statsBtn
                text: "Estadísticas"
                variant: "ghost"
                activeFocusOnTab: true
                KeyNavigation.tab: viewToggleBtn
                KeyNavigation.backtab: countLabel
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.openStatistics()
            }

            MichiButton {
                id: viewToggleBtn
                text: root._viewMode === "timeline" ? "Vista tabla" : "Vista línea"
                variant: "ghost"
                activeFocusOnTab: true
                KeyNavigation.tab: retentionBtn
                KeyNavigation.backtab: statsBtn
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root._viewMode = root._viewMode === "timeline" ? "table" : "timeline"
            }
            MichiButton {
                id: retentionBtn
                text: "Retención"
                variant: "ghost"
                activeFocusOnTab: true
                KeyNavigation.tab: clearFilteredBtn
                KeyNavigation.backtab: viewToggleBtn
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.openRetentionDialog()
            }
            MichiButton {
                id: clearFilteredBtn
                text: "Limpiar filtrados"
                variant: "danger"
                visible: root._filtered
                activeFocusOnTab: true
                KeyNavigation.tab: clearAllBtn
                KeyNavigation.backtab: retentionBtn
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.clearFiltered()
            }
            MichiButton {
                id: clearAllBtn
                text: "Limpiar todo"
                variant: "danger"
                activeFocusOnTab: true
                KeyNavigation.tab: exportBtn
                KeyNavigation.backtab: clearFilteredBtn
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: confirmClearDialog.open()
            }
            MichiButton {
                id: exportBtn
                text: "Exportar"
                variant: "ghost"
                activeFocusOnTab: true
                KeyNavigation.backtab: clearAllBtn
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.openExportDialog()
            }
        }

        HistoryFilterBar {
            id: filterBar
            Layout.fillWidth: true
            onFiltersChanged: {
                root._artistFilter = filterBar.artistFilter
                root._albumFilter = filterBar.albumFilter
                root._deviceFilter = filterBar.deviceFilter
                root._searchText = filterBar.searchText
                root._dateRangeEnabled = filterBar.dateRangeEnabled
                root._dateFrom = filterBar.dateFrom
                root._dateTo = filterBar.dateTo
                root.applyFilters()
            }
            onClearFilters: {
                root._artistFilter = ""
                root._albumFilter = ""
                root._deviceFilter = ""
                root._searchText = ""
                root._dateRangeEnabled = false
                root._dateFrom = 0
                root._dateTo = 0
                root.applyFilters()
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            LoadingState {
                anchors.centerIn: parent
                visible: root._state === "LOADING"
                title: "Cargando historial"
                message: "Obteniendo registros de reproducción..."
            }

            EmptyState {
                anchors.centerIn: parent
                visible: root._state === "EMPTY"
                iconText: ""
                title: "Sin historial"
                subtitle: root._filtered ? "No hay registros que coincidan con los filtros actuales."
                                          : "Aún no hay registros de reproducción. Reproduce música para empezar."
                actionText: root._filtered ? "Limpiar filtros" : ""
                showAction: root._filtered
                onActionClicked: filterBar.reset()
            }

            ErrorState {
                anchors.centerIn: parent
                visible: root._state === "ERROR"
                title: "Error al cargar historial"
                message: !root.bridge ? "El servicio de historial no está disponible."
                                      : "No se pudieron cargar los registros. Verifica la conexión e intenta de nuevo."
                showRetry: true
                onRetryRequested: root.refresh()
            }

            HistoryTimeline {
                id: timelineView
                anchors.fill: parent
                model: root._events
                bridge: root.bridge
                visible: root._state === "READY" && root._viewMode === "timeline"
                activeFocusOnTab: true
                onPlayRequested: function(trackId, title) { root.playEvent(trackId) }
                onRemoveRequested: function(eventId, trackId) {
                    if (eventId) root.removeEvent(eventId)
                    else root.removeItem(trackId)
                }
                onOpenTrackRequested: function(trackId) { root.openTrack(trackId) }
                onOpenAlbumRequested: function(trackId) { root.openAlbum(trackId) }
                onAddToQueueRequested: function(trackId) { root.addToQueue(trackId) }
            }

            HistoryTable {
                id: tableView
                anchors.fill: parent
                model: root._events
                bridge: root.bridge
                visible: root._state === "READY" && root._viewMode === "table"
                activeFocusOnTab: true
                onPlayRequested: function(trackId, title) { root.playEvent(trackId) }
                onRemoveRequested: function(trackId) { root.removeItem(trackId) }
                onOpenTrackRequested: function(trackId) { root.openTrack(trackId) }
                onOpenAlbumRequested: function(trackId) { root.openAlbum(trackId) }
                onAddToQueueRequested: function(trackId) { root.addToQueue(trackId) }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: MichiTheme.rowHeightCompact
            visible: root._state === "READY" && root._totalCount > root._pageSize

            MichiButton {
                text: "Anterior"
                variant: "ghost"
                enabled: root._currentPage > 0
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.prevPage()
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "Página " + (root._currentPage + 1) + " de " +
                      Math.max(1, Math.ceil(root._totalCount / root._pageSize))
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { Layout.fillWidth: true }

            MichiButton {
                text: "Siguiente"
                variant: "ghost"
                enabled: (root._currentPage + 1) * root._pageSize < root._totalCount
                activeFocusOnTab: true
                Keys.onReturnPressed: onClicked()
                Keys.onSpacePressed: onClicked()
                onClicked: root.nextPage()
            }
        }

        Text {
            id: statusMsg
            text: root._statusMsg
            color: root._statusMsg.indexOf("Error") >= 0 ? MichiTheme.colors.error : MichiTheme.colors.textSecondary
            font.pixelSize: MichiTheme.typography.metaSize
            Layout.fillWidth: true
            visible: text !== ""
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

    HistoryExportDialog {
        id: exportDialog
        bridge: root.bridge
        onExportCompleted: function(path, count) {
            root._statusMsg = "Exportadas " + count + " entradas a " + path
        }
        onExportCancelled: {
            root._statusMsg = "Exportación cancelada"
        }
    }

    HistoryStatisticsPage {
        id: statisticsDrawer
        bridge: root.bridge
    }

    Dialog {
        id: confirmClearDialog
        title: "Limpiar historial"
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 3
        closePolicy: Popup.CloseOnEscape
        Text {
            text: "¿Eliminar todo el historial de reproducción? Esta acción no se puede deshacer."
            color: MichiTheme.colors.textPrimary
            font.pixelSize: MichiTheme.typography.bodySize
            wrapMode: Text.WordWrap
            width: 300
        }
        onAccepted: { root.clearAll(); forceActiveFocus() }
        onRejected: { forceActiveFocus() }
    }

    Keys.onEscapePressed: {
        if (exportDialog.opened) exportDialog.close()
        else if (retentionDialog.opened) retentionDialog.close()
        else if (statisticsDrawer.opened) statisticsDrawer.close()
        else if (confirmClearDialog.opened) confirmClearDialog.close()
    }
}
