import QtQuick

LibrarySectionPage {
    id: root

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property int currentView: 0
    standardFiltersEnabled: true

    headerSearchPlaceholder: qsTr("Buscar en %1…").arg(
                                 root.sectionTitle.toLowerCase()
                             )
    headerViewModes: [
        {
            id: "detailed",
            icon: "../../icons/view/library-table.svg",
            label: qsTr("Tabla detallada"),
            description: qsTr("Muestra columnas técnicas y metadatos")
        },
        {
            id: "compact",
            icon: "../../icons/view/library-compact.svg",
            label: qsTr("Lista compacta"),
            description: qsTr("Prioriza título y artista para mostrar más canciones")
        }
    ]
    headerCurrentView: root.currentView
    headerStatusText: root.lib
                      ? qsTr("%1 canciones").arg(root.lib.visibleCount)
                      : ""
    headerLoading: root.lib
                   ? ["INITIALIZING", "LOADING", "SCANNING", "INDEXING"]
                     .indexOf(root.lib.state) >= 0
                   : false

    function reloadCollection() {
    }

    function applyHeaderView(index) {
        if (index >= 0 && index < root.headerViewModes.length)
            root.currentView = index
    }

    function applyHeaderSearch(text, submitted) {
        root.headerSearchText = text || ""
        if (root.lib && root.lib.search)
            root.lib.search(root.headerSearchText)
    }

    function refreshHeaderContext() {
        root.reloadCollection()
    }

    function routeEnter(route, params) {
        root.reloadCollection()
    }

    LibraryTrackTable {
        anchors.fill: parent
        trackModel: root.lib ? root.lib.trackModel : null
        bridge: root.lib
        compactMode: root.currentView === 1
    }

    Component.onCompleted: root.reloadCollection()
}
