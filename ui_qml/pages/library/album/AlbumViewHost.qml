import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../theme"
import "../../../components"
import ".." as LibraryPages

Item {
    id: root
    objectName: "albumViewHost"
    focus: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Explorador visual de álbumes")
    Accessible.description: qsTr("Cambia entre cinco presentaciones sin volver a consultar la biblioteca")

    property var albumModel: null
    property var bridge: null
    property int currentView: 0
    property string sortOrder: "year"
    property string density: "regular"
    property var viewStates: ({})
    readonly property var sortOptions: [
        { label: qsTr("Año"), key: "year" },
        { label: qsTr("Título"), key: "title" },
        { label: qsTr("Artista"), key: "artist" },
        { label: qsTr("Fecha añadida"), key: "added" },
        { label: qsTr("Reproducciones"), key: "play_count" }
    ]
    readonly property var densityOptions: [
        { label: qsTr("Compacta"), key: "compact" },
        { label: qsTr("Regular"), key: "regular" },
        { label: qsTr("Cómoda"), key: "comfortable" }
    ]
    readonly property bool initialLoading: root.albumModel && root.albumModel.loading && root.albumModel.count === 0
    readonly property bool loadingMore: root.albumModel && root.albumModel.loadingMore
    readonly property bool hasError: root.albumModel && root.albumModel.errorMessage !== ""
    readonly property int loadedCount: root.albumModel ? root.albumModel.count : 0
    readonly property int totalCount: root.albumModel ? root.albumModel.totalCount : 0
    readonly property bool modelContentMismatch: root.totalCount > 0
        && !root.initialLoading
        && !root.loadingMore
        && root.loadedCount === 0
        && !root.hasError
    readonly property var viewModes: [
        { name: qsTr("Grid"), shortName: qsTr("Grid"), description: qsTr("Colección adaptable") },
        { name: qsTr("CoverFlow"), shortName: qsTr("Flow"), description: qsTr("Exploración cinematográfica") },
        { name: qsTr("Vinyl Wall"), shortName: qsTr("Vinyl"), description: qsTr("Muro de discos") },
        { name: qsTr("Timeline"), shortName: qsTr("Tiempo"), description: qsTr("Archivo cronológico") },
        { name: qsTr("Magazine"), shortName: qsTr("Editorial"), description: qsTr("Curaduría visual") }
    ]

    signal albumClicked(string albumKey, string title, string artist, int year)
    signal viewChanged(int viewIndex)

    function saveCurrentViewState() {
        if (viewLoader.status !== Loader.Ready || !viewLoader.item)
            return
        var states = Object.assign({}, root.viewStates)
        states[String(root.currentView)] = {
            scrollPosition: Number(viewLoader.item.scrollPosition || 0),
            selectionIndex: Number(viewLoader.item.selectionIndex)
        }
        root.viewStates = states
    }

    function restoreCurrentViewState() {
        if (viewLoader.status !== Loader.Ready || !viewLoader.item)
            return
        var state = root.viewStates[String(root.currentView)]
        if (!state)
            return
        viewLoader.item.selectionIndex = state.selectionIndex
        viewLoader.item.scrollPosition = state.scrollPosition
    }

    function selectView(index) {
        if (index < 0 || index >= root.viewModes.length || index === root.currentView)
            return
        root.saveCurrentViewState()
        root.currentView = index
        root.viewChanged(index)
    }

    function cycleView(delta) {
        var next = (root.currentView + delta + root.viewModes.length) % root.viewModes.length
        root.selectView(next)
    }

    function applySort(index) {
        if (index < 0 || index >= root.sortOptions.length)
            return
        var option = root.sortOptions[index]
        root.sortOrder = option.key
        var ascending = option.key === "title" || option.key === "artist"
        if (root.albumModel && root.albumModel.refreshForSort)
            root.albumModel.refreshForSort(option.key, ascending)
    }

    function applyDensity(index) {
        if (index < 0 || index >= root.densityOptions.length)
            return
        root.density = root.densityOptions[index].key
        if (viewLoader.status === Loader.Ready && viewLoader.item &&
                typeof viewLoader.item.density !== "undefined")
            viewLoader.item.density = root.density
    }

    Keys.onPressed: function(event) {
        if ((event.modifiers & Qt.ControlModifier) &&
                event.key >= Qt.Key_1 && event.key <= Qt.Key_5) {
            root.selectView(event.key - Qt.Key_1)
            event.accepted = true
            return
        }
        if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_Tab) {
            root.cycleView((event.modifiers & Qt.ShiftModifier) ? -1 : 1)
            event.accepted = true
        }
    }

    Item {
        anchors.fill: parent

        Rectangle {
            id: sortToolbar
            objectName: "albumLibraryToolbar"
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 46
            color: MichiTheme.colors.surfaceElevation0

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: MichiTheme.spacing.md
                anchors.rightMargin: MichiTheme.spacing.md
                spacing: MichiTheme.spacing.sm

                AlbumViewSelector {
                    objectName: "albumViewSelector"
                    currentView: root.currentView
                    onViewChanged: function(index) { root.selectView(index) }
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: qsTr("Ordenar por")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                }

                ComboBox {
                    id: sortSelector
                    objectName: "albumSortSelector"
                    Layout.preferredWidth: 174
                    model: root.sortOptions
                    textRole: "label"
                    valueRole: "key"
                    Accessible.name: qsTr("Orden de los álbumes")
                    onActivated: root.applySort(index)
                }

                Text {
                    text: qsTr("Densidad")
                    color: MichiTheme.colors.textSecondary
                    font.pixelSize: MichiTheme.typography.metaSize
                }

                ComboBox {
                    id: densitySelector
                    objectName: "albumDensitySelector"
                    Layout.preferredWidth: 150
                    model: root.densityOptions
                    textRole: "label"
                    valueRole: "key"
                    currentIndex: root.density === "compact" ? 0
                                  : root.density === "comfortable" ? 2 : 1
                    Accessible.name: qsTr("Densidad de los álbumes")
                    onActivated: root.applyDensity(index)
                }
            }
        }

        Item {
            id: contentArea
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: sortToolbar.bottom
            anchors.bottom: parent.bottom
            clip: true

            Loader {
                id: viewLoader
                objectName: "albumViewLoader"
                anchors.fill: parent
                active: !root.hasError
                asynchronous: true
                opacity: status === Loader.Ready ? 1 : 0
                source: {
                    switch (root.currentView) {
                    case 0: return "AlbumGridView.qml"
                    case 1: return "AlbumCoverFlowView.qml"
                    case 2: return "AlbumVinylWallView.qml"
                    case 3: return "AlbumTimelineView.qml"
                    case 4: return "AlbumMagazineView.qml"
                    default: return "AlbumGridView.qml"
                    }
                }

                Behavior on opacity {
                    enabled: !MichiTheme.reducedMotion
                    NumberAnimation {
                        duration: MichiTheme.motionFast
                        easing.type: Easing.OutCubic
                    }
                }

                onLoaded: {
                    if (!item)
                        return
                    item.albumModel = root.albumModel
                    item.bridge = root.bridge
                    if (typeof item.density !== "undefined")
                        item.density = root.density
                    item.albumClicked.connect(root.albumClicked)
                    Qt.callLater(root.restoreCurrentViewState)
                    item.forceActiveFocus()
                }
            }

            Rectangle {
                objectName: "albumLoadingMoreIndicator"
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: MichiTheme.spacing.md
                width: loadingMoreRow.implicitWidth + MichiTheme.spacing.lg
                height: 34
                radius: MichiTheme.radius.pill
                color: MichiTheme.colors.surfaceOverlay
                border.width: MichiTheme.borderWidth
                border.color: MichiTheme.colors.borderCard
                visible: root.loadingMore && root.loadedCount > 0
                z: 20

                Row {
                    id: loadingMoreRow
                    anchors.centerIn: parent
                    spacing: MichiTheme.spacing.sm

                    BusyIndicator {
                        width: 18
                        height: 18
                        running: parent.parent.visible
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: qsTr("Cargando más álbumes…")
                        color: MichiTheme.colors.textSecondary
                        font.pixelSize: MichiTheme.typography.captionSize
                        font.weight: MichiTheme.typography.weightSemiBold
                    }
                }
            }

            MichiLoadingState {
                anchors.centerIn: parent
                z: 30
                visible: root.initialLoading || viewLoader.status === Loader.Loading
                title: root.initialLoading
                       ? qsTr("Cargando álbumes")
                       : qsTr("Preparando vista")
            }

            LibraryPages.LibraryErrorState {
                anchors.centerIn: parent
                z: 40
                visible: root.hasError
                title: qsTr("No se pudieron cargar los álbumes")
                message: root.albumModel ? root.albumModel.errorMessage : qsTr("Error de consulta")
                actionText: qsTr("Reintentar")
                onActionRequested: {
                    if (root.albumModel && root.albumModel.retry)
                        root.albumModel.retry()
                }
            }

            LibraryPages.LibraryErrorState {
                objectName: "albumModelContentMismatchState"
                anchors.centerIn: parent
                z: 35
                visible: root.modelContentMismatch
                title: qsTr("Inconsistencia de modelo")
                message: qsTr("La biblioteca reporta álbumes pero no se cargó ninguno. Puede deberse a un índice dañado o a un filtro incompatible.")
                actionText: qsTr("Reintentar")
                onActionRequested: {
                    if (root.albumModel && root.albumModel.retry)
                        root.albumModel.retry()
                }
            }

            LibraryPages.LibraryEmptyState {
                anchors.centerIn: parent
                z: 30
                visible: root.albumModel && root.albumModel.initialized &&
                         root.albumModel.count === 0 && !root.initialLoading &&
                         !root.hasError && !root.modelContentMismatch
                title: qsTr("Sin álbumes")
                message: qsTr("No hay álbumes que coincidan con la búsqueda y los filtros actuales.")
            }
        }
    }
}
