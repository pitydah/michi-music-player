import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

Item {
    id: root
    objectName: "libraryTrackTable"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Tabla de canciones de la biblioteca")

    property var trackModel: null
    property var bridge: null
    property var notif: null
    property var actionRegistry: null
    property var selectionController: null
    property bool _fetchingMore: false
    property bool _shiftPressed: false
    property var _selectedIds: []
    property int _lastClickedIndex: -1

    signal trackPlayRequested(int trackId)
    signal trackContextMenuRequested(int trackId, string title, string artist, string album, string albumKey)
    signal selectionChanged(var selectedIds)

    function getTrackId(index) {
        if (!root.trackModel || index < 0) return 0
        return root.trackModel.idAt(index) || 0
    }

    function commitSelection(ids) {
        root._selectedIds = ids.slice()
        root.selectionChanged(root._selectedIds.slice())
        if (root.selectionController) {
            if (root._selectedIds.length === 1 && root.selectionController.setSelectedId)
                root.selectionController.setSelectedId(String(root._selectedIds[0]))
            else if (root._selectedIds.length === 0 && root.selectionController.clearSelection)
                root.selectionController.clearSelection()
        }
    }

    function clearSelection() {
        root._lastClickedIndex = -1
        root.commitSelection([])
    }

    Connections {
        target: root.trackModel
        function onCountChanged() { root.clearSelection() }
    }

    function selectAllLoaded() {
        var ids = []
        if (root.trackModel) {
            for (var i = 0; i < root.trackModel.count; i++) {
                var trackId = root.getTrackId(i)
                if (trackId > 0) ids.push(trackId)
            }
        }
        root.commitSelection(ids)
    }

    function toggleSelection(id, index, ctrl, shift) {
        var ids = root._selectedIds.slice()
        if (shift && root._lastClickedIndex >= 0) {
            var start = Math.min(root._lastClickedIndex, index)
            var end = Math.max(root._lastClickedIndex, index)
            if (!ctrl) ids = []
            for (var i = start; i <= end; i++) {
                var rangeId = root.getTrackId(i)
                if (rangeId > 0 && ids.indexOf(rangeId) === -1) ids.push(rangeId)
            }
        } else if (ctrl) {
            var selectedIndex = ids.indexOf(id)
            if (selectedIndex >= 0) ids.splice(selectedIndex, 1)
            else ids.push(id)
        } else {
            ids = [id]
        }
        root._lastClickedIndex = index
        root.commitSelection(ids)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        LibraryTrackHeader {
            id: header
            Layout.fillWidth: true
            bridge: root.bridge
            sortKey: root.bridge ? root.bridge.activeSortKey : "title"
            sortAsc: root.bridge ? root.bridge.activeSortAscending : true
        }

        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.trackModel
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            cacheBuffer: 320
            focus: true
            activeFocusOnTab: true
            keyNavigationWraps: false

            Accessible.role: Accessible.List
            Accessible.name: qsTr("Lista de canciones")

            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Shift) root._shiftPressed = true
                if (event.key === Qt.Key_Escape) {
                    root.clearSelection()
                    event.accepted = true
                } else if (event.key === Qt.Key_A && (event.modifiers & Qt.ControlModifier)) {
                    root.selectAllLoaded()
                    event.accepted = true
                } else if (event.key === Qt.Key_Down) {
                    incrementCurrentIndex()
                    event.accepted = true
                } else if (event.key === Qt.Key_Up) {
                    decrementCurrentIndex()
                    event.accepted = true
                } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    var trackId = root.getTrackId(listView.currentIndex)
                    if (trackId > 0 && root.bridge && root.bridge.playTrackById)
                        root.bridge.playTrackById(trackId)
                    event.accepted = true
                } else if (event.key === Qt.Key_Space) {
                    var selectedTrackId = root.getTrackId(listView.currentIndex)
                    if (selectedTrackId > 0)
                        root.toggleSelection(selectedTrackId, listView.currentIndex,
                                             event.modifiers & Qt.ControlModifier,
                                             event.modifiers & Qt.ShiftModifier)
                    event.accepted = true
                }
            }

            Keys.onReleased: function(event) {
                if (event.key === Qt.Key_Shift) root._shiftPressed = false
            }

            onContentYChanged: {
                if (!root.trackModel || root.trackModel.loadingMore || root.trackModel.loading || !root.trackModel.hasMore)
                    return
                if (contentY + height >= contentHeight - 480)
                    root.trackModel.fetchMore()
            }

            ScrollBar.vertical: ScrollBar { width: 8; policy: ScrollBar.AsNeeded }

            delegate: LibraryTrackRow {
                width: ListView.view.width
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
                    var trackId = model.trackId || 0
                    if (root._selectedIds.indexOf(trackId) === -1)
                        root.commitSelection([trackId])
                    root.trackContextMenuRequested(trackId, model.title || "", model.artist || "",
                                                   model.album || "", model.albumKey || "")
                }
                onSelectionToggled: function(id, ctrl, shift) {
                    listView.currentIndex = index
                    root.toggleSelection(id, index, ctrl, shift)
                }
            }

            footer: Item {
                width: listView.width
                height: root.trackModel && root.trackModel.hasMore ? 46 : 0

                Row {
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.md
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("Mostrando %1 de %2").arg(root.trackModel ? root.trackModel.count : 0)
                              .arg(root.trackModel ? root.trackModel.totalCount : 0)
                        color: MichiTheme.colors.textMuted
                        font.pixelSize: MichiTheme.typography.metaSize
                    }
                    MichiButton {
                        text: root.trackModel && root.trackModel.loadingMore ? qsTr("Cargando…") : qsTr("Cargar más")
                        variant: "ghost"
                        enabled: root.trackModel && !root.trackModel.loadingMore
                        onClicked: {
                            if (root.trackModel && root.trackModel.hasMore)
                                root.trackModel.fetchMore()
                        }
                    }
                }
            }
        }

        LibraryEmptyState {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.trackModel && root.trackModel.count === 0 && root.trackModel.initialized && !root.trackModel.loading
            title: qsTr("Sin resultados")
            message: qsTr("No se encontraron canciones con los filtros actuales.")
            actionText: qsTr("Limpiar filtros")
            onActionRequested: {
                if (root.bridge && root.bridge.clearFilters) root.bridge.clearFilters()
            }
        }
    }

    Connections {
        target: root.trackModel
        function onLoadingMoreChanged() {
            root._fetchingMore = root.trackModel ? root.trackModel.loadingMore : false
        }
    }
}
