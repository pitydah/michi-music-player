import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../theme"
// POST-R4 P5: packing y render consumen AlbumListColumnMetrics.

ListView {
    id: root
    objectName: "albumListView"

    property var albumModel: library.albums
    // M9-R3 CONVERGENCE SEAL: target del contexto por teclado — el
    // álbum del currentIndex (roving). El teclado vive en el VIEW, no en
    // los delegates (activeFocusOnTab false): Menu/Shift+F10 abren el
    // menú del álbum actual.
    property var contextAlbum: null

    function openCurrentAlbumContext() {
        if (root.albumModel === undefined
                || root.albumModel.length === 0
                || root.currentIndex < 0
                || root.currentIndex >= root.albumModel.length)
            return
        root.contextAlbum = root.albumModel[root.currentIndex]
        if (root.browseState && root.contextAlbum)
            root.browseState.remember(root.contextAlbum.key)
        albumContextMenu.popup()
    }

    function handleAlbumContextKey(event) {
        if (event.key === Qt.Key_Menu
                || (event.key === Qt.Key_F10
                    && (event.modifiers & Qt.ShiftModifier))) {
            root.openCurrentAlbumContext()
            event.accepted = true
            return true
        }
        return false
    }
    property string sortMode: "title"
    property bool sortDescending: false
    property var browseState: null
    // R7-01: currentKey es la identidad canónica del browse; las
    // transiciones de currentIndex durante la restauración nunca la
    // escriben. TRUE desde la construcción.
    property bool browseRestoreInProgress: true
    property var viewPreferences: ({})
    signal sortRequested(string mode)
    readonly property var columnPlan: resolveColumnPlan(width, viewPreferences)
    readonly property bool showArtistColumn: columnPlan.artist
    readonly property bool showYearColumn: columnPlan.year
    readonly property bool showTrackCountColumn: columnPlan.tracks
    readonly property bool showDurationColumn: columnPlan.duration
    readonly property bool showTechnicalColumn: columnPlan.format

    function resolveColumnPlan(availableWidth, preferences) {
        // POST-R4 P5: que una columna costosa no quepa (p.ej. Artist) NO
        // impide probar las siguientes (Year/Tracks/Duration/Format):
        // continue, nunca break — el packing recorre el orden completo.
        var remaining = Math.max(0, availableWidth - 360)
        var result = { artist: false, year: false, tracks: false,
            duration: false, format: false }
        var ordered = [
            { key: "artist", pref: "artistColumn" },
            { key: "year", pref: "yearColumn" },
            { key: "tracks", pref: "tracksColumn" },
            { key: "duration", pref: "durationColumn" },
            { key: "format", pref: "formatColumn" }
        ]
        for (var index = 0; index < ordered.length; ++index) {
            var column = ordered[index]
            if (preferences[column.pref] === false)
                continue
            var cost = AlbumListColumnMetrics.columnCost(column.key)
            if (remaining < cost)
                continue
            result[column.key] = true
            remaining -= cost
        }
        return result
    }

    Layout.fillWidth: true
    Layout.fillHeight: true
    model: albumModel
    clip: true
    spacing: MichiSpacing.xs
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true
    keyNavigationWraps: false
    activeFocusOnTab: true
    focus: true
    cacheBuffer: height
    reuseItems: true
    headerPositioning: ListView.OverlayHeader
    Accessible.role: Accessible.Table
    Accessible.name: qsTr("Albums in list view")

    function findIndexByKey(key) {
        if (!key)
            return -1
        for (var i = 0; i < albumModel.length; ++i) {
            if (albumModel[i].key === key)
                return i
        }
        return -1
    }

    // R7-01: lifecycle determinístico de restauración/proyección.
    function restoreBrowseSelection() {
        if (!browseState || !albumModel)
            return
        if (albumModel.length === 0)
            return  // restauración pendiente (modelo tardío)
        browseKeyboardArmed = false
        browseRestoreInProgress = true
        var resolvedIndex = browseState.currentKey !== ""
            ? root.findIndexByKey(browseState.currentKey)
            : browseState.listIndex
        if (resolvedIndex < 0)
            resolvedIndex = 0
        if (resolvedIndex >= albumModel.length)
            resolvedIndex = albumModel.length - 1
        root.currentIndex = resolvedIndex
        root.contentY = browseState.listContentY
        if (browseState.currentKey !== ""
                && albumModel[resolvedIndex].key !== browseState.currentKey) {
            browseState.currentKey = ""
            browseState.listIndex = -1
            if (albumModel.length > 0) {
                root.currentIndex = 0
                browseState.remember(albumModel[0].key)
            }
            root.contentY = 0
        }
        browseRestoreInProgress = false
    }
        Timer {
        id: browseRestoreTimer
        interval: 0
        repeat: false
        onTriggered: root.restoreBrowseSelection()
    }
    Component.onCompleted: browseRestoreTimer.start()
    // R7-01: la identidad puede cambiar por una intención en OTRA
    // superficie (search, detail, fallback): la vista activa re-proyecta
    // el índice — sin re-escribir la key (el flag del restore protege).
    Connections {
        target: root.browseState
        function onCurrentKeyChanged() {
            if (root.browseState && root.browseState.currentKey !== "")
                browseRestoreTimer.start()
        }
    }
    onAlbumModelChanged: if (browseState && albumModel.length > 0)
        browseRestoreTimer.start()
    // R7-01: la identidad exige INTENCIÓN — ruta única explícita.
    property bool browseKeyboardArmed: false
    function browseTo(index) {
        if (index < 0 || index >= albumModel.length)
            return
        root.currentIndex = index
        if (browseState && !browseRestoreInProgress)
            browseState.remember(albumModel[index].key)
    }
    onContentYChanged: if (browseState) browseState.listContentY = contentY
    onCurrentIndexChanged: if (browseState) {
        browseState.listIndex = currentIndex
        if (browseKeyboardArmed && !browseRestoreInProgress
                && currentIndex >= 0 && currentIndex < albumModel.length) {
            browseKeyboardArmed = false
            browseState.remember(albumModel[currentIndex].key)
        }
    }

    header: AlbumTableHeader {
        width: root.width
        artworkSize: root.viewPreferences.artworkSize || "small"
        showArtist: root.showArtistColumn
        showYear: root.showYearColumn
        showTrackCount: root.showTrackCountColumn
        showDuration: root.showDurationColumn
        showTechnical: root.showTechnicalColumn
        sortMode: root.sortMode
        sortDescending: root.sortDescending
        onSortRequested: mode => root.sortRequested(mode)
    }

    Keys.onReturnPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length) {
            root.browseTo(currentIndex)
            library.select_album(albumModel[currentIndex].key)
        }
    }
    Keys.onEnterPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length) {
            root.browseTo(currentIndex)
            library.select_album(albumModel[currentIndex].key)
        }
    }
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Up || event.key === Qt.Key_Down)
            root.browseKeyboardArmed = true
    }
    // R7-01: intención one-shot — el release desarma SIEMPRE (si el
    // built-in no movió el índice, el armed no sobrevive a la tecla).
    Keys.onReleased: function(event) {
        if (event.key === Qt.Key_Up || event.key === Qt.Key_Down)
            root.browseKeyboardArmed = false
    }
    Keys.onSpacePressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.play_album(albumModel[currentIndex].key)
    }

    ScrollBar.vertical: MichiScrollBar { }

    delegate: MichiAlbumRow {
        required property int index
        required property var modelData
        width: root.width
        album: modelData
        selected: ListView.isCurrentItem
        collectionFocus: root.activeFocus && ListView.isCurrentItem
        showArtist: root.showArtistColumn
        showYear: root.showYearColumn
        showTrackCount: root.showTrackCountColumn
        showDuration: root.showDurationColumn
        showTechnical: root.showTechnicalColumn
        precisionMetadata: root.viewPreferences.precisionMetadata !== false
        artworkSize: root.viewPreferences.artworkSize || "small"
        rowDensity: root.viewPreferences.density || "standard"
        onActiveFocusChanged: {
            if (activeFocus)
                root.browseTo(index)
        }
        onSelectedRequested: {
            root.browseTo(index)
        }
        onOpenRequested: {
            root.browseTo(index)
            library.select_album(modelData.key)
        }
        onPlayRequested: library.play_album(modelData.key)
    }

    // M9-R3 CONVERGENCE SEAL: menú raíz del teclado (roving del view).
    AlbumContextMenu {
        id: albumContextMenu
                album: root.contextAlbum
        canAddToPlaylist: true
        canCreatePlaylist: true
        canShowProperties: true
        z: 300
    }
}