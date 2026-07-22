import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../../theme"
import "../../components"
import "../../components/foundations"
import "../../materials"
import "album"

MichiPage {
    id: root
    objectName: "libraryPage_control"
    focus: true
    accessibleName: qsTr("Biblioteca")
    scrollable: false
    constrainContentWidth: false

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var notif: typeof notificationBridge !== "undefined" ? notificationBridge : null
    property var sel: typeof selectionContextBridge !== "undefined" ? selectionContextBridge : null
    property int _currentLibrarySection: 0
    readonly property int _navigationSection: _currentLibrarySection === 3 ? 5 : _currentLibrarySection
    readonly property var _localSectionTitles: [qsTr("Canciones"), qsTr("Álbumes"), qsTr("Artistas"), qsTr("Carpetas")]
    property bool _searchActive: false
    property bool _restoringState: false

    MichiResponsive { id: responsive; availableWidth: root.width }

    header: MichiPageHeader {
        width: parent ? parent.width : 0
        title: qsTr("Biblioteca")
        subtitle: qsTr("Explora canciones, álbumes, artistas y carpetas")
        iconKey: "library"
        tabs: LibraryNavigationBar {
            width: parent ? parent.width : 0
            currentIndex: root._navigationSection
            onSectionRequested: function(index, route) {
                if (index <= 2) {
                    root._currentLibrarySection = index
                    pageState.currentTab = index
                } else if (index === 5) {
                    root._currentLibrarySection = 3
                    pageState.currentTab = 3
                } else if (typeof navigationBridge !== "undefined") {
                    navigationBridge.navigate(route)
                }
            }
        }
    }

    PageStateManager {
        id: pageState
        route: "library"
        active: true
        onCurrentTabChanged: pageState.save()
        onSearchTextChanged: pageState.save()
    }

    enum State {
        INITIALIZING,
        NO_SOURCES,
        SOURCE_EMPTY,
        SOURCE_OFFLINE,
        SOURCE_PERMISSION_ERROR,
        SCANNING,
        INDEXING,
        LOADING,
        READY,
        FILTERED_EMPTY,
        DATABASE_ERROR,
        QUERY_ERROR,
        PARTIAL_RESULTS,
        CANCELLED,
        MISSING_CONTENT
    }

    property int libraryState: LibraryPage.INITIALIZING

    function refreshData() {
        if (root.lib && root.lib.refresh) {
            root.lib.refresh()
            if (root.notif) root.notif.showMessage(qsTr("Biblioteca actualizada"), "info")
        }
    }

    function clearFilters() {
        toolbar.setSearchText("")
        filterBar.specialFilter = ""
        filterBar.genreText = ""
        filterBar.composerText = ""
        filterBar.yearText = ""
        if (root.lib && root.lib.clearFilters) root.lib.clearFilters()
    }

    function showArtistDetail(name) {
        if (typeof navigationBridge !== "undefined" && name)
            navigationBridge.navigateWithParams("library.artist_detail", {artist: name})
    }

    function showAlbumDetail(key, title, artist, year) {
        if (typeof navigationBridge !== "undefined" && key)
            navigationBridge.navigateWithParams("library.album_detail", {album_key: key})
    }

    function _updateState() {
        if (!root.lib) {
            libraryState = LibraryPage.INITIALIZING
            return
        }
        switch (root.lib.state || "INITIALIZING") {
        case "NO_SOURCES": libraryState = LibraryPage.NO_SOURCES; break
        case "SOURCE_EMPTY": libraryState = LibraryPage.SOURCE_EMPTY; break
        case "SOURCE_OFFLINE": libraryState = LibraryPage.SOURCE_OFFLINE; break
        case "SOURCE_PERMISSION_ERROR": libraryState = LibraryPage.SOURCE_PERMISSION_ERROR; break
        case "SCANNING": libraryState = LibraryPage.SCANNING; break
        case "INDEXING": libraryState = LibraryPage.INDEXING; break
        case "LOADING": libraryState = LibraryPage.LOADING; break
        case "READY": libraryState = LibraryPage.READY; break
        case "FILTERED_EMPTY": libraryState = LibraryPage.FILTERED_EMPTY; break
        case "DATABASE_ERROR": libraryState = LibraryPage.DATABASE_ERROR; break
        case "QUERY_ERROR": libraryState = LibraryPage.QUERY_ERROR; break
        case "PARTIAL_RESULTS": libraryState = LibraryPage.PARTIAL_RESULTS; break
        case "CANCELLED": libraryState = LibraryPage.CANCELLED; break
        case "MISSING_CONTENT": libraryState = LibraryPage.MISSING_CONTENT; break
        default: libraryState = LibraryPage.INITIALIZING
        }
    }

    function _saveFilterState() {
        if (root._restoringState) return
        pageState.filterState = {
            specialFilter: filterBar.specialFilter,
            genreText: filterBar.genreText,
            composerText: filterBar.composerText,
            yearText: filterBar.yearText,
            expanded: filterBar.expanded
        }
        pageState.save()
    }

    function _restoreVisualState() {
        if (!pageState.hasSavedState()) return
        root._restoringState = true
        var state = pageState.restore()
        root._currentLibrarySection = pageState.currentTab
        toolbar.setSearchText(pageState.searchText)
        albumViewHost.currentView = pageState.currentView
        var filters = state.filterState || ({})
        filterBar.specialFilter = filters.specialFilter || ""
        filterBar.genreText = filters.genreText || ""
        filterBar.composerText = filters.composerText || ""
        filterBar.yearText = filters.yearText || ""
        filterBar.expanded = filters.expanded || false
        root._restoringState = false
    }

    function routeEnter(route, params) {
        root._restoreVisualState()
        if (root.lib && root.lib.ensureLoaded) root.lib.ensureLoaded()
        root._updateState()
    }

    function openTrackContextMenu(trackId, trackTitle, trackArtist, trackAlbum, albumKey) {
        contextMenu.trackId = trackId
        contextMenu.trackTitle = trackTitle
        contextMenu.trackArtist = trackArtist
        contextMenu.trackAlbum = trackAlbum
        contextMenu.albumKey = albumKey
        contextMenu.open()
    }

    function runSelectionAction(actionId, ids) {
        if (!root.lib || !ids || ids.length === 0) return
        var succeeded = 0
        if (actionId === "track_play_now") {
            var playResult = root.lib.playTrackById(ids[0])
            if (playResult && playResult.ok) succeeded++
            for (var i = 1; i < ids.length; i++) {
                var enqueueAfterPlay = root.lib.enqueueTrackById(ids[i])
                if (enqueueAfterPlay && enqueueAfterPlay.ok) succeeded++
            }
        } else if (actionId === "track_add_to_queue") {
            for (var q = 0; q < ids.length; q++) {
                var queueResult = root.lib.enqueueTrackById(ids[q])
                if (queueResult && queueResult.ok) succeeded++
            }
        } else if (actionId === "track_favorite") {
            for (var f = 0; f < ids.length; f++) {
                var favoriteResult = root.lib.toggleFavoriteById(ids[f])
                if (favoriteResult && favoriteResult.ok) succeeded++
            }
        }
        if (root.notif)
            root.notif.showMessage(qsTr("Acción aplicada a %1 de %2 elementos").arg(succeeded).arg(ids.length),
                                   succeeded === ids.length ? "success" : "warning")
        tracksView.clearSelection()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: MichiTheme.spacing.xs

        MichiLibraryToolbar {
            id: toolbar
            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
            title: root._localSectionTitles[root._currentLibrarySection]
            filterModel: []
            currentFilterIndex: root._navigationSection
            selectionActive: selectionBar.visible
            selectedCount: selectionBar.selectedCount
            onFilterChanged: function(index) {
                root._currentLibrarySection = index
                pageState.currentTab = index
            }
            onSearchChanged: function(text) {
                if (root._restoringState) return
                if (root.lib && root.lib.search) root.lib.search(text)
                root._searchActive = text.length > 0
                pageState.searchText = text
                pageState.save()
            }
            onRefreshRequested: root.refreshData()
        }

        LibraryFilterBar {
            id: filterBar
            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
            activeFocusOnTab: true
            onFormatFilterChanged: function(format) {
                if (root.lib) root.lib.setFormatFilter(format)
            }
            onGenreFilterChanged: function(genre) {
                if (root.lib) root.lib.setGenreFilter(genre)
            }
            onComposerFilterChanged: function(composer) {
                if (root.lib) root.lib.setComposerFilter(composer)
            }
            onYearFilterChanged: function(year) {
                if (root.lib) root.lib.setYearFilter(year)
            }
            onSpecialFilterChanged: root._saveFilterState()
            onGenreTextChanged: root._saveFilterState()
            onComposerTextChanged: root._saveFilterState()
            onYearTextChanged: root._saveFilterState()
            onExpandedChanged: root._saveFilterState()
        }

        LibraryStatusHeader {
            id: statusHeader
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? implicitHeight : 0
            visible: root.lib && (root.lib.songCount > 0 || root.lib.state !== "READY")
            songCount: root.lib ? root.lib.songCount : 0
            albumCount: root.lib ? root.lib.albumCount : 0
            artistCount: root.lib ? root.lib.artistCount : 0
            state: root.lib ? root.lib.state : "INITIALIZING"
        }

        StackLayout {
            id: stackContainer
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root._currentLibrarySection
            onCurrentIndexChanged: {
                root._currentLibrarySection = currentIndex
                pageState.currentTab = currentIndex
            }

            FocusScope {
                focus: root._currentLibrarySection === 0
                LibraryTrackTable {
                    id: tracksView
                    anchors.fill: parent
                    trackModel: root.lib ? root.lib.trackModel : null
                    bridge: root.lib
                    notif: root.notif
                    selectionController: root.sel
                    activeFocusOnTab: true
                    onSelectionChanged: function(ids) {
                        selectionBar.selectedIds = ids.slice()
                    }
                    onTrackContextMenuRequested: function(trackId, title, artist, album, albumKey) {
                        root.openTrackContextMenu(trackId, title, artist, album, albumKey)
                    }
                }
            }

            FocusScope {
                focus: root._currentLibrarySection === 1
                AlbumViewHost {
                    id: albumViewHost
                    anchors.fill: parent
                    albumModel: root.lib ? root.lib.albumModel : null
                    bridge: root.lib
                    onAlbumClicked: function(key, title, artist, year) {
                        root.showAlbumDetail(key, title, artist, year)
                    }
                    onViewChanged: function(index) {
                        pageState.currentView = index
                        pageState.save()
                    }
                }
            }

            FocusScope {
                focus: root._currentLibrarySection === 2
                ArtistGridPage {
                    anchors.fill: parent
                    artistModel: root.lib ? root.lib.artistModel : null
                    bridge: root.lib
                    activeFocusOnTab: true
                    onArtistClicked: function(name) { root.showArtistDetail(name) }
                }
            }

            FocusScope {
                focus: root._currentLibrarySection === 3
                FolderBrowserPage {
                    anchors.fill: parent
                    folderModel: root.lib ? root.lib.folderModel : null
                    bridge: root.lib
                    embedded: true
                    activeFocusOnTab: true
                }
            }
        }

        LibrarySelectionBar {
            id: selectionBar
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? implicitHeight : 0
            z: 10
            bridge: root.lib
            visible: selectedCount > 0
            onActionRequested: function(actionId, ids) { root.runSelectionAction(actionId, ids) }
            onSelectionCleared: tracksView.clearSelection()
        }
    }

    LibraryContextMenu {
        id: contextMenu
        bridge: root.lib
    }

    Rectangle {
        id: partialResultsBanner
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: MichiTheme.spacing.md
        width: Math.min(560, parent.width - MichiTheme.spacing.xl)
        height: 44
        radius: MichiTheme.radius.lg
        color: MichiTheme.colors.badgeWarningBg
        border.width: MichiTheme.borderWidth
        border.color: MichiTheme.colors.warning
        z: 30
        visible: libraryState === LibraryPage.PARTIAL_RESULTS || libraryState === LibraryPage.MISSING_CONTENT
        Text {
            anchors.centerIn: parent
            text: libraryState === LibraryPage.MISSING_CONTENT
                  ? qsTr("Parte de la colección no está disponible en disco")
                  : qsTr("Se muestran resultados parciales; puedes reintentar la consulta")
            color: MichiTheme.colors.badgeWarningText
            font.pixelSize: MichiTheme.typography.metaSize
            font.weight: MichiTheme.typography.weightSemiBold
        }
    }

    MichiEmptyState {
        anchors.centerIn: parent
        z: 40
        visible: libraryState === LibraryPage.NO_SOURCES
        title: qsTr("Sin fuentes musicales")
        message: qsTr("Configura una o más carpetas para construir tu biblioteca.")
        primaryActionText: qsTr("Configurar fuentes")
        onPrimaryActionRequested: {
            if (typeof navigationBridge !== "undefined") navigationBridge.navigate("library.sources")
        }
    }

    MichiEmptyState {
        anchors.centerIn: parent
        z: 40
        visible: libraryState === LibraryPage.SOURCE_EMPTY
        title: qsTr("La fuente está vacía")
        message: qsTr("La carpeta configurada no contiene archivos de audio compatibles.")
        primaryActionText: qsTr("Reescanear")
        onPrimaryActionRequested: root.refreshData()
    }

    MichiEmptyState {
        anchors.centerIn: parent
        z: 40
        visible: libraryState === LibraryPage.FILTERED_EMPTY
        title: qsTr("Sin resultados")
        message: qsTr("No se encontraron elementos con los filtros actuales.")
        primaryActionText: qsTr("Limpiar filtros")
        onPrimaryActionRequested: root.clearFilters()
    }

    MichiEmptyState {
        anchors.centerIn: parent
        z: 40
        visible: libraryState === LibraryPage.SOURCE_OFFLINE
        title: qsTr("Fuente no disponible")
        message: qsTr("La unidad, recurso de red o carpeta configurada está desconectada.")
        primaryActionText: qsTr("Reintentar")
        onPrimaryActionRequested: root.refreshData()
    }

    MichiErrorState {
        anchors.centerIn: parent
        z: 40
        visible: libraryState === LibraryPage.SOURCE_PERMISSION_ERROR
        title: qsTr("Permiso denegado")
        message: qsTr("Michi no puede leer una de las fuentes configuradas. Revisa sus permisos.")
        primaryActionText: qsTr("Abrir fuentes")
        onPrimaryActionRequested: {
            if (typeof navigationBridge !== "undefined") navigationBridge.navigate("library.sources")
        }
    }

    MichiErrorState {
        anchors.centerIn: parent
        z: 40
        visible: libraryState === LibraryPage.QUERY_ERROR || libraryState === LibraryPage.DATABASE_ERROR
        title: qsTr("Error de biblioteca")
        message: root.lib ? root.lib.errorMessage : qsTr("No fue posible consultar la biblioteca.")
        primaryActionText: qsTr("Reintentar")
        onPrimaryActionRequested: root.refreshData()
    }

    MichiEmptyState {
        anchors.centerIn: parent
        z: 40
        visible: libraryState === LibraryPage.CANCELLED
        title: qsTr("Operación cancelada")
        message: qsTr("La carga de la biblioteca fue cancelada antes de completarse.")
        primaryActionText: qsTr("Reintentar")
        onPrimaryActionRequested: root.refreshData()
    }

    MichiLoadingState {
        anchors.centerIn: parent
        z: 50
        visible: libraryState === LibraryPage.INITIALIZING ||
                 libraryState === LibraryPage.LOADING ||
                 libraryState === LibraryPage.SCANNING ||
                 libraryState === LibraryPage.INDEXING
        title: libraryState === LibraryPage.SCANNING ? qsTr("Escaneando fuentes")
              : libraryState === LibraryPage.INDEXING ? qsTr("Indexando biblioteca")
              : qsTr("Cargando biblioteca")
    }

    Connections {
        target: root.lib
        function onStateChanged() { root._updateState() }
        function onDataChanged() { root._updateState() }
    }

    Component.onCompleted: {
        root._restoreVisualState()
        if (root.lib && root.lib.ensureLoaded) root.lib.ensureLoaded()
        root._updateState()
    }
}
