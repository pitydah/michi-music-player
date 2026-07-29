import QtQuick

LibrarySectionPage {
    id: root
    objectName: "composersPage"
    focus: true
    sectionTitle: qsTr("Compositores")
    sectionSubtitle: qsTr("Obras agrupadas por autor y compositor")
    sectionIcon: "artists"
    navigationIndex: 4

    property var lib: typeof libraryBridge !== "undefined" ? libraryBridge : null
    property var _composers: []
    property int currentView: 0
    property int pageSize: 100
    property bool hasMore: false
    property bool loadingMore: false
    property int totalComposers: 0
    readonly property var visibleComposers: root.filteredEntries(
                                                       root._composers,
                                                       root.headerSearchText
                                                   )

    headerSearchPlaceholder: qsTr("Buscar compositores…")
    headerViewModes: [
        {
            id: "grid",
            icon: "../../icons/view/library-artist-grid.svg",
            label: qsTr("Mosaico de compositores"),
            description: qsTr("Tarjetas amplias con cantidad de obras")
        },
        {
            id: "list",
            icon: "../../icons/view/library-artist-list.svg",
            label: qsTr("Lista de compositores"),
            description: qsTr("Lectura compacta ordenada por nombre")
        }
    ]
    headerCurrentView: root.currentView
    headerStatusText: root.totalComposers > root.visibleComposers.length && root.headerSearchText === ""
                      ? qsTr("%1 de %2 compositores").arg(root._composers.length).arg(root.totalComposers)
                      : qsTr("%1 compositores").arg(root.visibleComposers.length)

    signal composerSelected(string composer)

    function entryName(entry) {
        if (typeof entry !== "object")
            return entry || ""
        return entry.name || entry.composer || ""
    }

    function filteredEntries(entries, query) {
        var normalized = (query || "").trim().toLocaleLowerCase()
        if (normalized === "")
            return entries || []
        return (entries || []).filter(function(entry) {
            return root.entryName(entry).toLocaleLowerCase().indexOf(normalized) >= 0
        })
    }

    function reload() {
        root._composers = []
        root.hasMore = false
        root.totalComposers = 0
        root.fetchMore()
    }

    function fetchMore() {
        if (!root.lib || !root.lib.getComposers || root.loadingMore)
            return
        root.loadingMore = true
        var result = root.lib.getComposers(root._composers.length, root.pageSize) || {}
        var items = result.items || []
        root._composers = root._composers.concat(items)
        root.totalComposers = Number(result.total || root._composers.length)
        root.hasMore = Boolean(result.has_more)
        root.loadingMore = false
    }

    function openComposer(composer) {
        root.composerSelected(composer)
        if (typeof navigationBridge !== "undefined" && composer)
            navigationBridge.navigateWithParams(
                "library.composer_detail",
                {composer: composer}
            )
    }

    function applyHeaderSearch(text, submitted) {
        root.headerSearchText = text || ""
    }

    function applyHeaderView(index) {
        if (index >= 0 && index < root.headerViewModes.length)
            root.currentView = index
    }

    function refreshHeaderContext() {
        root.reload()
    }

    function routeEnter(route, params) {
        root.reload()
    }

    LibraryFacetView {
        anchors.fill: parent
        entries: root.visibleComposers
        currentView: root.currentView
        singularName: qsTr("compositor")
        pluralName: qsTr("compositores")
        iconKey: "artists"
        hasMore: root.hasMore
        loadingMore: root.loadingMore
        onEntryActivated: function(value) { root.openComposer(value) }
        onFetchMoreRequested: root.fetchMore()
    }

    Component.onCompleted: reload()
}
