import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root

    property var trackModel: null
    property var bridge: null
    property var notif: null
    property var actionRegistry: null
    property var selectionController: null
    property bool _fetchingMore: false
    property bool _fetchingMore: false
    property bool _shiftPressed: false
    property int _lastClickedIndex: -1

    signal trackPlayRequested(int trackId)
    signal trackContextMenuRequested(int trackId, string title, string artist, string album)

    function getTrackId(index) {
        if (!root.trackModel) return 0
        var idx = root.trackModel.index(index, 0)
        var role = root.trackModel.TrackIdRole || 256
        return root.trackModel.data(idx, role) || 0
    }

    function getTrackData(index, roleName) {
        if (!root.trackModel || !root.trackModel.roleNames) return ""
        var roleMap = root.trackModel.roleNames()
        var role = 256
        for (var r in roleMap) {
            if (roleMap[r] === roleName) { role = parseInt(r); break }
        }
        var idx = root.trackModel.index(index, 0)
        return root.trackModel.data(idx, role) || ""
    }

    property bool _loading: root.trackModel ? !root.trackModel.initialized : true
    property bool _empty: root.trackModel && root.trackModel.initialized && root.trackModel.count === 0
    property bool _error: false

    objectName: "library.trackTable"
    Accessible.role: Accessible.Table
    Accessible.name: "Lista de canciones"

    Column {
        anchors.fill: parent; spacing: 0

        LibraryTrackHeader {
            id: header
            width: parent.width
            bridge: root.bridge
            sortKey: root.bridge ? root.bridge.activeSortKey : "title"
            sortAsc: root.bridge ? root.bridge.activeSortAscending : true
            objectName: "library.trackHeader"
        }

        Item {
            width: parent.width
            height: parent.height - header.height - loadMoreBar.height
            visible: root._loading
            anchors.centerIn: undefined

            Column {
                anchors.centerIn: parent
                spacing: MichiTheme.spacing.sm
                BusyIndicator {
                    anchors.horizontalCenter: parent.horizontalCenter
                    running: true
                    Accessible.name: "Cargando canciones"
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Cargando canciones..."
                    color: MichiTheme.colors.textMuted
                    font.pixelSize: MichiTheme.typography.metaSize
                }
            }
        }

        Item {
            width: parent.width
            height: parent.height - header.height - loadMoreBar.height
            visible: root._error

            LibraryErrorState {
                anchors.centerIn: parent
                title: "Error al cargar canciones"
                message: "No se pudieron cargar las canciones"
                actionText: "Reintentar"
                onActionRequested: {
                    if (root.trackModel) root.trackModel.refresh()
                }
            }
        }

        ListView {
            id: listView
            width: parent.width
            height: parent.height - header.height - loadMoreBar.height
            model: root.trackModel
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            cacheBuffer: 200
            focus: true
            visible: !root._loading && !root._error
            objectName: "library.trackList"
            keyNavigationWraps: false

            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Shift) root._shiftPressed = true
                if (event.key === Qt.Key_Escape) {
                    root._selectedIds = []
                    if (root.selectionController) root.selectionController.clear()
                    updateSelectionBar()
                    if (root.selectionController) root.selectionController.clear()
                    if (root.selectionController) root.selectionController.clear()
                    root._selectedIds = []
                    if (root.selectionController) root.selectionController.clear()
                    updateSelectionBar()
                }
                if (event.key === Qt.Key_A && (event.modifiers & Qt.ControlModifier)) {
                    selectAll()
                }
                if (event.key === Qt.Key_Down) {
                    incrementCurrentIndex()
                    event.accepted = true
                }
                if (event.key === Qt.Key_Up) {
                    decrementCurrentIndex()
                    event.accepted = true
                }
                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    var curIdx = listView.currentIndex
                    if (curIdx >= 0) {
                        var tid = getTrackId(curIdx)
                        if (root.bridge && root.bridge.playTrackById)
                            root.bridge.playTrackById(tid)
                    }
                    event.accepted = true
                if (event.key === Qt.Key_Down) {
                    incrementCurrentIndex()
                    event.accepted = true
                }
                if (event.key === Qt.Key_Up) {
                    decrementCurrentIndex()
                    event.accepted = true
                }
                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    var curIdx = listView.currentIndex
                    if (curIdx >= 0) {
                        var tid = getTrackId(curIdx)
                        if (root.bridge && root.bridge.playTrackById)
                            root.bridge.playTrackById(tid)
                    }
                    event.accepted = true
                }
            }

            Keys.onReleased: function(event) {
                if (event.key === Qt.Key_Shift) root._shiftPressed = false
            }

            onContentYChanged: {
                if (!root.trackModel || root.trackModel.loadingMore || !root.trackModel.hasMore) return
                if (contentY + height >= contentHeight - 400) {
                    root.trackModel.fetchMore()
                }
            }

            ScrollBar.vertical: ScrollBar {
                width: 8
                policy: ScrollBar.AsNeeded
            }

            delegate: LibraryTrackRow {
                width: parent.width
                trackId: model.trackId || 0
                trackTitle: model.title || ""
                trackArtist: model.artist || ""
                trackAlbum: model.album || ""
                trackDuration: model.duration || 0
                trackFormat: model.format || ""
                trackYear: model.year || 0
                trackGenre: model.genre || ""
                trackNumber: model.trackNumber || 0
                trackFavorite: model.favorite || false
                trackMissing: model.missing || false
                trackQuality: model.bitDepth || model.bitrate || 0
                isSelected: root._selectedIds.indexOf(model.trackId || 0) !== -1
                isSelected: root.selectionController ? root.selectionController.contains(model.trackId || 0) : false
                isSelected: root._selectedIds.indexOf(model.trackId || 0) !== -1
                isShiftPressed: root._shiftPressed
                lastClickedIndex: root._lastClickedIndex
                rowIndex: index

                onPlayClicked: {
                    if (root.bridge && root.bridge.playTrackById)
                        root.bridge.playTrackById(model.trackId || 0)
                }

                onDoubleClicked: {
                    if (root.bridge && root.bridge.playTrackById)
                        root.bridge.playTrackById(model.trackId || 0)
                }

                onRightClicked: function(mx, my) {
                    root._selectedIds = [model.trackId || 0]
                    updateSelectionBar()
                    root.trackContextMenuRequested(model.trackId || 0, model.title || "", model.artist || "", model.album || "")
                    if (root.selectionController) {
                        root.selectionController.replace([model.trackId || 0])
                    }
                    contextMenu.x = mx; contextMenu.y = my
                    contextMenu.open()
                    root._selectedIds = [model.trackId || 0]
                    updateSelectionBar()
                    root.trackContextMenuRequested(model.trackId || 0, model.title || "", model.artist || "", model.album || "")
                }

                onSelectionToggled: function(id, ctrl, shift) {
                    if (!root.selectionController) return
                    if (ctrl && shift) {
                        var visibleIds = root.trackModel ? root.trackModel.visibleIds() : []
                        root.selectionController.selectRangeByRows(root._lastClickedIndex, index, visibleIds)
                        var start = Math.min(root._lastClickedIndex, index)
                        var end = Math.max(root._lastClickedIndex, index)
                        for (var i = start; i <= end; i++) {
                            var tid = getTrackId(i)
                            if (root._selectedIds.indexOf(tid) === -1)
                                root._selectedIds.push(tid)
                        }
                    } else if (ctrl) {
                        root.selectionController.toggle(id)
                    } else {
                        root.selectionController.replace([id])
                    }
                    root._lastClickedIndex = index
                }
            }
        }

        Row {
            id: loadMoreBar
            width: parent.width; height: 28; spacing: MichiTheme.spacing.sm
            leftPadding: MichiTheme.spacing.md
            visible: root.trackModel && root.trackModel.hasMore
            objectName: "library.loadMoreBar"

            Text {
                text: "Mostrando " + (root.trackModel ? root.trackModel.count : 0) + " de " + (root.trackModel ? root.trackModel.totalCount : 0)
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
            }

            MichiButton {
                text: "Cargar más"; variant: "ghost"; height: 24
                objectName: "library.loadMoreButton"
                Accessible.name: "Cargar más canciones"
                onClicked: {
                    if (root.trackModel && root.trackModel.hasMore && !root.trackModel.loadingMore) {
                        root.trackModel.fetchMore()
                    }
                }
            }
        }

        Item {
            width: parent.width
            height: parent.height > 0 ? parent.height - listView.height - header.height - loadMoreBar.height : 0
            visible: root.trackModel && root.trackModel.initialized && root.trackModel.count === 0

            LibraryEmptyState {
                anchors.centerIn: parent
                title: "Sin resultados"
                message: "No se encontraron canciones con los filtros actuales."
                actionText: "Limpiar filtros"
                onActionRequested: { if (typeof libraryBridge !== "undefined") libraryBridge.clearFilters() }
            }
        }
    }

    function selectAll() {
        root._selectedIds = []
        if (root.trackModel) {
            for (var i = 0; i < root.trackModel.count; i++) {
                var tid = getTrackId(i)
                if (tid > 0) root._selectedIds.push(tid)
            }
        }
        updateSelectionBar()
    LibraryTrackContextMenu {
        id: contextMenu
        bridge: root.bridge
        selectionController: root.selectionController
        trackModel: root.trackModel
        objectName: "library.trackContextMenu"
    }

    function updateSelectionBar() {
        if (typeof selectionBar !== "undefined" && selectionBar) {
            selectionBar.selectedCount = root._selectedIds.length
            selectionBar.selectedIds = root._selectedIds
            selectionBar.visible = root._selectedIds.length > 0
        }
    }

    function clearSelection() {
        root._selectedIds = []
        if (typeof selectionBar !== "undefined" && selectionBar)
            selectionBar.visible = false
        if (root.selectionController) root.selectionController.clear()
    function selectAll() {
        root._selectedIds = []
        if (root.trackModel) {
            for (var i = 0; i < root.trackModel.count; i++) {
                var tid = getTrackId(i)
                if (tid > 0) root._selectedIds.push(tid)
            }
        }
        updateSelectionBar()
    }

    function updateSelectionBar() {
        if (typeof selectionBar !== "undefined" && selectionBar) {
            selectionBar.selectedCount = root._selectedIds.length
            selectionBar.selectedIds = root._selectedIds
            selectionBar.visible = root._selectedIds.length > 0
        }
    }

    function clearSelection() {
        root._selectedIds = []
        if (typeof selectionBar !== "undefined" && selectionBar)
            selectionBar.visible = false
    }

    function formatDuration(secs) {
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
