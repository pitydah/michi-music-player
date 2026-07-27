import QtQuick
import "../../theme"
import "album"

LibrarySectionPage {
    id: root
    objectName: "albumGridPage"
    focus: true
    sectionTitle: qsTr("Álbumes")
    sectionSubtitle: qsTr("Explora discos, ediciones y archivos cronológicos")
    sectionIcon: "albums"
    navigationIndex: 1
    standardFiltersEnabled: true

    Accessible.role: Accessible.Pane
    Accessible.name: qsTr("Álbumes")
    Accessible.description: qsTr("Explorador visual de álbumes")

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var albumModel: root.lib ? root.lib.albumModel : null
    property var bridge: root.lib
    property int currentView: 0

    headerSearchPlaceholder: qsTr("Buscar álbumes…")
    headerViewModes: [
        {
            id: "grid",
            icon: "../../icons/view/library-grid.svg",
            label: qsTr("Cuadrícula"),
            description: qsTr("Carátulas adaptables para explorar la colección")
        },
        {
            id: "coverflow",
            icon: "../../icons/view/library-coverflow.svg",
            label: qsTr("CoverFlow"),
            description: qsTr("Exploración horizontal centrada en las carátulas")
        },
        {
            id: "vinyl",
            icon: "../../icons/view/library-vinyl.svg",
            label: qsTr("Muro de vinilos"),
            description: qsTr("Presentación visual inspirada en discos físicos")
        },
        {
            id: "timeline",
            icon: "../../icons/view/library-timeline.svg",
            label: qsTr("Línea de tiempo"),
            description: qsTr("Organiza los álbumes por año y década")
        },
        {
            id: "editorial",
            icon: "../../icons/view/library-editorial.svg",
            label: qsTr("Editorial"),
            description: qsTr("Composición amplia con jerarquía de revista")
        }
    ]
    headerCurrentView: root.currentView
    headerStatusText: root.albumModel
                      ? qsTr("%1 álbumes").arg(root.albumModel.totalCount)
                      : ""
    headerLoading: root.albumModel
                   ? root.albumModel.loading || root.albumModel.loadingMore
                   : false

    signal albumClicked(string albumKey, string title, string artist, int year)
    signal viewChanged(int index)

    function selectView(index) {
        if (index < 0 || index >= root.headerViewModes.length ||
                index === root.currentView)
            return
        root.currentView = index
        root.viewChanged(index)
    }

    function applyHeaderView(index) {
        albumViewHost.selectView(index)
    }

    function applyHeaderSearch(text, submitted) {
        root.headerSearchText = text || ""
        if (root.lib && root.lib.search)
            root.lib.search(root.headerSearchText)
    }

    function refreshHeaderContext() {
        if (root.albumModel && root.albumModel.refresh)
            root.albumModel.refresh()
    }

    function routeEnter(route, params) {
        if (root.lib && root.lib.ensureLoaded)
            root.lib.ensureLoaded()
    }

    AlbumViewHost {
        id: albumViewHost
        anchors.fill: parent
        albumModel: root.albumModel
        bridge: root.bridge
        currentView: root.currentView
        onViewChanged: function(index) {
            root.currentView = index
            root.viewChanged(index)
        }
        onAlbumClicked: function(key, title, artist, year) {
            root.albumClicked(key, title, artist, year)
            if (typeof navigationBridge !== "undefined" && key)
                navigationBridge.navigateWithParams(
                    "library.album_detail",
                    {album_key: key}
                )
        }
    }

    Component.onCompleted: {
        if (root.lib && root.lib.ensureLoaded)
            root.lib.ensureLoaded()
    }
}
