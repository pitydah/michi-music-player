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
    readonly property bool initialLoading: root.albumModel && root.albumModel.loading && root.albumModel.count === 0
    readonly property bool loadingMore: root.albumModel && root.albumModel.loadingMore
    readonly property bool hasError: root.albumModel && root.albumModel.errorMessage !== ""
    readonly property int loadedCount: root.albumModel ? root.albumModel.count : 0
    readonly property int totalCount: root.albumModel ? root.albumModel.totalCount : 0
    readonly property var viewModes: [
        { name: qsTr("Grid"), shortName: qsTr("Grid"), description: qsTr("Colección adaptable") },
        { name: qsTr("CoverFlow"), shortName: qsTr("Flow"), description: qsTr("Exploración cinematográfica") },
        { name: qsTr("Vinyl Wall"), shortName: qsTr("Vinyl"), description: qsTr("Muro de discos") },
        { name: qsTr("Timeline"), shortName: qsTr("Tiempo"), description: qsTr("Archivo cronológico") },
        { name: qsTr("Magazine"), shortName: qsTr("Editorial"), description: qsTr("Curaduría visual") }
    ]

    signal albumClicked(string albumKey, string title, string artist, int year)
    signal viewChanged(int viewIndex)

    function selectView(index) {
        if (index < 0 || index >= root.viewModes.length || index === root.currentView)
            return
        root.currentView = index
        root.viewChanged(index)
    }

    function cycleView(delta) {
        var next = (root.currentView + delta + root.viewModes.length) % root.viewModes.length
        root.selectView(next)
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
            id: contentArea

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
                    item.albumClicked.connect(root.albumClicked)
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

            LoadingState {
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

            LibraryPages.LibraryEmptyState {
                anchors.centerIn: parent
                z: 30
                visible: root.albumModel && root.albumModel.initialized &&
                         root.albumModel.count === 0 && !root.initialLoading && !root.hasError
                title: qsTr("Sin álbumes")
                message: qsTr("No hay álbumes que coincidan con la búsqueda y los filtros actuales.")
            }
    }
}
