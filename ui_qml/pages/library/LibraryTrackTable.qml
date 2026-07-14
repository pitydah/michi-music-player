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
    property bool _fetchingMore: false
    property bool _shiftPressed: false
    property var _selectedIds: []
    property int _lastClickedIndex: -1

    signal trackPlayRequested(int trackId)
    signal trackContextMenuRequested(int trackId, int x, int y)

    Column {
        anchors.fill: parent; spacing: 0

        LibraryTrackHeader {
            id: header
            width: parent.width
            bridge: root.bridge
            sortKey: root.bridge ? root.bridge.activeSortKey : "title"
            sortAsc: root.bridge ? root.bridge.activeSortAscending : true
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

            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Shift) root._shiftPressed = true
                if (event.key === Qt.Key_Escape) { root._selectedIds = []; selectionModel.clear(); selectionBar.visible = false }
                if (event.key === Qt.Key_A && (event.modifiers & Qt.ControlModifier)) {
                    selectAll()
                }
            }

            Keys.onReleased: function(event) {
                if (event.key === Qt.Key_Shift) root._shiftPressed = false
            }

            onContentYChanged: {
                if (!root.trackModel || root._fetchingMore || !root.trackModel.hasMore) return
                if (contentY + height >= contentHeight - 400) {
                    root._fetchingMore = true
                    root.trackModel.fetchMore()
                    root._fetchingMore = false
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
                isSelected: root._selectedIds.indexOf(model.trackId) !== -1
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
                    if (root.actionRegistry) {
                        contextMenu.x = mx; contextMenu.y = my
                        contextMenu.open()
                    }
                }

                onSelectionToggled: function(id, ctrl, shift) {
                    if (ctrl && shift) {
                        var start = Math.min(root._lastClickedIndex, index)
                        var end = Math.max(root._lastClickedIndex, index)
                        for (var i = start; i <= end; i++) {
                            var tid = root.trackModel.data(root.trackModel.index(i, 0), TrackIdRole)
                            if (root._selectedIds.indexOf(tid) === -1)
                                root._selectedIds.push(tid)
                        }
                    } else if (ctrl) {
                        var idx = root._selectedIds.indexOf(id)
                        if (idx !== -1) root._selectedIds.splice(idx, 1)
                        else root._selectedIds.push(id)
                    } else {
                        root._selectedIds = [id]
                    }
                    root._lastClickedIndex = index
                    updateSelectionBar()
                }
            }
        }

        Row {
            id: loadMoreBar
            width: parent.width; height: 28; spacing: MichiTheme.spacing.sm
            leftPadding: MichiTheme.spacing.md
            visible: root.trackModel && root.trackModel.hasMore

            Text {
                text: "Mostrando " + (root.trackModel ? root.trackModel.count : 0) + " de " + (root.trackModel ? root.trackModel.totalCount : 0)
                color: MichiTheme.colors.textMuted
                font.pixelSize: MichiTheme.typography.metaSize
                anchors.verticalCenter: parent.verticalCenter
            }

            MichiButton {
                text: "Cargar más"; variant: "ghost"; height: 24
                onClicked: {
                    if (root.trackModel && root.trackModel.hasMore && !root._fetchingMore) {
                        root._fetchingMore = true
                        root.trackModel.fetchMore()
                        root._fetchingMore = false
                    }
                }
            }
        }

        Item {
            width: parent.width
            height: parent.height > 0 ? parent.height - listView.height - header.height - loadMoreBar.height : 0
            visible: root.trackModel && root.trackModel.count === 0 && root.trackModel.initialized

            LibraryEmptyState {
                anchors.centerIn: parent
                title: "Sin resultados"
                message: "No se encontraron canciones con los filtros actuales."
                actionText: "Limpiar filtros"
                onActionRequested: { if (typeof libraryBridge !== "undefined") libraryBridge.clearFilters() }
            }
        }
    }

    LibrarySortMenu {
        id: contextMenu
        bridge: root.bridge
    }

    function selectAll() {
        root._selectedIds = []
        if (root.trackModel) {
            for (var i = 0; i < root.trackModel.count; i++) {
                root._selectedIds.push(root.trackModel.data(root.trackModel.index(i, 0), TrackIdRole))
            }
        }
        updateSelectionBar()
    }

    function updateSelectionBar() {
        selectionBar.selectedCount = root._selectedIds.length
        selectionBar.selectedIds = root._selectedIds
        selectionBar.visible = root._selectedIds.length > 0
    }

    function clearSelection() {
        root._selectedIds = []
        selectionBar.visible = false
    }

    function formatDuration(secs) {
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return m + ":" + (s < 10 ? "0" : "") + s
    }
}
