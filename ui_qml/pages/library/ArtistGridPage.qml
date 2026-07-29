import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../theme"
import "../../components"

LibrarySectionPage {
    id: root
    objectName: "artistGridPage"
    focus: true
    sectionTitle: qsTr("Artistas")
    sectionSubtitle: qsTr("Explora intérpretes y creadores de tu biblioteca")
    sectionIcon: "artists"
    navigationIndex: 2
    standardFiltersEnabled: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Artistas")
    Accessible.description: qsTr("Explorador adaptable de artistas de la biblioteca")

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var artistModel: root.lib ? root.lib.artistModel : null
    property var bridge: root.lib
    property string density: "regular"
    readonly property var densityOptions: [
        { label: qsTr("Compacta"), key: "compact" },
        { label: qsTr("Regular"), key: "regular" },
        { label: qsTr("Cómoda"), key: "comfortable" }
    ]
    readonly property int minimumCardWidth: {
        if (root.density === "compact")
            return width < 760 ? 142 : 152
        if (root.density === "comfortable")
            return width < 760 ? 190 : 216
        return width < 760 ? 158 : 184
    }
    property bool automaticPagination: true
    property int currentView: 0
    headerSearchPlaceholder: qsTr("Buscar artistas…")
    headerViewModes: [
        {
            id: "grid",
            icon: "../../icons/view/library-artist-grid.svg",
            label: qsTr("Cuadrícula de artistas"),
            description: qsTr("Retratos y estadísticas en tarjetas")
        },
        {
            id: "list",
            icon: "../../icons/view/library-artist-list.svg",
            label: qsTr("Lista de artistas"),
            description: qsTr("Lectura compacta ordenada por nombre")
        }
    ]
    headerCurrentView: root.currentView
    headerStatusText: root.artistModel
                      ? qsTr("%1 artistas").arg(root.artistModel.totalCount)
                      : ""
    headerLoading: root.artistModel
                   ? root.artistModel.loading || root.artistModel.loadingMore
                   : false

    signal artistClicked(string name)
    signal viewChanged(int index)

    function selectView(index) {
        if (index < 0 || index >= root.headerViewModes.length ||
                index === root.currentView)
            return
        root.currentView = index
        root.viewChanged(index)
    }

    function applyHeaderView(index) {
        root.selectView(index)
    }

    function applyHeaderSearch(text, submitted) {
        root.headerSearchText = text || ""
        if (root.lib && root.lib.search)
            root.lib.search(root.headerSearchText)
    }

    function refreshHeaderContext() {
        if (root.artistModel && root.artistModel.refresh)
            root.artistModel.refresh()
    }

    function openCurrentArtist() {
        if (!root.artistModel || gridView.currentIndex < 0 || !root.artistModel.get)
            return
        var artist = root.artistModel.get(gridView.currentIndex)
        var name = artist.name || ""
        if (name)
            root.artistClicked(name)
    }

    function maybeFetchMore() {
        if (!root.automaticPagination || !root.artistModel || !root.artistModel.hasMore ||
                root.artistModel.loadingMore || gridView.moving)
            return
        var remaining = gridView.contentHeight - (gridView.contentY + gridView.height)
        if (remaining <= gridView.cellHeight * 2)
            root.artistModel.fetchMore()
    }

    StackLayout {
        anchors.fill: parent
        currentIndex: root.currentView

        GridView {
            id: gridView
            objectName: "artistGrid"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.topMargin: 46
            model: root.artistModel
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            keyNavigationWraps: false
            activeFocusOnTab: true
            focus: true
            cacheBuffer: cellHeight * 2

            readonly property int columnCount: Math.max(
                1,
                Math.floor(width / root.minimumCardWidth)
            )
            cellWidth: width / columnCount
            cellHeight: Math.max(206, Math.min(258, cellWidth + 42))

            onContentYChanged: paginationTimer.restart()
            onMovementEnded: root.maybeFetchMore()
            onCurrentIndexChanged: {
                if (currentIndex >= 0) {
                    positionViewAtIndex(currentIndex, GridView.Contain)
                    if (root.artistModel && root.artistModel.hasMore &&
                            !root.artistModel.loadingMore &&
                            currentIndex >= Math.max(0, count - 5))
                        root.artistModel.fetchMore()
                }
            }

            Keys.onReturnPressed: root.openCurrentArtist()
            Keys.onEnterPressed: root.openCurrentArtist()
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Home) {
                    currentIndex = count > 0 ? 0 : -1
                    positionViewAtBeginning()
                    event.accepted = true
                } else if (event.key === Qt.Key_End) {
                    currentIndex = count > 0 ? count - 1 : -1
                    positionViewAtEnd()
                    root.maybeFetchMore()
                    event.accepted = true
                }
            }

            Timer {
                id: paginationTimer
                interval: 90
                repeat: false
                onTriggered: root.maybeFetchMore()
            }

            ScrollBar.vertical: ScrollBar {
                width: 8
                policy: ScrollBar.AsNeeded
            }

            delegate: Item {
                id: artistDelegate
                required property int index
                required property string name
                required property var trackCount
                required property var albumCount
                required property string coverKey

                width: gridView.cellWidth
                height: gridView.cellHeight

                ArtistCard {
                    anchors.fill: parent
                    anchors.margins: MichiTheme.spacing.sm
                    artistName: artistDelegate.name
                    trackCount: Number(artistDelegate.trackCount) || 0
                    albumCount: Number(artistDelegate.albumCount) || 0
                    coverKey: artistDelegate.coverKey
                    selected: GridView.isCurrentItem

                    onClicked: {
                        gridView.currentIndex = artistDelegate.index
                        root.artistClicked(artistDelegate.name)
                    }
                }
            }

            footer: Item {
                width: gridView.width
                height: root.artistModel && root.artistModel.hasMore
                        ? 52
                        : MichiTheme.spacing.md

                MichiButton {
                    anchors.centerIn: parent
                    visible: root.artistModel && root.artistModel.hasMore
                    enabled: root.artistModel && !root.artistModel.loadingMore
                    text: root.artistModel && root.artistModel.loadingMore
                          ? qsTr("Cargando…")
                          : qsTr("Cargar más artistas")
                    variant: "ghost"
                    onClicked: root.artistModel.fetchMore()
                }
            }
        }

        ArtistListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            artistModel: root.artistModel
            bridge: root.bridge
            onArtistClicked: function(name) { root.artistClicked(name) }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 46
        color: MichiTheme.colors.surfaceElevation0
        visible: root.currentView === 0
        z: 10

        RowLayout {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: MichiTheme.spacing.md
            spacing: MichiTheme.spacing.sm

            Text {
                text: qsTr("Densidad")
                color: MichiTheme.colors.textSecondary
                font.pixelSize: MichiTheme.typography.metaSize
            }

            ComboBox {
                objectName: "artistDensitySelector"
                Layout.preferredWidth: 150
                model: root.densityOptions
                textRole: "label"
                valueRole: "key"
                currentIndex: root.density === "compact" ? 0
                              : root.density === "comfortable" ? 2 : 1
                Accessible.name: qsTr("Densidad de la cuadrícula de artistas")
                onActivated: root.density = currentValue
            }
        }
    }

    Component.onCompleted: {
        if (root.lib && root.lib.ensureLoaded)
            root.lib.ensureLoaded()
    }
}
