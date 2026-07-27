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
    headerStatusText: qsTr("%1 compositores").arg(root.visibleComposers.length)

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
        if (root.lib && root.lib.getComposers)
            root._composers = root.lib.getComposers() || []
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
        onEntryActivated: function(value) { root.openComposer(value) }
    }

    Component.onCompleted: reload()
}
