import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../media"
import "../theme"

GridView {
    id: albumGrid
    objectName: "albumGridView"

    property var albumModel: library.albums
    // M9-R3 CONVERGENCE SEAL: target del contexto por teclado — el
    // álbum del currentIndex (roving). El teclado vive en el VIEW, no en
    // los delegates (activeFocusOnTab false): Menu/Shift+F10 abren el
    // menú del álbum actual.
    property var contextAlbum: null

    function openCurrentAlbumContext() {
        if (albumGrid.albumModel === undefined
                || albumGrid.albumModel.length === 0
                || albumGrid.currentIndex < 0
                || albumGrid.currentIndex >= albumGrid.albumModel.length)
            return
        albumGrid.contextAlbum = albumGrid.albumModel[albumGrid.currentIndex]
        if (albumGrid.browseState && albumGrid.contextAlbum)
            albumGrid.browseState.remember(albumGrid.contextAlbum.key)
        albumContextMenu.popup()
    }

    function handleAlbumContextKey(event) {
        if (event.key === Qt.Key_Menu
                || (event.key === Qt.Key_F10
                    && (event.modifiers & Qt.ShiftModifier))) {
            albumGrid.openCurrentAlbumContext()
            event.accepted = true
            return true
        }
        return false
    }
    property real albumZoom: 1.0
    property var browseState: null
    // R7-01: currentKey es la identidad canónica del browse. Durante la
    // restauración inicial (y los fallbacks controlados), las
    // transiciones de currentIndex NUNCA escriben la identidad — solo la
    // interacción del usuario la muta. TRUE desde la construcción: el
    // índice inicial/default de la vista no puede contaminar la key.
    property bool browseRestoreInProgress: true
    property string spacingMode: "balanced"
    property string metadataLevel: "standard"
    property bool quickActions: true
    property bool precisionMetadata: false
    property bool layoutReady: false
    readonly property real contentMaxWidth: 1760
    readonly property real usableWidth: Math.min(width, contentMaxWidth)
    readonly property int minimumCardWidth: MichiThemeState.density === "compact"
        ? Math.round(154 * albumZoom)
        : MichiThemeState.density === "comfortable"
            ? Math.round(220 * albumZoom) : Math.round(184 * albumZoom)
    readonly property int maximumCardWidth: MichiThemeState.density === "compact"
        ? Math.round(184 * albumZoom)
        : MichiThemeState.density === "comfortable"
            ? Math.round(250 * albumZoom) : Math.round(216 * albumZoom)
    readonly property int cardGap: spacingMode === "tight" ? MichiSpacing.sm
        : spacingMode === "airy" ? MichiSpacing.xl : MichiThemeState.contentGap
    readonly property int columnCount: Math.max(1, Math.floor(
        (usableWidth + cardGap) / (minimumCardWidth + cardGap)))
    readonly property bool rowsFlowActive: flow === GridView.FlowLeftToRight
    readonly property real resolvedCardWidth: Math.min(maximumCardWidth,
        cellWidth - cardGap)
    readonly property int metadataHeight: metadataLevel === "minimal" ? 64
        : metadataLevel === "detailed" ? 112 : 86

    Layout.fillWidth: true
    Layout.fillHeight: true
    // A Loader may complete this component before its layout has assigned the
    // final width. Defer delegate creation one event-loop turn so GridView does
    // not retain cells positioned against the provisional one-column geometry.
    model: layoutReady ? albumModel : []
    flow: GridView.FlowLeftToRight
    leftMargin: Math.max(0, (width - usableWidth) / 2)
    rightMargin: leftMargin
    cellWidth: usableWidth / columnCount
    cellHeight: resolvedCardWidth + metadataHeight + cardGap
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    keyNavigationEnabled: true
    keyNavigationWraps: false
    activeFocusOnTab: true
    focus: true
    cacheBuffer: cellHeight * 2
    Accessible.role: Accessible.List
    Accessible.name: qsTr("Albums in grid view")
    Accessible.description: qsTr("Use arrow keys to browse and Enter to open an album")

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
    // 1) identidad: currentKey → índice en el modelo vigente;
    // 2) posición visual local (nunca impone identidad);
    // 3) fallback explícito cuando la key ya no existe en el modelo
    //    activo (clear + índice 0 + nueva key establecida de forma
    //    controlada — jamás por efecto colateral del índice viejo).
    // Con el modelo aún vacío la restauración queda PENDIENTE: la key
    // nunca se borra por un estado transitorio (onAlbumModelChanged la
    // completa cuando el modelo llega).
    function restoreBrowseSelection() {
        if (!browseState || !albumModel)
            return
        if (albumModel.length === 0)
            return  // restauración pendiente: browseRestoreInProgress sigue true
        browseKeyboardArmed = false
        browseRestoreInProgress = true
        var resolvedIndex = -1
        if (browseState.currentKey !== "")
            resolvedIndex = albumGrid.findIndexByKey(browseState.currentKey)
        else
            resolvedIndex = browseState.galleryIndex
        if (resolvedIndex < 0)
            resolvedIndex = 0
        if (resolvedIndex >= albumModel.length)
            resolvedIndex = albumModel.length - 1
        albumGrid.currentIndex = resolvedIndex
        albumGrid.contentY = browseState.galleryContentY
        if (browseState.currentKey !== ""
                && albumModel[resolvedIndex].key !== browseState.currentKey) {
            // la key desapareció del modelo activo: fallback explícito
            // determinístico (índice 0), con la nueva key establecida
            // de forma controlada.
            browseState.currentKey = ""
            browseState.galleryIndex = -1
            if (albumModel.length > 0) {
                albumGrid.currentIndex = 0
                browseState.remember(albumModel[0].key)
            }
            albumGrid.contentY = 0
        }
        browseRestoreInProgress = false
    }
    // R7-01: el defer de un ciclo (restauración tras el update del
    // modelo del view) usa un Timer de 0 ms: se destruye con la vista —
    // el callLater evalúa en un contexto inválido durante el teardown.
    Timer {
        id: browseRestoreTimer
        interval: 0
        repeat: false
        onTriggered: albumGrid.restoreBrowseSelection()
    }
    Component.onCompleted: {
        albumGrid.layoutReady = true
        albumGrid.forceLayout()
        browseRestoreTimer.start()
    }
    // R7-01: la identidad puede cambiar por una intención en OTRA
    // superficie (search, detail, fallback): la vista activa re-proyecta
    // el índice — sin re-escribir la key (el flag del restore protege).
    Connections {
        target: albumGrid.browseState
        function onCurrentKeyChanged() {
            if (albumGrid.browseState && albumGrid.browseState.currentKey !== "")
                browseRestoreTimer.start()
        }
    }
    // modelo tardío o cambios del modelo (sort/filter/search/scan):
    // re-proyectar la key (o completar la restauración pendiente).
    onAlbumModelChanged: if (browseState && albumModel.length > 0)
        browseRestoreTimer.start()
    onCellWidthChanged: if (layoutReady) albumGrid.forceLayout()
    onCellHeightChanged: if (layoutReady) albumGrid.forceLayout()
    onContentYChanged: if (browseState) browseState.galleryContentY = contentY
    // R7-01: el remember exige INTENCIÓN — el armed lo pone la
    // navegación por teclado (flechas) antes del movimiento built-in; el
    // handler lo consume y desarma. Los cambios de índice del layout/
    // restauración nunca escriben la identidad.
    property bool browseKeyboardArmed: false
    function browseTo(index) {
        if (index < 0 || index >= albumModel.length)
            return
        albumGrid.currentIndex = index
        if (browseState && !browseRestoreInProgress)
            browseState.remember(albumModel[index].key)
    }
    onCurrentIndexChanged: if (browseState) {
        browseState.galleryIndex = currentIndex
        if (browseKeyboardArmed && !browseRestoreInProgress
                && currentIndex >= 0 && currentIndex < albumModel.length) {
            browseKeyboardArmed = false
            browseState.remember(albumModel[currentIndex].key)
        }
    }

    Keys.onReturnPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }
    Keys.onEnterPressed: {
        if (currentIndex >= 0 && currentIndex < albumModel.length)
            library.select_album(albumModel[currentIndex].key)
    }
    Keys.onPressed: function(event) {
        if (albumGrid.handleAlbumContextKey(event))
            return
        if (event.key === Qt.Key_Home) {
            albumGrid.browseTo(0)
            positionViewAtBeginning()
            event.accepted = true
        } else if (event.key === Qt.Key_End) {
            albumGrid.browseTo(count - 1)
            positionViewAtEnd()
            event.accepted = true
        } else if (event.key === Qt.Key_Up || event.key === Qt.Key_Down
                || event.key === Qt.Key_Left || event.key === Qt.Key_Right) {
            // la navegación built-in moverá el índice: armar la intención.
            albumGrid.browseKeyboardArmed = true
        }
    }
    // R7-01: intención one-shot — el release desarma SIEMPRE (si el
    // built-in no movió el índice, el armed no sobrevive a la tecla).
    Keys.onReleased: function(event) {
        albumGrid.browseKeyboardArmed = false
    }

    ScrollBar.vertical: MichiScrollBar { }

    delegate: Item {
        id: albumCell
        objectName: "albumGridCell"
        required property int index
        required property var modelData
        readonly property bool current: GridView.isCurrentItem

        width: albumGrid.cellWidth
        height: albumGrid.cellHeight

        AlbumCard {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: albumGrid.resolvedCardWidth
            height: parent.height - albumGrid.cardGap
            album: albumCell.modelData
            selected: albumCell.current
            collectionFocus: albumGrid.activeFocus && albumCell.current
            metadataLevel: albumGrid.metadataLevel
            quickActionsVisible: albumGrid.quickActions
            precisionMetadata: albumGrid.precisionMetadata
            onActiveFocusChanged: {
                if (activeFocus)
                    albumGrid.browseTo(albumCell.index)
            }
            onSelectedRequested: {
                albumGrid.browseTo(albumCell.index)
            }
            onOpenRequested: {
                albumGrid.browseTo(albumCell.index)
                library.select_album(albumCell.modelData.key)
            }
            onPlayRequested: library.play_album(albumCell.modelData.key)
        }
    }

    // M9-R3 CONVERGENCE SEAL: menú raíz del teclado (roving del view).
    AlbumContextMenu {
        id: albumContextMenu
                album: albumGrid.contextAlbum
        // R3 (shared host A1): consumer real de playlist/create/properties
        // (request_album_playlist_target / new_playlist / properties →
        // host → picker/dialog/view). El archivo del menú conserva los
        // defaults false (fail-closed sin host).
        canAddToPlaylist: true
        canCreatePlaylist: true
        canShowProperties: true
        z: 300
    }
}